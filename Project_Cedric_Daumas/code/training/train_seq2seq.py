# %%
# %load_ext autoreload
# %autoreload 2

# %%
import argparse
from datasets import Dataset
from transformers import M2M100Tokenizer, M2M100ForConditionalGeneration, Seq2SeqTrainer, Seq2SeqTrainingArguments, DataCollatorForSeq2Seq
import torch
import os
import json
from random import sample
from text2sparql.prompts import question_label2uri_database_to_sparql

def load_data_from_file(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return {key: [d[key] for d in data] for key in data[0].keys()}

def generate_prompt_question(example):
    question = example['question']
    sparql = example["sparql"]
    prompt = f"### INSTRUCTION\nPlease convert the following context into an SPARQL query.\n\n### CONTEXT:\n{question}\n\n### SPARQL:\n{sparql}"
    return {'text': prompt}

def generate_prompt_label2uri(example):
    question = example['question']
    sparql = example["sparql"]
    label2uri = str(example["label2URI"])
    database = example["database"]

    prompt = question_label2uri_database_to_sparql.format(
        question=question, label2uri=label2uri, database=database, sparql='')
    return {'prompt': prompt}
            

# Command line arguments
parser = argparse.ArgumentParser(description="Training script")
parser.add_argument("--output_dir", default="/home/julio/repos/text2sparql/assets/models/M2M100",
                    help="Output directory for the trained model")
parser.add_argument("--train_data", default="/home/julio/repos/text2sparql/data/rikenmetadb/dataset_train.json", help="Path to the training data")
parser.add_argument("--model_id", default="facebook/m2m100_418M",
                    help="Pre-trained model ID")
parser.add_argument("--max_steps", default=2000, help="Number of training steps")
parser.add_argument("--device_map", default='auto', type=str, help="Device map for model.")
parser.add_argument('--data_percentage', type=int, default=100, help='Percentage of data to load (between 0 and 100)')
parser.add_argument("--prompt_type", default='label2uri', type=str, help="Type of prompt to use")

#Put '' when debugging
args = parser.parse_args()

output_dir = args.output_dir
model_id = args.model_id

# Load the model and tokenizer
model = M2M100ForConditionalGeneration.from_pretrained(model_id, device_map=args.device_map)
tokenizer = M2M100Tokenizer.from_pretrained(model_id)

# Load the full dataset
train_data = load_data_from_file(args.train_data)

# Sample a percentage of the data if needed
if 0 < args.data_percentage < 100:
    n_samples = int(len(next(iter(train_data.values()))) * args.data_percentage / 100)
    sampled_indices = sample(range(len(next(iter(train_data.values())))), n_samples)
    sampled_train_data = {key: [values[i] for i in sampled_indices] for key, values in train_data.items()}
    train_dataset = Dataset.from_dict(sampled_train_data)
else:    
    train_dataset = Dataset.from_dict(train_data)

if args.prompt_type == 'question':
    generate_prompt = generate_prompt_question
elif args.prompt_type == 'label2uri':
    generate_prompt = generate_prompt_label2uri
else:
    generate_prompt = generate_prompt_question

# %%
# Map the dataset to the prompt
mapped_datasets = train_dataset.map(generate_prompt)

#%%
# Preprocess/tokenize the data for model input
def preprocess_function(examples):
    model_inputs = tokenizer(examples["prompt"], max_length=128, truncation=True, padding="max_length")
    
    # Set the labels to be the same as the input (for seq2seq tasks, this might be different depending on your task)
    labels = tokenizer(examples["sparql"], max_length=128, truncation=True, padding="max_length")
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_datasets = mapped_datasets.map(preprocess_function, batched=True)
# Remove unnecessary columns,  keep them cause troubles
tokenized_datasets = tokenized_datasets.remove_columns(['label2URI', 'question', 'database', 'sparql', 'prompt'])

#%%
# Data collator for Seq2Seq models
data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

# Training arguments specific to Seq2Seq models
training_args = Seq2SeqTrainingArguments(
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    learning_rate=2e-5,
    max_steps=int(args.max_steps),
    output_dir=output_dir,
    optim="adamw_torch",
    fp16=True,
    save_total_limit=3,
    # evaluation_strategy="steps",
    save_steps=500,  # Adjust as necessary
    # eval_steps=500,  # Adjust as necessary
    predict_with_generate=True,  # Important for Seq2Seq models to generate text
    remove_unused_columns=False  # Do not remove columns since we handle preprocessing
)

# Seq2Seq Trainer
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

# Train
trainer.train()

# %%
