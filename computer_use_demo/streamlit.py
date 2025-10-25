"""
Entrypoint for streamlit, see https://docs.streamlit.io/
"""

import asyncio
import base64
import os
import subprocess
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from functools import partial
from pathlib import PosixPath
from typing import cast, get_args

import httpx
import streamlit as st
from anthropic import RateLimitError
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
)
from streamlit.delta_generator import DeltaGenerator

from computer_use_demo.loop import (
    APIProvider,
    sampling_loop,
)
from computer_use_demo.tools import ToolResult, ToolVersion
from computer_use_demo.action_recorder import ActionRecorder
from computer_use_demo.vector_db import ActionVectorDB

PROVIDER_TO_DEFAULT_MODEL_NAME: dict[APIProvider, str] = {
    APIProvider.ANTHROPIC: "claude-sonnet-4-5-20250929",
    APIProvider.BEDROCK: "anthropic.claude-3-5-sonnet-20241022-v2:0",
    APIProvider.VERTEX: "claude-3-5-sonnet-v2@20241022",
}


@dataclass(kw_only=True, frozen=True)
class ModelConfig:
    tool_version: ToolVersion
    max_output_tokens: int
    default_output_tokens: int
    has_thinking: bool = False


SONNET_3_5_NEW = ModelConfig(
    tool_version="computer_use_20241022",
    max_output_tokens=1024 * 8,
    default_output_tokens=1024 * 4,
)

SONNET_3_7 = ModelConfig(
    tool_version="computer_use_20250124",
    max_output_tokens=128_000,
    default_output_tokens=1024 * 16,
    has_thinking=True,
)

CLAUDE_4 = ModelConfig(
    tool_version="computer_use_20250124",
    max_output_tokens=128_000,
    default_output_tokens=1024 * 16,
    has_thinking=True,
)

CLAUDE_4_5 = ModelConfig(
    tool_version="computer_use_20250124",
    max_output_tokens=128_000,
    default_output_tokens=1024 * 16,
    has_thinking=True,
)

HAIKU_4_5 = ModelConfig(
    tool_version="computer_use_20250124",
    max_output_tokens=1024 * 8,
    default_output_tokens=1024 * 4,
    has_thinking=False,
)

MODEL_TO_MODEL_CONF: dict[str, ModelConfig] = {
    "claude-3-7-sonnet-20250219": SONNET_3_7,
    "claude-opus-4@20250508": CLAUDE_4,
    "claude-sonnet-4-20250514": CLAUDE_4,
    "claude-sonnet-4-5-20250929": CLAUDE_4_5,
    "claude-opus-4-20250514": CLAUDE_4,
    "claude-haiku-4-5-20251001": HAIKU_4_5,
    "anthropic.claude-haiku-4-5-20251001-v1:0": HAIKU_4_5,  # Bedrock
    "claude-haiku-4-5@20251001": HAIKU_4_5,  # Vertex
}

CONFIG_DIR = PosixPath("~/.anthropic").expanduser()
API_KEY_FILE = CONFIG_DIR / "api_key"
STREAMLIT_STYLE = """
<style>
    /* Highlight the stop button in red */
    button[kind=header] {
        background-color: rgb(255, 75, 75);
        border: 1px solid rgb(255, 75, 75);
        color: rgb(255, 255, 255);
    }
    button[kind=header]:hover {
        background-color: rgb(255, 51, 51);
    }
     /* Hide the streamlit deploy button */
    .stAppDeployButton {
        visibility: hidden;
    }
</style>
"""

WARNING_TEXT = "⚠️ Security Alert: Never provide access to sensitive accounts or data, as malicious web content can hijack Claude's behavior"
INTERRUPT_TEXT = "(user stopped or interrupted and wrote the following)"
INTERRUPT_TOOL_ERROR = "human stopped or interrupted tool execution"


class Sender(StrEnum):
    USER = "user"
    BOT = "assistant"
    TOOL = "tool"


def setup_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_key" not in st.session_state:
        # Try to load API key from file first, then environment
        st.session_state.api_key = load_from_storage("api_key") or os.getenv(
            "ANTHROPIC_API_KEY", ""
        )
    if "provider" not in st.session_state:
        st.session_state.provider = (
            os.getenv("API_PROVIDER", "anthropic") or APIProvider.ANTHROPIC
        )
    if "provider_radio" not in st.session_state:
        st.session_state.provider_radio = st.session_state.provider
    if "model" not in st.session_state:
        _reset_model()
    if "auth_validated" not in st.session_state:
        st.session_state.auth_validated = False
    if "responses" not in st.session_state:
        st.session_state.responses = {}
    if "tools" not in st.session_state:
        st.session_state.tools = {}
    if "only_n_most_recent_images" not in st.session_state:
        st.session_state.only_n_most_recent_images = 3
    if "custom_system_prompt" not in st.session_state:
        st.session_state.custom_system_prompt = load_from_storage("system_prompt") or ""
    if "hide_images" not in st.session_state:
        st.session_state.hide_images = False
    if "token_efficient_tools_beta" not in st.session_state:
        st.session_state.token_efficient_tools_beta = False
    if "in_sampling_loop" not in st.session_state:
        st.session_state.in_sampling_loop = False
    if "action_recorder" not in st.session_state:
        st.session_state.action_recorder = ActionRecorder()
    if "record_actions_pending" not in st.session_state:
        st.session_state.record_actions_pending = False
    if "vector_db_status" not in st.session_state:
        st.session_state.vector_db_status = None
    if "vector_db" not in st.session_state:
        # Initialize VectorDB and try to load existing index
        st.session_state.vector_db = ActionVectorDB()
        if st.session_state.vector_db.load_index():
            # Successfully loaded existing index
            count = st.session_state.vector_db.next_id
            st.session_state.vector_db_status = {
                "type": "loaded",
                "count": count,
            }
        else:
            # If no index exists, build one from existing logs
            try:
                count = st.session_state.vector_db.build_index_from_logs(verbose=False)
                if count > 0:
                    st.session_state.vector_db.save_index()
                    st.session_state.vector_db_status = {
                        "type": "built",
                        "count": count,
                    }
                else:
                    st.session_state.vector_db_status = {
                        "type": "empty",
                        "count": 0,
                    }
            except Exception as e:
                st.session_state.vector_db_status = {
                    "type": "error",
                    "message": str(e),
                }
                print(f"Failed to build vector index: {e}")


def _reset_model():
    st.session_state.model = PROVIDER_TO_DEFAULT_MODEL_NAME[
        cast(APIProvider, st.session_state.provider)
    ]
    _reset_model_conf()


def _reset_model_conf():
    model_conf = (
        MODEL_TO_MODEL_CONF.get(
            st.session_state.model, SONNET_3_5_NEW
        )  # Default fallback
    )

    # If we're in radio selection mode, use the selected tool version
    if hasattr(st.session_state, "tool_versions"):
        st.session_state.tool_version = st.session_state.tool_versions
    else:
        st.session_state.tool_version = model_conf.tool_version

    st.session_state.has_thinking = model_conf.has_thinking
    st.session_state.output_tokens = model_conf.default_output_tokens
    st.session_state.max_output_tokens = model_conf.max_output_tokens
    st.session_state.thinking_budget = int(model_conf.default_output_tokens / 2)


async def main():
    """Render loop for streamlit"""
    setup_state()

    st.markdown(STREAMLIT_STYLE, unsafe_allow_html=True)

    st.title("Claude Computer Use Demo")

    if not os.getenv("HIDE_WARNING", False):
        st.warning(WARNING_TEXT)

    # Display VectorDB loading status
    if st.session_state.vector_db_status:
        status = st.session_state.vector_db_status
        if status["type"] == "loaded":
            st.success(f"✓ Vector database loaded: {status['count']} action{'s' if status['count'] != 1 else ''} indexed")
        elif status["type"] == "built":
            st.success(f"✓ Vector database built: {status['count']} action{'s' if status['count'] != 1 else ''} indexed from logs")
        elif status["type"] == "empty":
            st.info("ℹ Vector database initialized: No action logs found yet")
        elif status["type"] == "error":
            st.warning(f"⚠ Vector database error: {status['message']}")

    with st.sidebar:

        def _reset_api_provider():
            if st.session_state.provider_radio != st.session_state.provider:
                _reset_model()
                st.session_state.provider = st.session_state.provider_radio
                st.session_state.auth_validated = False

        provider_options = [option.value for option in APIProvider]
        st.radio(
            "API Provider",
            options=provider_options,
            key="provider_radio",
            format_func=lambda x: x.title(),
            on_change=_reset_api_provider,
        )

        st.text_input("Model", key="model", on_change=_reset_model_conf)

        if st.session_state.provider == APIProvider.ANTHROPIC:
            st.text_input(
                "Claude API Key",
                type="password",
                key="api_key",
                on_change=lambda: save_to_storage("api_key", st.session_state.api_key),
            )

        st.number_input(
            "Only send N most recent images",
            min_value=0,
            key="only_n_most_recent_images",
            help="To decrease the total tokens sent, remove older screenshots from the conversation",
        )
        st.text_area(
            "Custom System Prompt Suffix",
            key="custom_system_prompt",
            help="Additional instructions to append to the system prompt. see computer_use_demo/loop.py for the base system prompt.",
            on_change=lambda: save_to_storage(
                "system_prompt", st.session_state.custom_system_prompt
            ),
        )
        st.checkbox("Hide screenshots", key="hide_images")
        st.checkbox(
            "Enable token-efficient tools beta", key="token_efficient_tools_beta"
        )
        versions = get_args(ToolVersion)
        st.radio(
            "Tool Versions",
            key="tool_versions",
            options=versions,
            index=versions.index(st.session_state.tool_version),
            on_change=lambda: setattr(
                st.session_state, "tool_version", st.session_state.tool_versions
            ),
        )

        st.number_input("Max Output Tokens", key="output_tokens", step=1)

        st.checkbox("Thinking Enabled", key="thinking", value=False)
        st.number_input(
            "Thinking Budget",
            key="thinking_budget",
            max_value=st.session_state.max_output_tokens,
            step=1,
            disabled=not st.session_state.thinking,
        )

        if st.button("Reset", type="primary"):
            with st.spinner("Resetting..."):
                st.session_state.clear()
                st.rerun()

        if st.button("Record Actions"):
            st.session_state.record_actions_pending = True
            st.rerun()

    if not st.session_state.auth_validated:
        if auth_error := validate_auth(
            st.session_state.provider, st.session_state.api_key
        ):
            st.warning(f"Please resolve the following auth issue:\n\n{auth_error}")
            return
        else:
            st.session_state.auth_validated = True

    # Handle pending action recording
    if st.session_state.record_actions_pending:
        st.session_state.record_actions_pending = False
        await _handle_record_actions()

    chat, http_logs = st.tabs(["Chat", "HTTP Exchange Logs"])
    new_message = st.chat_input(
        "Type a message to send to Claude to control the computer..."
    )

    with chat:
        # render past chats
        for message in st.session_state.messages:
            if isinstance(message["content"], str):
                _render_message(message["role"], message["content"])
            elif isinstance(message["content"], list):
                for block in message["content"]:
                    # the tool result we send back to the Claude API isn't sufficient to render all details,
                    # so we store the tool use responses
                    if isinstance(block, dict) and block["type"] == "tool_result":
                        _render_message(
                            Sender.TOOL, st.session_state.tools[block["tool_use_id"]]
                        )
                    else:
                        _render_message(
                            message["role"],
                            cast(BetaContentBlockParam | ToolResult, block),
                        )

        # render past http exchanges
        for identity, (request, response) in st.session_state.responses.items():
            _render_api_response(request, response, identity, http_logs)

        # render past chats
        if new_message:
            st.session_state.messages.append(
                {
                    "role": Sender.USER,
                    "content": [
                        *maybe_add_interruption_blocks(),
                        BetaTextBlockParam(type="text", text=new_message),
                    ],
                }
            )
            _render_message(Sender.USER, new_message)
            # Record user message
            st.session_state.action_recorder.record_user_message(new_message)

        try:
            most_recent_message = st.session_state["messages"][-1]
        except IndexError:
            return

        if most_recent_message["role"] is not Sender.USER:
            # we don't have a user message to respond to, exit early
            return

        # Query VectorDB for similar past requests
        if new_message and hasattr(st.session_state, "vector_db"):
            try:
                similar_requests = st.session_state.vector_db.query_similar(
                    request_text=new_message,
                    k=1,
                    min_similarity=0.3,
                )

                if similar_requests:
                    best_match = similar_requests[0]
                    narrative = best_match["narrative"]

                    # Inject narrative as a text block
                    narrative_content = (
                        f"Reference: I found a similar past task.\n\n"
                        f"Previous request: \"{best_match['request_text']}\"\n\n"
                        f"Here's how it was successfully completed:\n\n{narrative}\n\n"
                        f"I should consider this approach as a reference while adapting it to the current task."
                    )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": [{
                            "type": "text",
                            "text": narrative_content,
                        }],
                    })
                    # Render the narrative message
                    _render_message(Sender.BOT, {"type": "text", "text": narrative_content})
            except Exception as e:
                # Silently fail if vector search has issues
                print(f"Vector search failed: {e}")

        with track_sampling_loop():
            # run the agent sampling loop with the newest message
            st.session_state.messages = await sampling_loop(
                system_prompt_suffix=st.session_state.custom_system_prompt,
                model=st.session_state.model,
                provider=st.session_state.provider,
                messages=st.session_state.messages,
                output_callback=partial(_render_message, Sender.BOT),
                tool_output_callback=partial(
                    _tool_output_callback, tool_state=st.session_state.tools
                ),
                api_response_callback=partial(
                    _api_response_callback,
                    tab=http_logs,
                    response_state=st.session_state.responses,
                ),
                api_key=st.session_state.api_key,
                only_n_most_recent_images=st.session_state.only_n_most_recent_images,
                tool_version=st.session_state.tool_versions,
                max_tokens=st.session_state.output_tokens,
                thinking_budget=st.session_state.thinking_budget
                if st.session_state.thinking
                else None,
                token_efficient_tools_beta=st.session_state.token_efficient_tools_beta,
            )


def maybe_add_interruption_blocks():
    if not st.session_state.in_sampling_loop:
        return []
    # If this function is called while we're in the sampling loop, we can assume that the previous sampling loop was interrupted
    # and we should annotate the conversation with additional context for the model and heal any incomplete tool use calls
    result = []
    last_message = st.session_state.messages[-1]
    previous_tool_use_ids = [
        block["id"] for block in last_message["content"] if block["type"] == "tool_use"
    ]
    for tool_use_id in previous_tool_use_ids:
        st.session_state.tools[tool_use_id] = ToolResult(error=INTERRUPT_TOOL_ERROR)
        result.append(
            BetaToolResultBlockParam(
                tool_use_id=tool_use_id,
                type="tool_result",
                content=INTERRUPT_TOOL_ERROR,
                is_error=True,
            )
        )
    result.append(BetaTextBlockParam(type="text", text=INTERRUPT_TEXT))
    return result


@contextmanager
def track_sampling_loop():
    st.session_state.in_sampling_loop = True
    yield
    st.session_state.in_sampling_loop = False


def validate_auth(provider: APIProvider, api_key: str | None):
    if provider == APIProvider.ANTHROPIC:
        if not api_key:
            return "Enter your Claude API key in the sidebar to continue."
    if provider == APIProvider.BEDROCK:
        import boto3

        if not boto3.Session().get_credentials():
            return "You must have AWS credentials set up to use the Bedrock API."
    if provider == APIProvider.VERTEX:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError

        if not os.environ.get("CLOUD_ML_REGION"):
            return "Set the CLOUD_ML_REGION environment variable to use the Vertex API."
        try:
            google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except DefaultCredentialsError:
            return "Your google cloud credentials are not set up correctly."


def load_from_storage(filename: str) -> str | None:
    """Load data from a file in the storage directory."""
    try:
        file_path = CONFIG_DIR / filename
        if file_path.exists():
            data = file_path.read_text().strip()
            if data:
                return data
    except Exception as e:
        st.write(f"Debug: Error loading {filename}: {e}")
    return None


def save_to_storage(filename: str, data: str) -> None:
    """Save data to a file in the storage directory."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        file_path = CONFIG_DIR / filename
        file_path.write_text(data)
        # Ensure only user can read/write the file
        file_path.chmod(0o600)
    except Exception as e:
        st.write(f"Debug: Error saving {filename}: {e}")


async def _handle_record_actions():
    """Handle the Record Actions button click."""
    try:
        if st.session_state.action_recorder.get_action_count() == 0:
            st.warning("No actions to record yet. Use the agent to perform some tasks first.")
            return

        with st.spinner("Processing and saving actions..."):
            filepath = await st.session_state.action_recorder.process_and_save(
                api_key=st.session_state.api_key,
            )
            st.success(f"Actions recorded successfully to: {filepath}")

            # Update VectorDB with the new recording
            if hasattr(st.session_state, "vector_db"):
                try:
                    import json
                    from pathlib import Path

                    # Load the saved recording to extract request and narrative
                    with open(filepath) as f:
                        recording = json.load(f)

                    request_text = recording.get("request", {}).get("content", {}).get("text")
                    narrative = recording.get("narrative")

                    if request_text and narrative:
                        # Add to vector index
                        st.session_state.vector_db.add_to_index(
                            request_text=request_text,
                            narrative=narrative,
                            log_file=Path(filepath).name,
                        )
                        # Save the updated index
                        st.session_state.vector_db.save_index()
                except Exception as e:
                    print(f"Failed to update vector index: {e}")

            # Clear the recorder for the next session
            st.session_state.action_recorder.clear()
    except Exception as e:
        st.error(f"Error recording actions: {str(e)}")


def _api_response_callback(
    request: httpx.Request,
    response: httpx.Response | object | None,
    error: Exception | None,
    tab: DeltaGenerator,
    response_state: dict[str, tuple[httpx.Request, httpx.Response | object | None]],
):
    """
    Handle an API response by storing it to state and rendering it.
    """
    response_id = datetime.now().isoformat()
    response_state[response_id] = (request, response)
    if error:
        _render_error(error)
    _render_api_response(request, response, response_id, tab)


def _tool_output_callback(
    tool_output: ToolResult,
    tool_id: str,
    tool_name: str,
    tool_input: dict,
    tool_state: dict[str, ToolResult]
):
    """Handle a tool output by storing it to state and rendering it."""
    tool_state[tool_id] = tool_output
    _render_message(Sender.TOOL, tool_output)

    # Record the tool execution
    st.session_state.action_recorder.record_tool_use(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_result=tool_output
    )


def _render_api_response(
    request: httpx.Request,
    response: httpx.Response | object | None,
    response_id: str,
    tab: DeltaGenerator,
):
    """Render an API response to a streamlit tab"""
    with tab:
        with st.expander(f"Request/Response ({response_id})"):
            newline = "\n\n"
            st.markdown(
                f"`{request.method} {request.url}`{newline}{newline.join(f'`{k}: {v}`' for k, v in request.headers.items())}"
            )
            st.json(request.read().decode())
            st.markdown("---")
            if isinstance(response, httpx.Response):
                st.markdown(
                    f"`{response.status_code}`{newline}{newline.join(f'`{k}: {v}`' for k, v in response.headers.items())}"
                )
                st.json(response.text)
            else:
                st.write(response)


def _render_error(error: Exception):
    if isinstance(error, RateLimitError):
        body = "You have been rate limited."
        if retry_after := error.response.headers.get("retry-after"):
            body += f" **Retry after {str(timedelta(seconds=int(retry_after)))} (HH:MM:SS).** See our API [documentation](https://docs.claude.com/en/api/rate-limits) for more details."
        body += f"\n\n{error.message}"
    else:
        body = str(error)
        body += "\n\n**Traceback:**"
        lines = "\n".join(traceback.format_exception(error))
        body += f"\n\n```{lines}```"
    save_to_storage(f"error_{datetime.now().timestamp()}.md", body)
    st.error(f"**{error.__class__.__name__}**\n\n{body}", icon=":material/error:")


def _render_message(
    sender: Sender,
    message: str | BetaContentBlockParam | ToolResult,
):
    """Convert input from the user or output from the agent to a streamlit message."""
    # streamlit's hotreloading breaks isinstance checks, so we need to check for class names
    is_tool_result = not isinstance(message, str | dict)
    if not message or (
        is_tool_result
        and st.session_state.hide_images
        and not hasattr(message, "error")
        and not hasattr(message, "output")
    ):
        return
    with st.chat_message(sender):
        if is_tool_result:
            message = cast(ToolResult, message)
            if message.output:
                if message.__class__.__name__ == "CLIResult":
                    st.code(message.output)
                else:
                    st.markdown(message.output)
            if message.error:
                st.error(message.error)
            if message.base64_image and not st.session_state.hide_images:
                st.image(base64.b64decode(message.base64_image))
        elif isinstance(message, dict):
            if message["type"] == "text":
                st.write(message["text"])
                st.session_state.action_recorder.record_thinking(message["text"])
            elif message["type"] == "thinking":
                thinking_content = message.get("thinking", "")
                st.markdown(f"[Thinking]\n\n{thinking_content}")
                st.session_state.action_recorder.record_thinking(thinking_content)
            elif message["type"] == "tool_use":
                st.code(f"Tool Use: {message['name']}\nInput: {message['input']}")
            else:
                # only expected return types are text and tool_use
                raise Exception(f"Unexpected response type {message['type']}")
        else:
            st.markdown(message)


if __name__ == "__main__":
    asyncio.run(main())
