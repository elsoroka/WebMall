from dataclasses import dataclass
from browsergym.experiments.loop import ExpArgs
from .env_args import EnvArgsWebMall

@dataclass
class ExpArgsWebMall(ExpArgs):
    env_args: EnvArgsWebMall

    def run(self):
        # Monkey-patch make_agent to inject task_name into agents that support it.
        original_make_agent = self.agent_args.make_agent
        task_name = self.env_args.task_name

        def make_agent_with_task_name():
            agent = original_make_agent()
            if hasattr(agent, 'task_name'):
                agent.task_name = task_name
            return agent

        self.agent_args.make_agent = make_agent_with_task_name
        try:
            super().run()
        finally:
            self.agent_args.make_agent = original_make_agent
