# Running WebMall with a Local vLLM Server (HPC Cluster via SSH Tunnel)

This guide covers serving a model with vLLM on an HPC cluster (SLURM + Apptainer) and connecting to it from your local machine through an SSH tunnel.

## Overview

The HPC cluster does not have Docker, so vLLM is run inside an Apptainer container on a compute node. Port 8000 is forwarded to `localhost:8000` on your local machine via an SSH tunnel, and WebMall connects to it transparently using the standard OpenAI-compatible API.

```
Local machine                    Cluster compute node
┌────────────────┐  SSH tunnel   ┌───────────────────────┐
│ WebMall agent  │◄─────────────►│ vLLM (Apptainer)      │
│ localhost:8000 │               │ port 8000             │
└────────────────┘               └───────────────────────┘
```

---

## 1. Start vLLM on the Cluster

SSH into the cluster and request a GPU compute node via SLURM:

```bash
srun --time=24:00:00 --mem=40G --cpus-per-task=8 --gpus=1 --pty bash
```

Pull the vLLM Apptainer image (one-time; takes a few minutes):

```bash
export OPENSSL_CONF=/dev/null   # required for apptainer pull on this cluster
apptainer pull vllm.sif docker://vllm/vllm-openai:latest
```

Serve a model (example: Qwen3-Coder-30B-A3B-Instruct-FP8):

```bash
export OPENSSL_CONF=/dev/null
apptainer exec --nv \
    --bind $HOME/.cache/huggingface:/root/.cache/huggingface \
    vllm.sif \
    vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
        --port 8000 \
        --max-model-len 32768 \
        --gpu-memory-utilization 0.95
```

Other pre-configured models — substitute the model name above:

| Agent constant              | Model name                                      |
|-----------------------------|-------------------------------------------------|
| `AGENT_VLLM_DEEPSEEK_6_7B`  | `deepseek-ai/deepseek-coder-6.7b-instruct`      |
| `AGENT_VLLM_DEEPSEEK_33B`   | `deepseek-ai/deepseek-coder-33b-instruct`       |
| `AGENT_VLLM_QWEN25_7B`      | `Qwen/Qwen2.5-Coder-7B-Instruct`               |
| `AGENT_VLLM_QWEN3_30B`      | `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`        |

> **Note:** Only one model can be served at a time since all four agent configs share the same URL.

---

## 2. Set Up the SSH Tunnel

In a separate terminal on your **local machine**, forward the cluster compute node's port 8000 to localhost:

```bash
# Replace <cluster-login> and <compute-node> with your actual hostnames
ssh -L 8000:<compute-node>:8000 <cluster-login>
```

If you are already SSHed into the login node and need to hop to the compute node:

```bash
# From the login node
ssh -L 8000:localhost:8000 <compute-node>
```

Keep this terminal open for the duration of the benchmark run.

---

## 3. Configure WebMall

No `.env` changes are needed if the tunnel is bound to `localhost:8000` (the default). To use a different port, add `VLLM_API_URL` to your `.env`:

```bash
VLLM_API_URL=http://localhost:8000/v1
```

No API key is required — vLLM does not enforce authentication by default.

---

## 4. Run the Benchmark

In `run_single_task.py`, set the active agent:

```python
agent = AGENT_VLLM_QWEN3_30B
```

Then run:

```bash
source ../venv312/bin/activate
python run_single_task.py
```

Or use `run_webmall_study.py` for a full study — import from `agent_configs.py`:

```python
from agentlab.agents.webmall_generic_agent.agent_configs import AGENT_VLLM_QWEN3_30B

agent_args = [AGENT_VLLM_QWEN3_30B]
```

All vLLM agents are configured as `PlanningAgentArgs` (planner + executor both using the local model).
