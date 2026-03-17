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
Agents are configured via AgentLab's `GenericAgent` with flags:
- `use_ax` — accessibility tree observation
- `use_screenshot` / `use_som` — vision capabilities
- `use_memory` — memory module
- LLM model (GPT-4o, Claude Sonnet, etc.)

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
