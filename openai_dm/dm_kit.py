from attr import field, Factory, define
import json
import requests
from typing import Callable, List

from griptape.artifacts import TextArtifact
from griptape.drivers import OpenAiChatPromptDriver, BasePromptDriver
from griptape.structures import Agent
from griptape.tasks import ToolkitTask, ActionSubtask, PromptTask
from griptape.utils import minify_json, PromptStack
from griptape.tools import BaseTool
import openai

from openai_dm.character_sheet import Character
from openai_dm.tools import CharacterSheetInspector, CharacterSheetUpdater
from openai_dm.utils import J2, abs_path


@define
class DMAgent(Agent):
    character_sheet: Character = field(default=Factory(lambda: Character()))
    tools: List[BaseTool] = field(default=Factory(list))
    token_counts: List[int] = field(default=Factory(list))
    prompt_history: List[PromptStack] = field(default=Factory(list))
    prompt_driver: BasePromptDriver = field(
        default=Factory(lambda: OpenAiChatPromptDriver()), kw_only=True
    )

    def __attrs_post_init__(self) -> None:
        self.prompt_driver = OpenAiDMPromptDriver(structure=self)

        if not self.tools:
            self.tools = [
                CharacterSheetInspector(self.character_sheet),
                CharacterSheetUpdater(self.character_sheet),
            ]
        self.add_task(DMToolkitTask(self.input_template, tools=self.tools))


@define
class DMToolkitTask(ToolkitTask):
    generate_assistant_subtask_template: Callable[[ActionSubtask], str] = field(
        default=Factory(
            lambda self: self.default_assistant_subtask_template_generator,
            takes_self=True,
        ),
        kw_only=True,
    )

    generate_user_subtask_template: Callable[[ActionSubtask], str] = field(
        default=Factory(
            lambda self: self.user_subtask_template_generator, takes_self=True
        ),
        kw_only=True,
    )

    def assistant_subtask_template_generator(self, subtask: ActionSubtask) -> str:
        return J2("assistant_subtask.j2").render(subtask=subtask)

    def user_subtask_template_generator(self, subtask: ActionSubtask) -> str:
        return J2("user_subtask.j2").render(subtask=subtask)

    def default_system_template_generator(self, _: PromptTask) -> str:
        memories = [r for r in self.memory if len(r.activities()) > 0]

        action_schema = minify_json(
            json.dumps(
                ActionSubtask.action_schema(self.action_types).json_schema(
                    "ActionSchema"
                )
            )
        )

        return J2("react.j2").render(
            rulesets=self.all_rulesets,
            action_schema=action_schema,
            tool_names=str.join(", ", [tool.name for tool in self.tools]),
            tools=[J2("partials/_tool.j2").render(tool=tool) for tool in self.tools],
            memory_names=str.join(", ", [memory.name for memory in memories]),
            memories=[
                J2("partials/_tool_memory.j2").render(memory=memory)
                for memory in memories
            ],
        )


@define
class OpenAiDMPromptDriver(OpenAiChatPromptDriver):
    def try_run(self, prompt_stack: PromptStack) -> TextArtifact:
        self.structure.prompt_history.append(
            {
                "prompt_stack": prompt_stack,
                "token_count": self.token_count(prompt_stack),
            }
        )
        return super().try_run(prompt_stack)
