import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import argparse

def merge_lora(base_model_path: str, lora_path: str, output_path: str):
    print(f"LoRA Merge Start!")
    
    # Path resolution
    if not os.path.isabs(base_model_path):
        base_model_path = os.path.join("backend", base_model_path)
    if not os.path.isabs(lora_path):
        lora_path = os.path.join("backend", lora_path)
    if not os.path.isabs(output_path):
        output_path = os.path.join("backend", output_path)
    print(f"Base model: {base_model_path}")
    print(f"LoRA path: {lora_path}")
    print(f"Output path: {output_path}")
    
    print("\n1. Loading base model... (using RAM)")
    # VRAM 이슈를 피하기 위해 CPU(RAM)로만 모델을 로드합니다.
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.float16,  # 16비트 실수로 로드 (병합을 위해 필요)
        device_map="cpu",           # GPU를 쓰지 않고 RAM만 사용
        low_cpu_mem_usage=True,
        trust_remote_code=True      # Gemma 4 아키텍처 로드를 위해 필수
    )
    
    print("2. Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_path)
    
    print(f"3. Applying LoRA adapter... ({lora_path})")
    peft_model = PeftModel.from_pretrained(
        base_model,
        lora_path,
        device_map="cpu"
    )
    
    print("4. Merging weights... (This may take a few minutes)")
    merged_model = peft_model.merge_and_unload()
    
    print(f"5. Saving merged model... ({output_path})")
    os.makedirs(output_path, exist_ok=True)
    
    # MemoryError 방지를 위해 여러 개의 작은 파일(shard)로 나누어 저장합니다.
    merged_model.save_pretrained(
        output_path, 
        safe_serialization=True,
        max_shard_size="2GB"  # 한 파일당 최대 2GB로 쪼개서 저장
    )
    tokenizer.save_pretrained(output_path)
    
    print("\nMerge completed! Ready for GGUF conversion.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="models/Gemma4_12B", help="베이스 모델 경로")
    parser.add_argument("--lora", default="outputs/miku_lora", help="학습된 LoRA 경로")
    parser.add_argument("--output", default="models/miku_Gemma4_12B_merged", help="병합된 모델을 저장할 경로")
    
    args = parser.parse_args()
    merge_lora(args.base_model, args.lora, args.output)
