"""
Note: This script is a convenience script to launch experiments instead of using
the command line.

Copy this script and modify at will, but don't push your changes to the
repository.
"""

import os
import logging
from dotenv import load_dotenv
import bgym

from agentlab.agents.visualwebmall_agent.agent import WA_AGENT_4O
from agentlab.agents.webmall_generic_agent import (
    AGENT_4o_VISION,
    AGENT_4o_MINI,
    AGENT_4o,
    AGENT_CLAUDE_SONNET_35,
    AGENT_37_SONNET,
)
from webmall_overrides.study import WebMallStudy
from pathlib import Path
from datetime import datetime
from analyze_agentlab_results.aggregate_log_statistics import process_study_directory
from analyze_agentlab_results.summarize_study import summarize_all_tasks_in_subdirs


logging.getLogger().setLevel(logging.DEBUG)

from agentlab.agents import dynamic_prompting as dp

from agentlab.llm.llm_configs import CHAT_MODEL_ARGS_DICT

from agentlab.agents.generic_agent.generic_agent import (
    GenericAgent,
    GenericPromptFlags,
    GenericAgentArgs,
)
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
            multiaction=False,
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
FLAGS_AX_M.extra_instructions = "Use your memory to note down important information like the URLs of potential solutions and corresponding pricing information."

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

AGENT_5mini_AX_M = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-5-mini-2025-08-07"],
    flags=FLAGS_AX_M,
)

AGENT_5_AX_M = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-5-2025-08-07"],
    flags=FLAGS_AX_M,
)

AGENT_CLAUDE_AX_M = GenericAgentArgs(
    chat_model_args=CHAT_MODEL_ARGS_DICT["anthropic/claude-sonnet-4-20250514"],
    flags=FLAGS_AX_M,
)
AGENT_5_PLANNER = PlanningAgentArgs(
    planner_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-5-2025-08-07"],
    executor_model_args=CHAT_MODEL_ARGS_DICT["openai/gpt-5-2025-08-07"],
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

current_file = Path(__file__).resolve()
PATH_TO_DOT_ENV_FILE = current_file.parent / ".env"
load_dotenv(PATH_TO_DOT_ENV_FILE)


# choose your agent or provide a new agent
agent_args = [AGENT_41_PLANNER]

# ## select the benchmark to run on

#benchmark = "webmall_specific_product_search_v1.0"
# benchmark = "webmall_vague_product_search_v1.0"
# benchmark = "webmall_cheapest_product_search_v1.0"
#benchmark = "webmall_action_and_transaction_v1.0"
# benchmark = "webmall_end_to_end_v1.0"
#benchmark = "webmall_basic_v1.0"
benchmark = "webmall_partial_advanced_v1.0"

# Set reproducibility_mode = True for reproducibility
# this will "ask" agents to be deterministic. Also, it will prevent you from launching if you have
# local changes. For your custom agents you need to implement set_reproducibility_mode
reproducibility_mode = False

# Set relaunch = True to relaunch an existing study, this will continue incomplete
# experiments and relaunch errored experiments
relaunch = False

## Number of parallel jobs
n_jobs = 1  # Make sure to use 1 job when debugging in VSCode
# n_jobs = -1  # to use all available cores


if __name__ == "__main__":  # necessary for dask backend

    if reproducibility_mode:
        [a.set_reproducibility_mode() for a in agent_args]

    if relaunch:
        #  relaunch an existing study
        study = WebMallStudy.load_most_recent(contains=None)
        study.find_incomplete(include_errors=True)

    else:
        study = WebMallStudy(
            agent_args, benchmark, logging_level_stdout=logging.INFO, suffix="AX_M"
        )
        study_name = study.name
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        study_dir = f"{os.getenv('AGENTLAB_EXP_ROOT')}/{timestamp}_{study_name}/"
        study = WebMallStudy(
            agent_args,
            benchmark,
            logging_level_stdout=logging.INFO,
            dir=study_dir,
            suffix="AX_M",
        )

    parallel_backends = ["sequential", "ray"]
    study.run(
        n_jobs=n_jobs,
        parallel_backend=parallel_backends[1],
        strict_reproducibility=reproducibility_mode,
        n_relaunch=1,
    )

    if reproducibility_mode:
        study.append_to_journal(strict_reproducibility=True)

    summarize_all_tasks_in_subdirs(study_dir)
    process_study_directory(study_dir)
