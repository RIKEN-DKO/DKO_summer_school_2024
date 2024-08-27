import argparse
from datasets import Dataset, DatasetDict
from transformers import LlamaTokenizer, AutoModelForCausalLM
import bitsandbytes as bnb
import torch
import os
import json
import transformers
from peft import LoraConfig
# from incorrect_promt import SPARQLQueryGenerator
from trl import SFTTrainer
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
from peft import AutoPeftModelForCausalLM
from random import sample
from .prompts import question_label2uri_database_to_sparql,question_label2uri_database_prefixes_to_sparql


def load_data_from_file(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return {key: [d[key] for d in data] for key in data[0].keys()}


def generate_prompt_question(example):
    question = example['question']
    sparql = example["sparql"]
    prompt = f"### INSTRUCTION\nPlease convert the following context into an SPARQL query.\n\n### CONTEXT:\n{question}\n\n### SPARQL:\n{sparql}"
    return {'text': prompt}

def generate_prompt_label2uri(example,databases2prefixes):
    prompt_str =  question_label2uri_database_prefixes_to_sparql
    question = example['question']
    sparql = example["sparql"]
    label2uri = str(example["label2URI"])
    database=example["database"]
    prefixes = "\n".join(databases2prefixes[database])
    prompt = prompt_str.format(
        question=question, label2uri=label2uri,database=database ,prefixes=prefixes, sparql=sparql)
    return {'text': prompt}


# Command line arguments
parser = argparse.ArgumentParser(description="Training script")
parser.add_argument("--output_dir", default="/home/julio/repos/text2sparql/assets/models/KQAPRO_LCQUAD_OpenLLAMA_contrastive",
                    help="Output directory for the trained model")
parser.add_argument("--train_data", default="/home/julio/repos/text2sparql/data/kqapro_lcquad_train.json",
                    help="Output directory for the trained model")
parser.add_argument(
    "--model_id", default="openlm-research/open_llama_7b_v2", help="Pre-trained model ID")
parser.add_argument(
    "--max_steps", default=2000, help="number if taining steps")
parser.add_argument("--device_map", default='auto',
                    type=str, help="Device map for model.")
parser.add_argument('--data_percentage', type=int, default=100, 
                    help='Percentage of data to load (between 0 and 100)')
parser.add_argument('--qlora_rank', type=int, default=16, 
                    help='Qlora rank')
parser.add_argument("--prompt_type", default='question',
                    type=str, help="Type of prompt to use")
parser.add_argument("--prefixes_file", default='/home/julio/repos/text2sparql/data/rikenmetadb/databases2prefixes.json',
                    type=str, help="Type of prompt to use")


args = parser.parse_args()

output_dir = args.output_dir
model_id = args.model_id

# generator = SPARQLQueryGenerator()

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)
if args.device_map == 'auto':
    device_map = 'auto'
else:
    device_map = {"": 0}

#Not working for nl2sparql env, need to check libraries
# Check if model_id is a local path or a Hugging Face model ID
# if os.path.exists(model_id):
#     print('<<<<<<<< Loading model from local path >>>>>>>>')
#     base_model = AutoPeftModelForCausalLM.from_pretrained(
#         model_id,
#         device_map=device_map
#     )

#     # base_model.train()
# else:#From huggingface
base_model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map=args.device_map
)

#Why does this was necesary? 
tokenizer = LlamaTokenizer.from_pretrained(model_id)
# tokenizer.add_special_tokens({'pad_token': '[PAD]'})
# base_model.resize_token_embeddings(len(tokenizer))
# print(base_model)


tokenizer.add_eos_token = True
tokenizer.pad_token_id = 0
tokenizer.padding_side = "left"



# Load the full dataset
train_data = load_data_from_file(args.train_data)

# Sample a percentage of the data if needed
if 0 < args.data_percentage < 100:
    # Calculate the number of samples
    n_samples = int(len(next(iter(train_data.values()))) * args.data_percentage / 100)
    print('Sampled #',n_samples)
    # Sample indices
    sampled_indices = sample(range(len(next(iter(train_data.values())))), n_samples)
    print('sampled indices',sampled_indices)
    # Build new sampled data
    sampled_train_data = {key: [values[i] for i in sampled_indices] for key, values in train_data.items()}

    train_dataset = Dataset.from_dict(sampled_train_data)

else:    
    train_dataset = Dataset.from_dict(train_data)
# dataset_dict = DatasetDict({"train": train_dataset, "test": []})
print(train_dataset)

databases2prefixes = {}

if args.prompt_type == 'question':
    generate_prompt = generate_prompt_question
elif args.prompt_type == 'label2uri':
    print('Using label2uri prompt')
    with open(args.prefixes_file, 'r') as json_file:
        databases2prefixes = json.load(json_file)
    generate_prompt = lambda example: generate_prompt_label2uri(example, databases2prefixes)
else:
    generate_prompt = generate_prompt_question

# Apply the mapping function to the dataset
mapped_datasets = train_dataset.map(generate_prompt)


print(mapped_datasets[0])   

r = args.qlora_rank
alpha = r*2
qlora_config = LoraConfig(
    r=r,
    lora_alpha=alpha,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

supervised_finetuning_trainer = SFTTrainer(
    base_model,
    train_dataset=mapped_datasets,
    args=transformers.TrainingArguments(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-5,
        max_steps=int(args.max_steps),
        output_dir=output_dir,
        optim="paged_adamw_8bit",
        fp16=True,
        save_total_limit=3  
    ),
    tokenizer=tokenizer,
    peft_config=qlora_config,
    dataset_text_field="text",
    max_seq_length=1024
)

# Train
supervised_finetuning_trainer.train()
