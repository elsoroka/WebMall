try:
    from task_logs_extractor import summarize_single_task
except ImportError:
    from .task_logs_extractor import summarize_single_task
import os
import json
import re
import csv
from collections import defaultdict

STUDY_RESULTS_DIR = "../AgentLab/study_results/final"


def calculation_results(benchmark_solutions, model_solution):
    """
    Calculate task completion, precision, and recall metrics.

    Args:
        benchmark_solutions: List of sets containing benchmark solutions
        model_solution: List of sets containing model solution

    Returns:
        dict: Contains avg_task_completion_rate, avg_precision, avg_recall, avg_f1_score
    """
    if len(benchmark_solutions) != len(model_solution):
        raise ValueError(
            "benchmark_solutions and model_solution must have the same length"
        )

    if len(benchmark_solutions) == 0:
        return {
            "avg_task_completion_rate": 0.0,
            "avg_precision": 0.0,
            "avg_recall": 0.0,
            "avg_f1_score": 0.0,
        }

    task_completions = []
    precisions = []
    recalls = []

    for benchmark_set, model_set in zip(benchmark_solutions, model_solution):
        # Convert to sets if they aren't already
        benchmark_set = set(benchmark_set) if benchmark_set is not None else set()
        model_set = set(model_set) if model_set is not None else set()

        # Task completion: 1 if exact match, 0 otherwise
        task_completion = 1 if benchmark_set == model_set else 0
        task_completions.append(task_completion)

        # Precision: intersection / model_set size
        if len(model_set) > 0:
            precision = len(benchmark_set.intersection(model_set)) / len(model_set)
        else:
            precision = 0.0
        precisions.append(precision)

        # Recall: intersection / benchmark_set size
        if len(benchmark_set) > 0:
            recall = len(benchmark_set.intersection(model_set)) / len(benchmark_set)
        else:
            recall = 0.0
        recalls.append(recall)

    # Calculate aggregated metrics
    avg_task_completion_rate = sum(task_completions) / len(benchmark_solutions)
    avg_precision = sum(precisions) / len(benchmark_solutions)
    avg_recall = sum(recalls) / len(benchmark_solutions)

    # Calculate F1 score with zero division protection
    if avg_precision + avg_recall > 0:
        avg_f1_score = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall)
    else:
        avg_f1_score = 0.0

    return {
        "avg_task_completion_rate": avg_task_completion_rate,
        "avg_precision": avg_precision,
        "avg_recall": avg_recall,
        "avg_f1_score": avg_f1_score,
    }


def extract_task_type(subdir_name):
    try:
        task_part = subdir_name.split(".")[-1]
        match = re.match(r"^(.*?_Task)\d+(?:_\d+){0,2}$", task_part)
        return match.group(1) if match else "Unknown_Task"
    except Exception:
        return "Unknown_Task"


def read_goal_achievement_data(subdir, task_type=None):
    """Read goal achievement data from goal_achievement.csv and return raw solutions

    Args:
        subdir: Directory containing the goal achievement data
        task_type: Task type to determine if penalties should be excluded
    """
    goal_achievement_path = os.path.join(subdir, "goal_achievement.csv")

    if not os.path.exists(goal_achievement_path):
        return {
            "benchmark_solution": set(),
            "model_solution": set(),
        }

    try:
        with open(goal_achievement_path, "r") as f:
            reader = csv.DictReader(f)

            # Group goals by answer vs checkpoint
            answer_goals = {}
            checkpoint_goals = {}

            for row in reader:
                goal_desc = row.get("goal_description", "")
                achieved = row.get("achieved", "").lower() == "true"

                if "answer" in goal_desc.lower():
                    answer_goals[goal_desc] = achieved
                else:
                    checkpoint_goals[goal_desc] = achieved

            # Read wrong solutions from penalties.csv
            wrong_solutions = []
            # Exclude penalties for specific task types
            exclude_penalties = task_type in [
                "Webmall_Add_To_Cart_Task",
                "Webmall_Checkout_Task",
                "Webmall_EndToEnd_Task",
            ]

            if not exclude_penalties:
                penalties_path = os.path.join(subdir, "penalties.csv")
                if os.path.exists(penalties_path):
                    try:
                        with open(penalties_path, "r") as f:
                            penalty_reader = csv.DictReader(f)
                            for row in penalty_reader:
                                wrong_solutions_str = row.get("wrong_solutions", "")
                                if wrong_solutions_str:
                                    wrong_solutions.extend(
                                        wrong_solutions_str.split("|")
                                    )
                    except Exception as e:
                        print(f"⚠️ Error reading penalties.csv in {subdir}: {e}")

            # For WebMall tasks, we need to extract benchmark and model solutions
            benchmark_solution = set()
            model_solution = set()

            # Extract answer goals as sets
            if answer_goals:
                benchmark_solution = set(answer_goals.keys())  # All expected answers

                # Model solution includes both correct answers and wrong answers
                correct_answers = set(
                    [goal for goal, achieved in answer_goals.items() if achieved]
                )
                wrong_answers = set(wrong_solutions)
                model_solution = correct_answers.union(wrong_answers)

            return {
                "benchmark_solution": benchmark_solution,
                "model_solution": model_solution,
            }

    except Exception as e:
        print(f"⚠️ Error reading goal_achievement.csv in {subdir}: {e}")
        return {
            "benchmark_solution": set(),
            "model_solution": set(),
        }


def read_penalties_data(subdir):
    """Read penalties data from penalties.csv"""
    penalties_path = os.path.join(subdir, "penalties.csv")
    penalty_data = {"penalty": 0.0, "wrong_solutions": []}

    if os.path.exists(penalties_path):
        try:
            with open(penalties_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    penalty_value = row.get("penalty", 0)
                    penalty_data["penalty"] = (
                        float(penalty_value) if penalty_value not in ["None"] else 0.0
                    )
                    wrong_solutions_str = row.get("wrong_solutions", "")
                    if wrong_solutions_str:
                        penalty_data["wrong_solutions"] = wrong_solutions_str.split("|")

            return penalty_data
        except Exception as e:
            print(f"⚠️ Error reading penalties.csv in {subdir}: {e}")

    return penalty_data


def read_summary_info_data(subdir):
    """Read token, cost, and runtime data from summary_info.json"""
    summary_info_path = os.path.join(subdir, "summary_info.json")
    summary_info_data = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cost": 0.0,
        "step_elapsed": 0.0,
        "agent_elapsed": 0.0,
    }

    if os.path.exists(summary_info_path):
        try:
            with open(summary_info_path, "r") as f:
                data = json.load(f)
                summary_info_data["input_tokens"] = data.get(
                    "stats.cum_input_tokens", 0
                )
                summary_info_data["output_tokens"] = data.get(
                    "stats.cum_output_tokens", 0
                )
                summary_info_data["cost"] = data.get("stats.cum_cost", 0.0)
                summary_info_data["step_elapsed"] = data.get(
                    "stats.cum_step_elapsed", 0.0
                )
                summary_info_data["agent_elapsed"] = data.get(
                    "stats.cum_agent_elapsed", 0.0
                )

            return summary_info_data
        except Exception as e:
            print(f"⚠️ Error reading summary_info.json in {subdir}: {e}")

    return summary_info_data


def summarize_all_tasks_in_subdirs(root_directory):
    task_results = []
    # Store solutions by task type for later calculation
    solutions_by_task_type = defaultdict(
        lambda: {"benchmark_solutions": [], "model_solutions": []}
    )

    for subdir, dirs, files in os.walk(root_directory):
        if any(f.startswith("step_") and f.endswith(".pkl.gz") for f in files):
            print(f"📁 Summarizing task in: {subdir}")
            summarize_single_task(subdir)

            task_summary_path = os.path.join(subdir, "task_summary.json")
            subdir_name = os.path.basename(subdir)

            # Extract task type first so we can pass it to read_goal_achievement_data
            task_type = extract_task_type(subdir_name)

            # Collect goal and penalty data
            goal_data = read_goal_achievement_data(subdir, task_type)
            penalty_data = read_penalties_data(subdir)
            summary_info_data = read_summary_info_data(subdir)

            # Store solutions by task type for later calculation
            solutions_by_task_type[task_type]["benchmark_solutions"].append(
                goal_data["benchmark_solution"]
            )
            solutions_by_task_type[task_type]["model_solutions"].append(
                goal_data["model_solution"]
            )

            # Calculate individual task metrics
            individual_metrics = calculation_results(
                [goal_data["benchmark_solution"]], [goal_data["model_solution"]]
            )

            task_result = {
                "task": subdir_name,
                "task_type": task_type,
                "critical_error": False,
                "num_action_errors": 0,
                "cumulative_reward": 0.0,
                "benchmark_solution": goal_data["benchmark_solution"],
                "model_solution": goal_data["model_solution"],
                "penalty": penalty_data["penalty"],
                "terminated": False,
                "truncated": False,
                "num_steps": 0,
                "input_tokens": summary_info_data["input_tokens"],
                "output_tokens": summary_info_data["output_tokens"],
                "cost": summary_info_data["cost"],
                "step_elapsed": summary_info_data["step_elapsed"],
                "agent_elapsed": summary_info_data["agent_elapsed"],
                "task_completion": individual_metrics["avg_task_completion_rate"],
                "precision": individual_metrics["avg_precision"],
                "recall": individual_metrics["avg_recall"],
                "f1_score": individual_metrics["avg_f1_score"],
            }

            if os.path.exists(task_summary_path):
                try:
                    with open(task_summary_path, "r") as f:
                        task_data = json.load(f)

                    steps = (
                        task_data["steps"]
                        if isinstance(task_data, dict) and "steps" in task_data
                        else task_data
                    )
                    sorted_keys = sorted(steps.keys(), key=lambda x: int(x))

                    # Count the number of steps
                    task_result["num_steps"] = len(sorted_keys)

                    if sorted_keys:
                        last_step_data = steps[sorted_keys[-1]]
                        if last_step_data.get("err_msg") and last_step_data.get(
                            "stack_trace"
                        ):
                            task_result["critical_error"] = True

                        # Track terminated/truncated status from the last step
                        if last_step_data.get("finished") == "terminated":
                            task_result["terminated"] = True
                        elif last_step_data.get("finished") == "truncated":
                            task_result["truncated"] = True

                    for step in steps.values():
                        if "action_error" in step:
                            task_result["num_action_errors"] += 1
                        if "cumulative_reward" in step:
                            task_result["cumulative_reward"] = step["cumulative_reward"]

                except Exception as e:
                    print(f"⚠️ Could not process task_summary.json in {subdir}: {e}")

            task_results.append(task_result)

    # ------------------- CALCULATE METRICS PER TASK TYPE -----------------------
    # Calculate metrics per task type using all solutions for that task type
    task_type_metrics = {}
    for task_type, solutions in solutions_by_task_type.items():
        if solutions["benchmark_solutions"] and solutions["model_solutions"]:
            metrics = calculation_results(
                solutions["benchmark_solutions"], solutions["model_solutions"]
            )
            task_type_metrics[task_type] = metrics
        else:
            task_type_metrics[task_type] = {
                "avg_task_completion_rate": 0.0,
                "avg_precision": 0.0,
                "avg_recall": 0.0,
                "avg_f1_score": 0.0,
            }

    # Update task results with calculated metrics
    for result in task_results:
        task_type = result["task_type"]
        metrics = task_type_metrics.get(
            task_type,
            {
                "avg_task_completion_rate": 0.0,
                "avg_precision": 0.0,
                "avg_recall": 0.0,
                "avg_f1_score": 0.0,
            },
        )
        result["avg_task_completion_rate"] = metrics["avg_task_completion_rate"]
        result["avg_precision"] = metrics["avg_precision"]
        result["avg_recall"] = metrics["avg_recall"]
        result["avg_f1_score"] = metrics["avg_f1_score"]

    # ------------------- AGGREGATE BY TASK TYPE -----------------------
    type_summary = {}
    full_summary = {}

    for result in task_results:
        task_type = result["task_type"]
        subtype_match = re.search(r"(Task\d+)", result["task"])
        subtype = subtype_match.group(1) if subtype_match else "Unknown"

        if task_type not in type_summary:
            type_summary[task_type] = {
                "count": 0,
                "subtypes": set(),
                "critical_errors": 0,
                "action_errors": 0,
                "terminated_count": 0,
                "truncated_count": 0,
                "total_steps": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost": 0.0,
                "total_step_elapsed": 0.0,
                "total_agent_elapsed": 0.0,
                "total_time_elapsed": 0.0,
            }
            full_summary[task_type] = {"summary": {}, "tasks": []}

        ts = type_summary[task_type]
        ts["count"] += 1
        ts["subtypes"].add(subtype)
        ts["critical_errors"] += int(result["critical_error"])
        ts["action_errors"] += result["num_action_errors"]
        ts["terminated_count"] += int(result["terminated"])
        ts["truncated_count"] += int(result["truncated"])
        ts["total_steps"] += result["num_steps"]
        ts["total_input_tokens"] += result["input_tokens"]
        ts["total_output_tokens"] += result["output_tokens"]
        ts["total_cost"] += result["cost"]
        ts["total_step_elapsed"] += result["step_elapsed"]
        ts["total_agent_elapsed"] += result["agent_elapsed"]
        ts["total_time_elapsed"] = ts["total_step_elapsed"] + ts["total_agent_elapsed"]

        # Create a clean copy of the result for JSON serialization (remove sets, cumulative_reward, and task-type-level metrics)
        clean_result = {
            k: v
            for k, v in result.items()
            if k
            not in [
                "benchmark_solution",
                "model_solution",
                "cumulative_reward",
                "avg_task_completion_rate",
                "avg_precision",
                "avg_recall",
                "avg_f1_score",
            ]
        }
        full_summary[task_type]["tasks"].append(clean_result)

    # ------------------- PRINT PER-TASK-TYPE STATS -------------------
    print("\n📊 Task-Type Summary:\n")
    export_type_summary = {}

    for task_type in sorted(type_summary.keys()):
        ts = type_summary[task_type]
        count = ts["count"]
        subtype_count = len(ts["subtypes"])
        avg_critical = ts["critical_errors"] / count
        avg_action = ts["action_errors"] / count

        # Get the pre-calculated metrics for this task type
        task_type_metric = task_type_metrics.get(
            task_type,
            {
                "avg_task_completion_rate": 0.0,
                "avg_precision": 0.0,
                "avg_recall": 0.0,
                "avg_f1_score": 0.0,
            },
        )

        terminated_rate = ts["terminated_count"] / count
        truncated_rate = ts["truncated_count"] / count
        avg_steps = ts["total_steps"] / count
        avg_input_tokens = ts["total_input_tokens"] / count
        avg_output_tokens = ts["total_output_tokens"] / count
        avg_cost = ts["total_cost"] / count
        avg_step_elapsed = ts["total_step_elapsed"] / count
        avg_agent_elapsed = ts["total_agent_elapsed"] / count
        avg_time_elapsed = ts["total_time_elapsed"] / count

        print(f"🔧 {task_type}  ({subtype_count} subtypes, {count} total runs)")
        print(f"   ❗ Avg Critical Errors: {avg_critical:.2f}")
        print(f"   ⚠️  Avg Action Errors: {avg_action:.2f}")
        print(
            f"   ✅ Avg Task Completion Rate: {task_type_metric['avg_task_completion_rate']:.2f}"
        )
        print(f"   🎯 Avg Precision: {task_type_metric['avg_precision']:.2f}")
        print(f"   🔄 Avg Recall: {task_type_metric['avg_recall']:.2f}")
        print(f"   📊 Avg F1 Score: {task_type_metric['avg_f1_score']:.2f}")
        print(f"   🏁 Terminated Rate: {terminated_rate:.2f}")
        print(f"   ⏱️ Truncated Rate: {truncated_rate:.2f}")
        print(f"   🔢 Avg Steps: {avg_steps:.2f}")
        print(f"   ⏰ Avg Step Runtime: {avg_step_elapsed:.2f}s")
        print(f"   🤖 Avg Agent Runtime: {avg_agent_elapsed:.2f}s")
        print(f"   ⏱️ Avg Total Runtime: {avg_time_elapsed:.2f}s")
        print(f"   📥 Avg Input Tokens: {avg_input_tokens:.0f}")
        print(f"   📤 Avg Output Tokens: {avg_output_tokens:.0f}")
        print(f"   💰 Avg Cost: ${avg_cost:.4f}\n")

        # Store clean summary
        export_type_summary[task_type] = {
            "num_subtypes": subtype_count,
            "num_runs": count,
            "avg_critical_errors": avg_critical,
            "avg_action_errors": avg_action,
            "avg_task_completion_rate": task_type_metric["avg_task_completion_rate"],
            "avg_precision": task_type_metric["avg_precision"],
            "avg_recall": task_type_metric["avg_recall"],
            "avg_f1_score": task_type_metric["avg_f1_score"],
            "terminated_rate": terminated_rate,
            "truncated_rate": truncated_rate,
            "avg_steps": avg_steps,
            "avg_step_elapsed": avg_step_elapsed,
            "avg_agent_elapsed": avg_agent_elapsed,
            "avg_time_elapsed": avg_time_elapsed,
            "avg_input_tokens": avg_input_tokens,
            "avg_output_tokens": avg_output_tokens,
            "avg_cost": avg_cost,
        }

        # Attach to full summary
        full_summary[task_type]["summary"] = export_type_summary[task_type]

    # ------------------- CALCULATE OVERALL METRICS ACROSS ALL TASK TYPES -----------------------
    # Combine all benchmark and model solutions from all task types
    all_benchmark_solutions = []
    all_model_solutions = []

    for task_type, solutions in solutions_by_task_type.items():
        all_benchmark_solutions.extend(solutions["benchmark_solutions"])
        all_model_solutions.extend(solutions["model_solutions"])

    # Calculate overall metrics
    if all_benchmark_solutions and all_model_solutions:
        overall_metrics = calculation_results(
            all_benchmark_solutions, all_model_solutions
        )
    else:
        overall_metrics = {
            "avg_task_completion_rate": 0.0,
            "avg_precision": 0.0,
            "avg_recall": 0.0,
            "avg_f1_score": 0.0,
        }

    # Calculate overall aggregated statistics
    total_tasks = len(task_results)
    total_critical_errors = sum(ts["critical_errors"] for ts in type_summary.values())
    total_action_errors = sum(ts["action_errors"] for ts in type_summary.values())
    total_terminated = sum(ts["terminated_count"] for ts in type_summary.values())
    total_truncated = sum(ts["truncated_count"] for ts in type_summary.values())
    total_steps = sum(ts["total_steps"] for ts in type_summary.values())
    total_input_tokens = sum(ts["total_input_tokens"] for ts in type_summary.values())
    total_output_tokens = sum(ts["total_output_tokens"] for ts in type_summary.values())
    total_cost = sum(ts["total_cost"] for ts in type_summary.values())
    total_step_elapsed = sum(ts["total_step_elapsed"] for ts in type_summary.values())
    total_agent_elapsed = sum(ts["total_agent_elapsed"] for ts in type_summary.values())
    total_time_elapsed = total_step_elapsed + total_agent_elapsed

    overall_summary = {
        "num_task_types": len(type_summary),
        "num_total_runs": total_tasks,
        "avg_critical_errors": (
            total_critical_errors / total_tasks if total_tasks > 0 else 0.0
        ),
        "avg_action_errors": (
            total_action_errors / total_tasks if total_tasks > 0 else 0.0
        ),
        "avg_task_completion_rate": overall_metrics["avg_task_completion_rate"],
        "avg_precision": overall_metrics["avg_precision"],
        "avg_recall": overall_metrics["avg_recall"],
        "avg_f1_score": overall_metrics["avg_f1_score"],
        "terminated_rate": total_terminated / total_tasks if total_tasks > 0 else 0.0,
        "truncated_rate": total_truncated / total_tasks if total_tasks > 0 else 0.0,
        "avg_steps": total_steps / total_tasks if total_tasks > 0 else 0.0,
        "avg_step_elapsed": (
            total_step_elapsed / total_tasks if total_tasks > 0 else 0.0
        ),
        "avg_agent_elapsed": (
            total_agent_elapsed / total_tasks if total_tasks > 0 else 0.0
        ),
        "avg_time_elapsed": (
            total_time_elapsed / total_tasks if total_tasks > 0 else 0.0
        ),
        "avg_input_tokens": (
            total_input_tokens / total_tasks if total_tasks > 0 else 0.0
        ),
        "avg_output_tokens": (
            total_output_tokens / total_tasks if total_tasks > 0 else 0.0
        ),
        "avg_cost": total_cost / total_tasks if total_tasks > 0 else 0.0,
    }

    # Print overall summary
    print("📊 Overall Summary (All Task Types Combined):\n")
    print(f"🔧 Total Task Types: {overall_summary['num_task_types']}")
    print(f"🔢 Total Runs: {overall_summary['num_total_runs']}")
    print(f"❗ Avg Critical Errors: {overall_summary['avg_critical_errors']:.2f}")
    print(f"⚠️  Avg Action Errors: {overall_summary['avg_action_errors']:.2f}")
    print(
        f"✅ Avg Task Completion Rate: {overall_summary['avg_task_completion_rate']:.2f}"
    )
    print(f"🎯 Avg Precision: {overall_summary['avg_precision']:.2f}")
    print(f"🔄 Avg Recall: {overall_summary['avg_recall']:.2f}")
    print(f"📊 Avg F1 Score: {overall_summary['avg_f1_score']:.2f}")
    print(f"🏁 Terminated Rate: {overall_summary['terminated_rate']:.2f}")
    print(f"⏱️ Truncated Rate: {overall_summary['truncated_rate']:.2f}")
    print(f"🔢 Avg Steps: {overall_summary['avg_steps']:.2f}")
    print(f"⏰ Avg Step Runtime: {overall_summary['avg_step_elapsed']:.2f}s")
    print(f"🤖 Avg Agent Runtime: {overall_summary['avg_agent_elapsed']:.2f}s")
    print(f"⏱️ Avg Total Runtime: {overall_summary['avg_time_elapsed']:.2f}s")
    print(f"📥 Avg Input Tokens: {overall_summary['avg_input_tokens']:.0f}")
    print(f"📤 Avg Output Tokens: {overall_summary['avg_output_tokens']:.0f}")
    print(f"💰 Avg Cost: ${overall_summary['avg_cost']:.4f}\n")

    # ------------------- PRINT INDIVIDUAL TASK DETAILS -------------------
    critical_tasks = sorted(
        [t for t in task_results if t["critical_error"]], key=lambda x: x["task"]
    )
    non_critical_tasks = sorted(
        [t for t in task_results if not t["critical_error"]], key=lambda x: x["task"]
    )

    def print_task_summary(tasks, header=None):
        if tasks and header:
            print(header)
        for result in tasks:
            print(f"🧾 Task: {result['task']}")
            if result["num_action_errors"] > 0:
                print(f"   ⚠️  Action Errors: {result['num_action_errors']}")
            print(f"   💲 Penalty: {result['penalty']}")
            print(f"   ✅ Task Completion: {result['task_completion']:.2f}")
            print(f"   🎯 Precision: {result['precision']:.2f}")
            print(f"   🔄 Recall: {result['recall']:.2f}")
            print(f"   📊 F1 Score: {result['f1_score']:.2f}")
            print(f"   🔢 Steps: {result['num_steps']}")
            print(f"   ⏰ Step Runtime: {result['step_elapsed']:.2f}s")
            print(f"   🤖 Agent Runtime: {result['agent_elapsed']:.2f}s")
            print(
                f"   ⏱️ Total Runtime: {result['step_elapsed'] + result['agent_elapsed']:.2f}s"
            )
            print(f"   📥 Input Tokens: {result['input_tokens']}")
            print(f"   📤 Output Tokens: {result['output_tokens']}")
            print(f"   💰 Cost: ${result['cost']:.4f}")
            if result["terminated"]:
                print(f"   🏁 Terminated: Yes")
            if result["truncated"]:
                print(f"   ⏱️ Truncated: Yes")
            print()

    print("📄 Individual Task Results:\n")

    if critical_tasks:
        print_task_summary(critical_tasks, header="❗ Tasks with Critical Errors:\n")

    print_task_summary(
        non_critical_tasks,
        header="✅ Tasks without Critical Errors:\n" if critical_tasks else None,
    )

    # ------------------- EXPORT TO JSON FILES -------------------
    json_path_summary = os.path.join(root_directory, "study_summary_short.json")
    json_path_full = os.path.join(root_directory, "study_summary.json")

    # Create the short summary with overall metrics
    short_summary = {"overall": overall_summary, "by_task_type": export_type_summary}

    with open(json_path_summary, "w") as f:
        json.dump(short_summary, f, indent=2)

    # Create the full summary with overall metrics
    full_summary_with_overall = {
        "overall": overall_summary,
        "by_task_type": full_summary,
    }

    with open(json_path_full, "w") as f:
        json.dump(full_summary_with_overall, f, indent=2)

    print(f"📦 JSON output saved to:\n  - {json_path_summary}\n  - {json_path_full}")


if __name__ == "__main__":
    # Get all study directories in the results folder
    if not os.path.exists(STUDY_RESULTS_DIR):
        print(f"❌ Study results directory not found: {STUDY_RESULTS_DIR}")
        exit(1)

    study_dirs = [
        d
        for d in os.listdir(STUDY_RESULTS_DIR)
        if os.path.isdir(os.path.join(STUDY_RESULTS_DIR, d))
    ]

    if not study_dirs:
        print(f"❌ No study directories found in: {STUDY_RESULTS_DIR}")
        exit(1)

    print(f"🔍 Found {len(study_dirs)} study directories:")
    for study_dir in sorted(study_dirs):
        print(f"  - {study_dir}")
    print()

    # Process each study directory
    for study_dir in sorted(study_dirs):
        study_path = os.path.join(STUDY_RESULTS_DIR, study_dir)
        print(f"🚀 Processing study: {study_dir}")
        print(f"📁 Path: {study_path}")
        print("-" * 80)

        try:
            summarize_all_tasks_in_subdirs(study_path)
            print(f"✅ Completed processing: {study_dir}\n")
        except Exception as e:
            print(f"❌ Error processing {study_dir}: {e}\n")

        print("=" * 80)
        print()
