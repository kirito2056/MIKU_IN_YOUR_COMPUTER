import json
import os
import argparse

import torch
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoModelForMultimodalLM,
    AutoProcessor,
    AutoTokenizer,
)


def is_gemma4_model(model_path: str) -> bool:
    """config.json 의 model_type 으로 Gemma 4 여부 판별."""
    config_path = os.path.join(model_path, "config.json")
    if not os.path.exists(config_path):
        return False
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("model_type") == "gemma4_unified"


def merge_lora(base_model_path: str, lora_path: str, output_path: str):
    print("LoRA Merge Start!")

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

    gemma4 = is_gemma4_model(base_model_path)
    model_cls = AutoModelForMultimodalLM if gemma4 else AutoModelForCausalLM
    print(f"Detected architecture: {'Gemma 4 (gemma4_unified)' if gemma4 else 'CausalLM (Gemma 3 등)'}")

    print("\n1. Loading base model... (using RAM)")
    # VRAM 이슈를 피하기 위해 CPU(RAM)로만 모델을 로드합니다.
    load_kwargs = dict(
        device_map="cpu",
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
    # Gemma 4(transformers 5.x)는 dtype, 그 외는 torch_dtype 사용
    if gemma4:
        load_kwargs["dtype"] = torch.float16
        load_kwargs["attn_implementation"] = "eager"
    else:
        load_kwargs["torch_dtype"] = torch.float16

    base_model = model_cls.from_pretrained(base_model_path, **load_kwargs)

    print("2. Loading tokenizer/processor...")
    if gemma4:
        processor = AutoProcessor.from_pretrained(base_model_path, trust_remote_code=True)
        tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor
    else:
        processor = None
        tokenizer = AutoTokenizer.from_pretrained(base_model_path)

    print(f"3. Applying LoRA adapter... ({lora_path})")
    peft_model = PeftModel.from_pretrained(
        base_model,
        lora_path,
        device_map="cpu",
    )

    print("4. Merging weights... (This may take a few minutes)")
    merged_model = peft_model.merge_and_unload()

    print(f"5. Saving merged model... ({output_path})")
    os.makedirs(output_path, exist_ok=True)

    # MemoryError 방지를 위해 여러 개의 작은 파일(shard)로 나누어 저장합니다.
    merged_model.save_pretrained(
        output_path,
        safe_serialization=True,
        max_shard_size="2GB",  # 한 파일당 최대 2GB로 쪼개서 저장
    )
    # 토크나이저/프로세서 저장 (GGUF 변환 시 필요)
    if processor is not None:
        processor.save_pretrained(output_path)
    else:
        tokenizer.save_pretrained(output_path)

    print("\nMerge completed! Ready for GGUF conversion.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="models/Gemma4_12B", help="베이스 모델 경로")
    parser.add_argument("--lora", default="models/outputs/miku_gemma4_v2", help="학습된 LoRA 경로")
    parser.add_argument("--output", default="models/miku_Gemma4_12B_merged", help="병합된 모델을 저장할 경로")

    args = parser.parse_args()
    merge_lora(args.base_model, args.lora, args.output)
