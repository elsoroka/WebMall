# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**WebMall** is a multi-shop e-commerce benchmark for evaluating LLM web agents. Agents must navigate 4 WooCommerce shops to find products, compare prices, add items to carts, and complete checkouts. Tasks range from exact product searches to vague requirement matching and finding cheaper alternatives.

Paper: https://arxiv.org/abs/2508.13024

## Setup

```bash
# Install dependencies (submodules)
cd Browsergym && make install   # Installs BrowserGym + Playwright browsers
cd AgentLab && pip install -e . # Installs AgentLab agent framework

# Configure environment
cp .env.example .env            # Fill in API keys and shop URLs

# Start the local shop infrastructure
cd docker_all && ./restore_all_and_deploy_local.sh
```

The two key submodules are:
- **Browsergym/**: Fork of BrowserGym containing the WebMall task definitions
- **AgentLab/**: Fork of AgentLab (agent runner/framework)

## Running the Benchmark

**Full study** (multiple agents × task sets, Ray-parallelized):
```bash
python run_webmall_study.py
```

**Single task** (debugging):
```bash
python run_single_task.py
# Edit task_name inside the file, e.g.: webmall.Webmall_Find_Specific_Product_Task6
```

Results are stored in `AGENTLAB_EXP_ROOT` (set in `.env`).

## Architecture

### Execution Flow
```
run_webmall_study.py
  → WebMallStudy (webmall_overrides/study.py)
    → WebMallBenchmark (webmall_overrides/benchmark.py)
      → task configs (webmall_overrides/configs.py)
    → ExpArgsWebMall / EnvArgsWebMall (webmall_overrides/exp_args.py, env_args.py)
      → WebMallTask (Browsergym/browsergym/webmall/src/browsergym/webmall/task.py)
        → task_sets.json (199KB, ~50 task categories, loaded at runtime)
        → Evaluators (evaluator.py): StringEvaluator, URLEvaluator, CartEvaluator, CheckoutEvaluator
```

### Key Components

**`webmall_overrides/`** — WebMall-specific integration layer on top of AgentLab/BrowserGym:
- `study.py`: `WebMallStudy` extends AgentLab's `Study`; registers WEBMALL_BENCHMARKS
- `benchmark.py`: `WebMallBenchmark` handles "webmall" backend string (not in upstream BrowserGym)
- `configs.py`: Defines all benchmark sets (task groups × difficulty levels)
- `env_args.py` / `exp_args.py`: Override BrowserGym env creation for WebMall

**`Browsergym/browsergym/webmall/`** — Task definitions (inside submodule):
- `task.py`: `WebMallTask` — loads tasks from `task_sets.json`, handles URL substitution, scoring
- `evaluator.py`: Evaluation logic for different task types
- `__init__.py`: Dynamically registers all tasks as Gym environments (`browsergym/webmall.<TaskName>`)

**`docker_all/`** — Docker Compose stack:
- 4 WordPress/WooCommerce shops (ports 8081–8084), 4 MariaDB instances, Elasticsearch, Nginx frontend (8085)
- Bitnami images with persistent named volumes

**`AgentLab/src/agentlab/agents/webmall_generic_agent/`** — Custom agent implementations (key fork additions):
- `generic_agent.py` + `generic_agent_prompt.py`: Single-stage agent that builds a prompt from the current observation and calls one LLM to predict the next action.
- `planning_agent.py` + `planner_agent_prompt.py`: **Work in progress.** Two-stage hierarchical agent. A **planner LLM** generates a Python code plan (validated via `compile()`); an **executor LLM** runs that plan inside a background thread using a `ThreadPoolExecutor`, communicating with the main thread via action/observation queues. Action functions available to the plan: `search_for_page`, `fill_text_field`, `press_button`, `select_option`, `add_to_cart`, `checkout`, `generic_action`, etc.
- `agent_configs.py`: Pre-built `AgentArgs` instances for all supported models (`AGENT_4o`, `AGENT_CLAUDE_SONNET_35`, `AGENT_37_SONNET`, `AGENT_o3_MINI`, `AGENT_5_PLANNER`, etc.). `AGENT_5_PLANNER` pairs a GPT-5 planner with a GPT-4o executor.
- `reproducibility_agent.py`: `ReproAgent` replays prior run traces using a mock LLM (`ReproChatModel`), useful for deterministic re-execution.

**Prompt flags** (`GenericPromptFlags` / `PlannerPromptFlags`) controlling agent behavior:
- `obs.use_ax_tree`, `obs.use_screenshot`, `obs.use_som` — observation modalities
- `use_thinking`, `use_plan`, `use_memory`, `use_hints` — reasoning modules
- `max_prompt_tokens` — token budget for prompt truncation

**Fork-specific additions to upstream AgentLab** (see `dynamic_prompting.py`):
- `PlannerGoalInstructions`, `PlannerSystemPromptElement`, `PlannerActionPromptElement` classes added for the two-stage planning pipeline

**`analyze_agentlab_results/`** — Post-run analysis scripts:
- `aggregate_log_statistics.py`, `summarize_study.py`, `task_logs_extractor.py`

### Benchmark Task Categories
Defined in `webmall_overrides/configs.py`:
- `webmall_specific_product_search_v1.0` — Find exact products (12 tasks)
- `webmall_cheapest_product_search_v1.0` — Find cheapest offers (10 tasks)
- `webmall_vague_product_search_v1.0` — Vague/open-ended requirements (11 tasks)
- `webmall_action_and_transaction_v1.0` — Add to cart + checkout (15 tasks)
- `webmall_end_to_end_v1.0` — Full end-to-end tasks

### Agent Configuration (in run scripts)
Import pre-built configs from `AgentLab/src/agentlab/agents/webmall_generic_agent/agent_configs.py`:
```python
from agentlab.agents.webmall_generic_agent.agent_configs import AGENT_4o, AGENT_5_PLANNER
```
Use `GenericAgent` for single-stage or `PlanningAgent` for two-stage (planner + executor). Pass `AgentArgs` to `WebMallStudy` alongside the benchmark config.

## Environment Variables

Shop URLs default to `localhost:8081–8085` for local Docker setup. For server deployment use the server-side script (`restore_all_and_deploy_server.sh`) and update URLs accordingly. WooCommerce REST API credentials (consumer key/secret) and application passwords per shop are required.

## Docker Management

```bash
cd docker_all
docker compose up -d           # Start all services
docker compose down            # Stop all services
./backup_all.sh                # Backup shop databases
./start_webmall.sh             # Quick start (if present)
./stop_webmall.sh              # Quick stop (if present)
```

See `docker_all/README.md` for troubleshooting and reset procedures.
