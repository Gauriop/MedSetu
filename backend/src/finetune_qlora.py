"""
finetune_qlora.py

*** RUN THIS ON A GPU MACHINE ONLY (Colab / college PC) ***

Fine-tunes Llama 3.1 8B Instruct on MTSamples using QLoRA.
"""

import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
# BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"   # fallback if Llama access/GPU is an issue

TRAIN_FILE = "data/processed/finetune_train.jsonl"
VAL_FILE = "data/processed/finetune_val.jsonl"
OUTPUT_DIR = "models/mtsamples-summarizer-lora"

MAX_SEQ_LENGTH = 2048
NUM_EPOCHS = 2
LEARNING_RATE = 2e-4
LORA_RANK = 16
LORA_ALPHA = 32
SYSTEM_PROMPT = "You are a medical assistant that summarizes clinical reports for patients."


def format_example(example):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{example['instruction']}\n\nReport:\n{example['input']}"},
            {"role": "assistant", "content": example["output"]},
        ]
    }


def main():
    print(f"Fine-tuning base model: {BASE_MODEL}")
    dataset = load_dataset("json", data_files={"train": TRAIN_FILE, "validation": VAL_FILE})

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def apply_template(example):
        formatted = format_example(example)
        text = tokenizer.apply_chat_template(formatted["messages"], tokenize=False)
        return {"text": text}

    dataset = dataset.map(apply_template)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, quantization_config=bnb_config, device_map="auto")
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=LORA_RANK, lora_alpha=LORA_ALPHA,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR, num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=2, gradient_accumulation_steps=4,
        learning_rate=LEARNING_RATE, logging_steps=10,
        save_strategy="epoch", eval_strategy="epoch", bf16=True, report_to="none",
    )

    trainer = SFTTrainer(
        model=model, args=training_args,
        train_dataset=dataset["train"], eval_dataset=dataset["validation"],
        dataset_text_field="text", max_seq_length=MAX_SEQ_LENGTH,
    )

    print("Starting fine-tuning...")
    trainer.train()

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    with open(f"{OUTPUT_DIR}/base_model.txt", "w") as f:
        f.write(BASE_MODEL)

    print("Done. Copy the models/mtsamples-summarizer-lora folder back to your repo.")


if __name__ == "__main__":
    main()
