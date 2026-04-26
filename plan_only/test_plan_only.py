import json
import openai
from dotenv import load_dotenv
load_dotenv()
from tqdm import tqdm

example = """
Example: Make a plan to find the cheapest offer for Product P.
```
stores = ["http://localhost:8081/", "http://localhost:8082/", "http://localhost:8083/", "http://localhost:8084/"]
results = []

for store in stores:
    url_or_none = search_for_page(store, "Product P") # Return the product page URL or None if not found
    if url_or_none is not None:
        price = extract_information_from_page("Lowest price of the product")
        results.append((url_or_none, price))

selected_url = min(results, key=lambda x: x[1])[0]

open_page("http://localhost:3000/")
fill_text_field("Solution field", selected_url)
press_button("Submit Final Result")
```"""

def get_first_valid(response:str)->str:
  response = response.strip()
  if '```' in response:
    s = response.split('```')
    for i in range(len(s)):
      if len(s[i].strip()) == 0:
        continue
      if s[i].startswith("python"):
        s[i] = s[i][6:].strip() # clip this off
      try:
        byte_code = compile(s[i], "<user_code>", "exec")
        return s[i]
      except Exception as e:
        print(e)
  return None


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
    EXAMPLE = True
    with open(f"webmall_plan_{MODEL}_{TEMP}_Example_{EXAMPLE}.jsonl", "w") as outfile:

        for p in tqdm(prompts):
            response = chat(p['prompt'] + (example + '\n' if EXAMPLE else ''), model=MODEL, temp=TEMP)
            p['response'] = response
            p['clean_response'] = get_first_valid(response)
            outfile.write(json.dumps(p) + '\n')
