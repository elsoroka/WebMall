import json
import openai
from dotenv import load_dotenv
load_dotenv()
from tqdm import tqdm

client = openai.OpenAI()

def chat(prompt: str, model="gpt-5.1", temp=0.0) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temp
    )
    return response.choices[0].message.content.strip()


if __name__ == '__main__':
    with open("webmall_prompts.jsonl", "r") as infile:
        prompts = [json.loads(l) for l in infile.readlines()]

    MODEL = "gpt-5.1"
    TEMP = 0.0
    with open(f"webmall_plan_{MODEL}_{TEMP}.jsonl", "w") as outfile:

        for p in tqdm(prompts):
            response = chat(p['prompt'], model=MODEL, temp=TEMP)
            p['response'] = response
            outfile.write(json.dumps(p) + '\n')
