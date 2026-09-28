import json, random, torch
from pathlib import Path
from datasets import Dataset
from transformers import (AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig,
                          TrainingArguments, Trainer, DataCollatorForSeq2Seq)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

BASE_DIR = Path(__file__).resolve().parent.parent
BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
TRAIN_FILE = BASE_DIR / "data/processed/finetune_train.jsonl"
VAL_FILE = BASE_DIR / "data/processed/finetune_val.jsonl"
OUTPUT_DIR = BASE_DIR / "models/mtsamples-summarizer-lora"

MAX_LEN = 1536
MAX_TRAIN = 1500
NUM_EPOCHS = 1
SYSTEM_PROMPT = "You are a medical assistant that summarizes clinical reports for patients."

def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]

def main():
    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def encode(ex):
        msgs = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{ex['instruction']}\n\nReport:\n{ex['input']}"}]
        prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
        a_ids = tok(ex["output"] + tok.eos_token, add_special_tokens=False)["input_ids"]
        ids = p_ids + a_ids
        labels = [-100] * len(p_ids) + a_ids
        return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels}

    def build(rows, limit=None):
        random.Random(42).shuffle(rows)
        out = []
        for r in rows:
            e = encode(r)
            if len(e["input_ids"]) <= MAX_LEN:
                out.append(e)
            if limit and len(out) >= limit:
                break
        return Dataset.from_list(out)

    train_ds = build(load_jsonl(TRAIN_FILE), MAX_TRAIN)
    val_ds = build(load_jsonl(VAL_FILE), 100)
    print(f"Train examples: {len(train_ds)} | Val examples: {len(val_ds)}")

    use_bf16 = torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if use_bf16 else torch.float16

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=dtype, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, quantization_config=bnb, device_map="auto")
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    args = TrainingArguments(
        output_dir=str(OUTPUT_DIR), num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=2e-4, lr_scheduler_type="cosine", warmup_steps=5,
        logging_steps=10, eval_strategy="no", save_strategy="no",
        bf16=use_bf16, fp16=not use_bf16, optim="paged_adamw_8bit",
        gradient_checkpointing=True, report_to="none")

    trainer = Trainer(model=model, args=args, train_dataset=train_ds,
                      data_collator=DataCollatorForSeq2Seq(tok, padding=True, label_pad_token_id=-100))
    trainer.train()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUTPUT_DIR)
    tok.save_pretrained(OUTPUT_DIR)
    (OUTPUT_DIR / "base_model.txt").write_text(BASE_MODEL)
    print("Adapter saved to", OUTPUT_DIR)

if __name__ == "__main__":
    main()