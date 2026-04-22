# cursed hack import
from Browsergym.browsergym.webmall.src.browsergym.webmall.task import WebMallTask
#from WebMall.Browsergym.browsergym.core.src.browsergym.core import observation
from webmall_overrides.configs import WEBMALL_BENCHMARKS
# import dynamic prompting
import AgentLab.src.agentlab.agents.dynamic_prompting as dp
import json
from AgentLab.src.agentlab.llm.llm_utils import (
    Discussion,
    HumanMessage,
    SystemMessage
)


system_prompt = """You are an expert planner. Your task is to write a plan in Python code to automate a web interaction task. Do not solve the task yourself: only write the plan.
# Instructions
Use the provided Python functions to write a plan in Python code to reach the goal. Do not solve the task yourself; only write the plan. Write a simple plan without considering edge cases.

## Goal:
"""

obs_str = """
# Observation of current step:

## Currently open tabs:
Tab 0 (active tab):
    Title: WebMall - Submit Final Result
    URL: http://localhost:8085/

## AXTree:
Note: [bid] is the unique alpha-numeric identifier at the beginning of lines for each element in the AXTree. Always use bid to refer to elements in your actions.

Note: You can only interact with visible elements. If the "visible" tag is not
present, the element is not visible on the page.

RootWebArea \'WebMall - Submit Final Result\', focused
\t[7] main \'\', visible
\t\t[8] heading \'Welcome to WebMall\', visible
\t\t[9] paragraph \'\', visible
\t\t\tStaticText \'When you are done, type your final results into the text field below and click the "Submit Final Result" button. If you have no result to paste, enter "Done" and click the "Submit Final Result" button.\'
\t\t[11] textbox \'Type your final answer here...\', visible
\t\t[12] button \'Submit Final Result\', clickable, visible
\t\t[13] generic, visible, live=\'polite\', relevant=\'additions text\'

## Focused element:
bid=\'6\'


# History of interaction with the task:
"""
action_prompt = """
# Action space:

# Functions::
Your plan should make use of the following Python functions to interact with a web browser. Assume these functions handle all edge cases and error checking internally.

14 different types of actions are available.

noop(wait_ms: float = 1000)
search_on_page(search_page_url: str, search_text: str) -> str
open_page(url: str) -> bool
close_page() -> bool
go_back()
go_forward()
navigate_to_page(description: str) -> bool
extract_information_from_page(description: str) -> str
fill_text_field(field_description: str, text: str) -> bool
press_button(button_description: str) -> bool
select_option(bid: str, options: str | list[str])
generic_action(description: str) -> str
add_to_cart(url: str, item_description: str) -> bool
checkout(payment_and_shipping_information: str) -> bool
 Example:
press_button(\'The submit button\')
go_back()
add_to_cart(\'product_url\')
"""

with open("webmall_prompts.jsonl", "w") as outfile:
    for k,v in WEBMALL_BENCHMARKS.items():
        print(k)
        benchmark = v()
        for t_name in benchmark.env_args_list:
            t = None
            if t_name.task_kwargs:
                t = WebMallTask(task_id=t_name.task_name, seed=t_name.task_seed, **t_name.task_kwargs)
            else:
                t = t = WebMallTask(task_id=t_name.task_name, seed=t_name.task_seed)
            instruction = t.task_config['instruction'].replace("\\n", '\n')
            print(instruction)
            specific_task = t.task_config['task'].replace('\\n', '\n')
            print(specific_task)

            prompt = f"""{system_prompt}
        
{instruction}

{specific_task}

{obs_str}

{action_prompt}
"""
            obj = {"prompt":prompt,
            "id": t_name.task_name,
            "seed":t_name.task_seed,
            "kwargs": t_name.task_kwargs}
            outfile.write(json.dumps(obj) + '\n')