# Lightweight Model Options

## Currently Selected: TinyLlama-1.1B-Chat
- **Size**: ~600MB
- **Parameters**: 1.1B
- **Speed**: Very Fast
- **Quality**: Good for basic conversations

## Alternative Lightweight Models

### 1. Phi-3-Mini (Recommended for better quality)
```
GGUF_REPO=microsoft/Phi-3-mini-4k-instruct-gguf
GGUF_FILE=Phi-3-mini-4k-instruct-q4.gguf
```
- **Size**: ~2.4GB
- **Parameters**: 3.8B
- **Speed**: Fast
- **Quality**: Excellent for its size

### 2. Qwen2-1.5B (Good balance)
```
GGUF_REPO=Qwen/Qwen2-1.5B-Instruct-GGUF
GGUF_FILE=qwen2-1_5b-instruct-q4_0.gguf
```
- **Size**: ~900MB
- **Parameters**: 1.5B
- **Speed**: Very Fast
- **Quality**: Better than TinyLlama

### 3. StableLM-2-Zephyr-1.6B
```
GGUF_REPO=stabilityai/stablelm-2-zephyr-1_6b-gguf
GGUF_FILE=stablelm-2-zephyr-1_6b.Q4_K_M.gguf
```
- **Size**: ~1GB
- **Parameters**: 1.6B
- **Speed**: Very Fast
- **Quality**: Good instruction following

### 4. OpenELM-1.1B (Apple's model)
```
GGUF_REPO=ggml-org/models
GGUF_FILE=openelm-1_1b-instruct-q4_0.gguf
```
- **Size**: ~700MB
- **Parameters**: 1.1B
- **Speed**: Very Fast
- **Quality**: Decent

## How to Change Models

### Method 1: Environment Variables (Recommended)
Set these environment variables before running:
```bash
export GGUF_REPO="microsoft/Phi-3-mini-4k-instruct-gguf"
export GGUF_FILE="Phi-3-mini-4k-instruct-q4.gguf"
```

### Method 2: Edit app.py
Change lines 14-15 in app.py:
```python
MODEL_REPO = os.getenv("GGUF_REPO", "your-chosen-repo")
MODEL_FILE = os.getenv("GGUF_FILE", "your-chosen-file.gguf")
```

### Method 3: Edit docker-compose.yml
Update the environment section in docker-compose.yml

## Performance Comparison
| Model | Size | Speed | Quality | Memory Usage |
|-------|------|-------|---------|--------------|
| TinyLlama-1.1B | 600MB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ~1GB RAM |
| Qwen2-1.5B | 900MB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ~1.5GB RAM |
| Phi-3-Mini | 2.4GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ~3GB RAM |
| StableLM-2 | 1GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ~1.5GB RAM |