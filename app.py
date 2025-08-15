import os
from flask import Flask, request, jsonify, session, render_template
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from flask_cors import CORS
from datetime import timedelta

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
# It's best practice to load this from an environment variable.
app.secret_key = os.getenv("SECRET_KEY", "a-very-secret-and-secure-key-for-testing")

# Set the session to be permanent with a 2-hour lifetime.
app.permanent_session_lifetime = timedelta(hours=2)

# Configure CORS (Cross-Origin Resource Sharing) for the chat API endpoint.
# This allows web pages from any origin to call the API.
# `supports_credentials=True` is necessary for sessions (cookies) to work correctly.
CORS(app, resources={r"/chat": {"origins": "*"}, r"/api/chat": {"origins": "*"}}, supports_credentials=True)

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
        if not user_msg:
            return jsonify({"error": "Message cannot be empty"}), 400

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
