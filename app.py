import os
from flask import Flask, request, jsonify, session, render_template
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from flask_cors import CORS
from datetime import timedelta, datetime
import secrets
import re
from functools import wraps

# --------------------------------------------------------------------------
# --- 1. Configuration ---
# --------------------------------------------------------------------------
# Load model configuration from environment variables with sensible defaults.
# This allows for flexible deployment without changing the code.
# Using TinyLlama for lightweight deployment (~600MB vs ~4GB)
MODEL_REPO = os.getenv("GGUF_REPO", "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF")
MODEL_FILE = os.getenv("GGUF_FILE", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")

# Configure model parameters.
# N_THREADS is set to one less than the CPU count for optimal performance.
# N_GPU_LAYERS allows offloading layers to a GPU if available (set to 0 for CPU-only).
N_THREADS = max(1, (os.cpu_count() or 4) - 1)
N_CTX = int(os.getenv("N_CTX", "2048"))
N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "0"))

# --------------------------------------------------------------------------
# --- 2. Download and Load LLM ---
# --------------------------------------------------------------------------
# Download the model file from Hugging Face Hub if it's not already cached.
print("Downloading/locating model...")
try:
    model_path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
except Exception as e:
    print(f"Error downloading model: {e}")
    exit()

# Load the model into memory using llama-cpp-python.
# This can take some time depending on the model size and hardware.
print("Loading model into memory... This may take a moment.")
llm = Llama(
    model_path=model_path,
    n_ctx=N_CTX,
    n_threads=N_THREADS,
    n_gpu_layers=N_GPU_LAYERS,
    verbose=False,  # Set to True for detailed llama.cpp logging.
)
print("Model loaded successfully.")

# --------------------------------------------------------------------------
# --- 3. Flask Application Setup ---
# --------------------------------------------------------------------------
app = Flask(__name__)

# Set a secret key for session management. This is crucial for security.
# Generate a secure random key if not provided via environment variable.
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)

# Production security configurations
app.config.update(
    SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY=True,  # Prevent XSS attacks
    SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)

# Set the session to be permanent with a 2-hour lifetime.
app.permanent_session_lifetime = timedelta(hours=2)

# Configure CORS (Cross-Origin Resource Sharing) for production deployment.
# Load allowed origins from environment variable for security.
# Default to localhost for development, but should be set to actual domain(s) in production.
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000").split(",")

# Production-ready CORS configuration
CORS(app, 
     resources={
         r"/chat": {
             "origins": ALLOWED_ORIGINS,
             "methods": ["POST"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Type"],
             "max_age": 3600  # Cache preflight requests for 1 hour
         },
         r"/api/chat": {
             "origins": ALLOWED_ORIGINS,
             "methods": ["POST"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Type"],
             "max_age": 3600
         }
     }, 
     supports_credentials=True)

# Add security headers for production
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Only add HSTS in production with HTTPS
    if os.getenv("FLASK_ENV") == "production":
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

# Rate limiting for production
def rate_limit(max_requests=10, window_minutes=1):
    """Simple rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client IP
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            
            # Rate limiting key
            rate_key = f"rate_limit_{client_ip}"
            
            # Get current requests from session (simple in-memory rate limiting)
            current_time = datetime.now()
            if rate_key not in session:
                session[rate_key] = []
            
            # Clean old requests
            session[rate_key] = [
                req_time for req_time in session[rate_key] 
                if (current_time - datetime.fromisoformat(req_time)).total_seconds() < window_minutes * 60
            ]
            
            # Check rate limit
            if len(session[rate_key]) >= max_requests:
                return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
            
            # Add current request
            session[rate_key].append(current_time.isoformat())
            session.modified = True
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Input validation
def validate_message(message):
    """Validate user input for security."""
    if not message or not isinstance(message, str):
        return False, "Message must be a non-empty string"
    
    # Length validation
    if len(message) > 1000:
        return False, "Message too long (max 1000 characters)"
    
    if len(message.strip()) < 1:
        return False, "Message cannot be empty"
    
    # Basic content filtering (you can expand this)
    suspicious_patterns = [
        r'<script.*?>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return False, "Message contains potentially harmful content"
    
    return True, "Valid"

# --------------------------------------------------------------------------
# --- 4. System Prompt and Response Cleaning ---
# --------------------------------------------------------------------------
# This system prompt defines the chatbot's persona and rules.
# It guides the model's behavior, but adherence can vary.
SYSTEM_PROMPT = """You are a helpful and friendly health and wellness assistant named Metabolical.

**Your Core Instructions:**
1.  **First Response Only:** In your very first response to a user, introduce yourself briefly.
2.  **Be Direct:** For all subsequent responses, get straight to the point. DO NOT re-introduce yourself.
3.  **Stay Focused:** Only discuss health, nutrition, metabolism, and exercise.
4.  **Safety First:** Never diagnose medical conditions or give medical advice. Always recommend consulting a healthcare professional.
5.  **Use History:** Use conversation history for context.
"""

def clean_response(response: str) -> str:
    """
    Cleans the raw output from the LLM to enforce length constraints.
    """
    response = response.strip()
    # Split the response into sentences and limit it to the first 4.
    sentences = response.split('. ')
    if len(sentences) > 4:
        response = '. '.join(sentences[:4])
        # Ensure the truncated response ends with a period.
        if not response.endswith('.'):
            response += '.'
    return response

# --------------------------------------------------------------------------
# --- 5. Routes ---
# --------------------------------------------------------------------------
@app.route("/")
def index():
    """Serve the main chat interface."""
    return render_template('index.html')

@app.route("/chat", methods=["POST"])
@app.route("/api/chat", methods=["POST"])
@rate_limit(max_requests=20, window_minutes=1)  # Allow 20 requests per minute
def chat():
    """
    Handles the chat interaction. It receives a user message, maintains
    conversation history in a session, gets a response from the LLM,
    and returns it.
    """
    try:
        # --- Get User Input ---
        data = request.get_json(force=True)
        user_msg = (data.get("message") or "").strip()
        
        # Validate input
        is_valid, validation_message = validate_message(user_msg)
        if not is_valid:
            return jsonify({"error": validation_message}), 400

        # --- Manage Conversation History ---
        # Load messages from the session, or start a new list.
        messages = session.get('messages', [])
        messages.append({"role": "user", "content": user_msg})

        # --- Prepare Messages for LLM ---
        # The message list for the LLM always starts with the system prompt.
        llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        
        # To prevent the context from exceeding the model's limit (N_CTX),
        # we truncate the history, keeping the system prompt and the last 8 messages.
        if len(llm_messages) > 9:
            llm_messages = [llm_messages[0]] + llm_messages[-8:]

        # --- Generate LLM Response ---
        resp = llm.create_chat_completion(
            messages=llm_messages,
            temperature=0.3,
            top_p=0.8,
            max_tokens=150,
            stop=["User:", "You:", "\n\n", "Human:"], # Stop tokens prevent run-on sentences.
        )

        raw_answer = resp["choices"][0]["message"]["content"]
        clean_answer = clean_response(raw_answer)

        # --- Update Session and Return Response ---
        messages.append({"role": "assistant", "content": clean_answer})
        session['messages'] = messages
        session.modified = True  # Explicitly mark session as modified.

        return jsonify({"reply": clean_answer})

    except Exception as e:
        print(f"[ERROR] /api/chat: {str(e)}")
        return jsonify({"error": "An internal server error occurred. Please try again."}), 500

# --------------------------------------------------------------------------
# --- 6. Main Execution Block ---
# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Check for debug mode from environment variable.
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ["true", "1"]
    
    # Print startup information.
    print(f"--- Starting Metabolical Chatbot ---")
    print(f"Model: {MODEL_REPO}/{MODEL_FILE}")
    print(f"GPU Layers: {N_GPU_LAYERS}")
    print(f"Debug Mode: {debug_mode}")
    print("------------------------------------")
    
    # Run the Flask app. host="0.0.0.0" makes it accessible on your local network.
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
