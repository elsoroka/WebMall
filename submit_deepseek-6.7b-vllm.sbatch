#!/bin/sh  
#SBATCH --job-name=deepseek-coder-6.7b-vllm
#SBATCH -p batch  
#SBATCH --nodes=1
#SBATCH -A marlowe-m000186-pm05
#SBATCH -G 1
#SBATCH -c 2
#SBATCH --mem-per-gpu=64G
#SBATCH --time=0:30:00
#SBATCH --output=vllm_deepseek-coder-6.7b-instruct_%A.out
#SBATCH --error=vllm_deepseek-coder-6.7b-instruct_error_%A.out
#SBATCH --export=ALL

module load conda
CONDA_BASE="/marlowe/apps/Mambaforge/24.3.0-0"
eval "$($CONDA_BASE/bin/conda shell.bash hook)"
conda activate /scratch/m000186/esoroka/

vllm serve "deepseek-ai/deepseek-coder-6.7b-instruct" --port 8000 &

echo "Waiting for vLLM to be ready..."
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
    sleep 5
done
echo "vLLM is ready"

# Keep the job alive for the duration of the time limit
wait
