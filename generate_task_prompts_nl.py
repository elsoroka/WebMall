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


system_prompt = """You are an expert web navigation planner. Your role is to analyze a task goal and create a concise high-level strategy. You do not execute actions yourself; you provide a plan that a web agent will follow step by step.

## Instructions:
Given the task goal below, write a concise high-level plan as a numbered list of steps. \
Each step should describe a logical phase of the task (e.g., "Search for product X on store Y", \
"1. Search for Product P on Store S", "2. Add the cheapest option to cart"). \
Focus on strategy, not low-level browser interactions.

In your plan, refer to specific web URLs for stores, product names, and requirements for products. Only use the four provided webshops and the solutions page. Do not visit any other websites.
Make sure each step is self-contained with all the information necessary to execute it.
The steps will be provided to an LLM agent, and only one step will be visible at a time.
After each step, the LLM agent will make a note on its progress so it can retain information from previous steps.

Separate each step from the next with \\n\\n.

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

with open("webmall_prompts_nl.jsonl", "w") as outfile:
    seen_ids = set()
    for k,v in WEBMALL_BENCHMARKS.items():
        print(k)
        benchmark = v()
        for t_name in benchmark.env_args_list:
            if t_name.task_name in seen_ids:
                continue
            seen_ids.add(t_name.task_name)
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
"""
            obj = {"prompt":prompt,
            "id": t_name.task_name,
            "seed":t_name.task_seed,
            "kwargs": t_name.task_kwargs}
            outfile.write(json.dumps(obj) + '\n')