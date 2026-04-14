"""
Script to run a single or set of specific tasks
"""

import logging
import bgym
from dotenv import load_dotenv
from pathlib import Path
from webmall_overrides.env_args import EnvArgsWebMall
from webmall_overrides.exp_args import ExpArgsWebMall

from agentlab.agents.visualwebmall_agent.agent import WA_AGENT_4O
from agentlab.agents.generic_agent import AGENT_4o_VISION

from agentlab.agents.most_basic_agent.most_basic_agent import MostBasicAgentArgs
from agentlab.llm.llm_configs import CHAT_MODEL_ARGS_DICT

from agentlab.experiments.launch_exp import run_experiments

from agentlab.agents import dynamic_prompting as dp
from agentlab.experiments import args
from agentlab.llm.llm_configs import CHAT_MODEL_ARGS_DICT

from agentlab.agents.generic_agent.generic_agent import GenericAgent, GenericPromptFlags, GenericAgentArgs
from agentlab.agents.webmall_generic_agent.planning_agent import PlanningAgentArgs

FLAGS_default = GenericPromptFlags(
    obs=dp.ObsFlags(
        use_html=False,
        use_ax_tree=True,
        use_focused_element=True,
        use_error_logs=True,
        use_history=True,
        use_past_error_logs=False,
        use_action_history=True,
        use_think_history=True,
        use_diff=False,
        html_type="pruned_html",
        use_screenshot=False,
        use_som=False,
        extract_visible_tag=True,
        extract_clickable_tag=True,
        extract_coords="False",
        filter_visible_elements_only=False,
    ),
    action=dp.ActionFlags(
        action_set=bgym.HighLevelActionSetArgs(
            subsets=["bid"],
            multiaction=True,
        ),
        long_description=False,
        individual_examples=False,
    ),
    use_plan=False,
    use_criticise=False,
    use_thinking=True,
    use_memory=False,
    use_concrete_example=True,
    use_abstract_example=True,
    use_hints=True,
    enable_chat=False,
    max_prompt_tokens=60_000,
    be_cautious=True,
    extra_instructions=None,
    )

FLAGS_AX = FLAGS_default.copy()

FLAGS_V = FLAGS_default.copy()
FLAGS_V.obs.use_screenshot = True
FLAGS_V.obs.use_som = True
FLAGS_V.obs.use_ax_tree = False

FLAGS_AX_V = FLAGS_default.copy()
FLAGS_AX_V.obs.use_screenshot = True
FLAGS_AX_V.obs.use_som = True

FLAGS_AX_M = FLAGS_default.copy()
FLAGS_AX_M.use_memory = True
FLAGS_AX_M.extra_instructions = 'Use your memory to note down important information like the URLs of potential solutions and corresponding pricing information.'

AGENT_41_AX = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-4.1-2025-04-14"],
    flags=FLAGS_AX,
)

AGENT_CLAUDE_AX = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["anthropic/claude-sonnet-4-20250514"],
    flags=FLAGS_AX,
)

AGENT_41_V = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-4.1-2025-04-14"],
    flags=FLAGS_V,
)

AGENT_CLAUDE_V = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["anthropic/claude-sonnet-4-20250514"],
    flags=FLAGS_V,
)

AGENT_41_AX_V = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-4.1-2025-04-14"],
    flags=FLAGS_AX_V,
)

AGENT_CLAUDE_AX_V = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["anthropic/claude-sonnet-4-20250514"],
    flags=FLAGS_AX_V,
)

AGENT_41_AX_M = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-4.1-2025-04-14"],
    flags=FLAGS_AX_M,
)

AGENT_CLAUDE_AX_M = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["anthropic/claude-sonnet-4-20250514"],
    flags=FLAGS_AX_M,
)
AGENT_5_PLANNER = PlanningAgentArgs(
    planner_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-5-2025-08-07"],
    executor_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-4o-2024-05-13"],
    flags=FLAGS_AX,
)
AGENT_41_PLANNER = PlanningAgentArgs(
    planner_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-4.1-2025-04-14"],
    executor_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-4.1-2025-04-14"],
    flags=FLAGS_AX,
)

AGENT_4o_PLANNER = PlanningAgentArgs(
    planner_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-4o-2024-05-13"],
    executor_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-4o-2024-05-13"],
    flags=FLAGS_AX,
)


# example for a single task
env_args = EnvArgsWebMall(
    task_name="webmall.Webmall_Find_Specific_Product_Task6",
    task_seed=0,
    max_steps=60,
    headless=True,
    record_video=False
)



agent = AGENT_41_PLANNER
agent.set_benchmark(bgym.DEFAULT_BENCHMARKS["webarena"](), demo_mode="off")

#chat_model_args = CHAT_MODEL_ARGS_DICT["openai/gpt-4.1-2025-04-14"]
#chat_model_args = CHAT_MODEL_ARGS_DICT["anthropic/claude-sonnet-4-20250514"]

exp_args = [
    ExpArgsWebMall(
        agent_args=agent,
        env_args=env_args,
        logging_level=logging.INFO,
    ),
]

current_file = Path(__file__).resolve()
PATH_TO_DOT_ENV_FILE = current_file.parent / ".env"
load_dotenv(PATH_TO_DOT_ENV_FILE)

if __name__ == "__main__":
    run_experiments(n_jobs=1, exp_args_list=exp_args, study_dir="task_results", parallel_backend="sequential")
