import os
from huggingface_hub import snapshot_download

def download_model():
    model_id = "google/gemma-3-12b-it"
    local_dir = "models/Gemma_12B"
    
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
        print("\nNote: Gemma 3 requires accepting the license agreement on HuggingFace.")
        print("1. Go to https://huggingface.co/google/gemma-3-12b-it")
        print("2. Accept the terms")
        print("3. Run 'huggingface-cli login' in terminal to authenticate")

if __name__ == "__main__":
    download_model()
