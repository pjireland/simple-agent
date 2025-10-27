"""Simple AI agent."""

import json
from copy import deepcopy

import click
import docker
import litellm
from faker import Faker

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "make_random_name",
            "description": "Generate a random name",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]


def make_random_name() -> str:
    """Generate a random name."""
    return Faker().name()


@click.command()
@click.option("--prompt", prompt="Enter your prompt")
@click.option(
    "--model", default="gemini/gemini-2.5-flash-lite", help="LLM model to use"
)
@click.option(
    "--max-callbacks", default=5, help="Maximum number of callbacks with tool use"
)
@click.option(
    "--reflect",
    default=False,
    help="Whether to reflect on the output to try to improve it",
)
@click.option(
    "--execute-code",
    default=True,
    help=(
        "Whether to execute code returned by the model. Requires Docker Desktop to be "
        "running"
    ),
)
def run_agent(
    prompt: str,
    model: str = "gemini/gemini-2.5-flash-lite",
    max_callbacks: int = 5,
    reflect: bool = False,
    execute_code: bool = True,
) -> None:
    """Print the response for the given prompt to the terminal.

    Also executes any code return by the LLM when ``execute_code`` is ``True``.

    Parameters
    ----------
    message : str
        The prompt to pass as the user.
    model : str
        The model to use. The corresponding API key must be defined in the environment
        for the provider as '<PROVIDER>_API_KEY' (e.g., 'GEMINI_API_KEY').
    max_callbacks : int
        The maximum number of callbacks allowed.
    reflect : bool
        Whether to reflect on the response and try to improve it.
    execute_code : bool
        Whether to execute code returned by the model. Code will be executed in a
        ``python:3.10-slim`` Docker container.

    """
    messages = [
        {
            "role": "user",
            "content": (
                "Please include your name if asked. "
                "You can get your name using the ``make_random_name`` tool."
            ),
        },
        {
            "role": "user",
            "content": (
                """
                If I request code, please return it as python delimited with "
                "<execute_python> and </execute_python> tags."
                """
            ),
        },
        {"role": "user", "content": prompt},
    ]
    if not litellm.supports_function_calling(model=model):
        msg = "You must choose a model that supports function calling"
        raise ValueError(msg)
    # LightLLM annoyingly mutates tools in place
    response = litellm.completion(
        model=model,
        messages=messages,
        tools=deepcopy(TOOLS),
        tool_choice="auto",
    )
    callbacks = 0
    while (
        message := response.choices[0].message
    ).tool_calls and callbacks <= max_callbacks:
        messages.append(message)
        possible_functions = [
            tool["function"]["name"] for tool in TOOLS if tool["type"] == "function"
        ]
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            if function_name not in possible_functions:
                msg = f"Requested to call unrecognized function {function_name}"
                raise ValueError(msg)
            function_to_call = globals()[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(**function_args)
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )
        response = litellm.completion(
            model=model,
            messages=messages,
            tools=deepcopy(TOOLS),
            tool_choice="auto",
        )
        callbacks += 1
    if reflect:
        reflect_prompt = (
            "Please reflect on your last output, which was "
            f"'{response.choices[0].message.content}'. "
            "If you can improve it, please do so and provide a new response."
        )
        messages.append({"role": "user", "content": reflect_prompt})
        response = litellm.completion(
            model=model,
            messages=messages,
            tools=deepcopy(TOOLS),
            tool_choice="auto",
        )
    message_content: str = response.choices[0].message.content
    print(">>> LLM Response:")  # noqa: T201
    print(message_content)  # noqa: T201
    if (
        execute_code
        and message_content is not None
        and ("<execute_python>" in message_content)
        and ("</execute_python>" in message_content)
    ):
        code = message_content.split("<execute_python>", maxsplit=1)[1].split(
            "</execute_python>", maxsplit=1
        )[0]
        client = docker.from_env()
        output = client.containers.run(
            image="python:3.10-slim",
            command=["python", "-c", code],
            stdout=True,
            stderr=True,
            remove=True,
            network_disabled=True,
            mem_limit="128m",
            cpu_quota=50000,  # Half of one CPU core
        ).decode()
        print(">>> Code execution output:")  # noqa: T201
        print(output)  # noqa: T201
