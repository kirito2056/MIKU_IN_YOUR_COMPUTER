import os
from huggingface_hub import snapshot_download

def download_model():
    model_id = "google/gemma-4-12B-it"
    local_dir = "models/Gemma4_12B"
    
    print(f"Downloading {model_id} to {local_dir}...")
    
    # Create directory if it doesn't exist
    os.makedirs(local_dir, exist_ok=True)
    
    try:
        # Download the model
        snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False, # We want actual files, not symlinks
            ignore_patterns=["*.msgpack", "*.h5", "*.tflite", "*original*"] # Only get safetensors
        )
        print("\nDownload completed successfully!")
    except Exception as e:
        print(f"\nError downloading model: {e}")
        print("\nNote: Gemma 4 is Apache 2.0 licensed. If download fails, check network or HuggingFace access.")
        print("1. Go to https://huggingface.co/google/gemma-4-12B-it")
        print("2. Run 'huggingface-cli login' in terminal if authentication is required")

if __name__ == "__main__":
    download_model()
