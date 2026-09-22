"""
summarize_finetuned.py

*** RUN THIS ON A GPU MACHINE ONLY ***

Loads base model + fine-tuned LoRA adapter, generates a summary.
"""

import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

ADAPTER_PATH = "models/mtsamples-summarizer-lora"
SYSTEM_PROMPT = "You are a medical assistant that summarizes clinical reports for patients."


def get_base_model_name() -> str:
    f = Path(ADAPTER_PATH) / "base_model.txt"
    return f.read_text().strip() if f.exists() else "meta-llama/Llama-3.1-8B-Instruct"


def load_finetuned_model():
    base_model_name = get_base_model_name()
    print(f"Loading base model: {base_model_name}")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    base_model = AutoModelForCausalLM.from_pretrained(base_model_name, quantization_config=bnb_config, device_map="auto")
    model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    model.eval()
    return model, tokenizer


def summarize_with_finetuned(model, tokenizer, report_text: str, max_new_tokens: int = 256) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Summarize this medical report in simple, patient-friendly language.\n\nReport:\n{report_text}"},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output_ids = model.generate(
            **inputs, max_new_tokens=max_new_tokens, temperature=0.3,
            do_sample=True, pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()


if __name__ == "__main__":
    model, tokenizer = load_finetuned_model()
    sample_report = """
    PREOPERATIVE DIAGNOSIS: Acute appendicitis.
    POSTOPERATIVE DIAGNOSIS: Acute appendicitis with perforation.
    PROCEDURE: Laparoscopic appendectomy.
    The patient is a 34-year-old male who presented with right lower
    quadrant pain for two days. CT scan showed an inflamed appendix
    measuring 1.2 cm with evidence of perforation. No signs of abscess
    formation.
    """
    summary = summarize_with_finetuned(model, tokenizer, sample_report)
    print("\n--- Fine-tuned Model Summary ---\n")
    print(summary)
