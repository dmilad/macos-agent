# macOS Agent - Claude AI with Native Desktop Control

A macOS-native implementation of Anthropic's computer use demo, enabling Claude AI to control your macOS desktop using PyAutoGUI instead of Docker/Linux virtualization.

> **⚠️ IMPORTANT SECURITY NOTICE**
>
> This agent has **full control** of your macOS desktop including:
> - Mouse and keyboard control
> - Screenshot access
> - File system access
> - Ability to run any command
>
> **Use with caution and never on a machine with sensitive data without proper isolation.**

## What This Is

This project adapts Anthropic's [computer-use-demo](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo) to run natively on macOS without Docker. It allows Claude AI to:

- **Control your mouse and keyboard** - Click, type, drag, scroll
- **See your screen** - Take and analyze screenshots
- **Run bash commands** - Execute terminal commands
- **Edit files** - Create, modify, and manage files
- **Perform complex tasks** - Chain multiple actions together

## Changes from Original

| Original (Docker/Linux) | This Version (macOS Native) |
|------------------------|----------------------------|
| `xdotool` for control | `PyAutoGUI` for control |
| `scrot` for screenshots | `pyautogui.screenshot()` |
| X11 virtual display | Real macOS desktop |
| Docker container | Native Python application |
| Ubuntu environment | macOS environment |
| VNC viewer for display | Direct desktop control |

## Prerequisites

- **macOS** (tested on macOS 14+, should work on 12+)
- **Python 3.11+**
- **uv** package manager ([install here](https://docs.astral.sh/uv/getting-started/installation/))
- **Anthropic API key** ([get one here](https://console.anthropic.com/))

## Quick Start

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and setup

```bash
cd macos-agent
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Set up configuration directories

### 3. Set your API key

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

Or enter it in the Streamlit UI when prompted.

### 4. Run the agent

```bash
./run.sh
```

This will start the Streamlit UI at `http://localhost:8501`

### 5. Grant Accessibility permissions

On first run, macOS will prompt you to grant Accessibility permissions:

1. Go to **System Settings** > **Privacy & Security** > **Accessibility**
2. Click the lock icon to make changes
3. Enable access for **Terminal** (or **Python** if prompted)
4. Restart the agent

## Usage

### Basic Tasks

Try these example prompts to test the agent:

**Simple tasks:**
- "Open Calculator and compute 15 * 234"
- "Open Safari and search for 'macOS Sequoia features'"
- "Create a text file at ~/Desktop/test.txt with 'Hello from Claude'"

**Medium tasks:**
- "Open TextEdit, write a haiku about computers, and save it to Desktop"
- "Search Google for the weather in San Francisco and tell me what you find"
- "Take a screenshot and describe what you see on my screen"

**Complex tasks:**
- "Open Safari, navigate to GitHub, and create a new repository called 'my-project'"
- "Find all PDF files in my Downloads folder and list their names"
- "Open Notes, create a new note with today's date, and write a to-do list"

### Understanding Tool Versions

The agent supports multiple tool versions:

- **computer_use_20241022** - Original October 2024 version (basic actions)
- **computer_use_20250124** - January 2025 version (adds scroll, hold_key, wait, triple_click)

Default: **computer_use_20250124** (recommended for full functionality)

### Keyboard Shortcuts

The agent automatically translates Linux/X11 keyboard shortcuts to macOS:

| Linux | macOS |
|-------|-------|
| `Ctrl+C` | `Cmd+C` |
| `Ctrl+V` | `Cmd+V` |
| `Ctrl+Q` | `Cmd+Q` |
| `Alt` | `Option` |

You can use either notation in your prompts - the agent will handle it.

## Project Structure

```
macos-agent/
├── computer_use_demo/
│   ├── __init__.py
│   ├── loop.py                    # Core agent loop (modified system prompt)
│   ├── streamlit.py               # Streamlit UI (Docker code removed)
│   └── tools/
│       ├── __init__.py
│       ├── base.py                # Tool base classes (unchanged)
│       ├── bash.py                # Bash execution (unchanged)
│       ├── edit.py                # File editing (unchanged)
│       ├── collection.py          # Tool management (unchanged)
│       ├── groups.py              # Tool versions (updated imports)
│       ├── run.py                 # Command runner (unchanged)
│       └── computer_macos.py      # ⭐ NEW: macOS computer control
├── pyproject.toml                 # Dependencies (uv compatible)
├── setup.sh                       # Setup script
├── run.sh                         # Run script
└── README.md                      # This file
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY` - Your Anthropic API key (required)
- `WIDTH` - Screen width in pixels (default: 1440)
- `HEIGHT` - Screen height in pixels (default: 900)
- `API_PROVIDER` - API provider: `anthropic`, `bedrock`, or `vertex` (default: `anthropic`)

### Screen Resolution

The agent uses your actual macOS screen resolution. Set it explicitly if needed:

```bash
export WIDTH=1920
export HEIGHT=1080
./run.sh
```

**Recommended resolution:** The agent works best with XGA (1024x768) or WXGA (1280x800) for optimal API performance. Screenshots are automatically scaled down if needed.

### Custom System Prompt

Edit [computer_use_demo/loop.py](computer_use_demo/loop.py#L48-L70) to customize the system prompt:

```python
SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
* You are controlling a macOS machine...
* Add your custom instructions here
</SYSTEM_CAPABILITY>"""
```

## How It Works

### 1. Agent Loop (loop.py)

The core loop:
1. Takes user input
2. Sends to Claude API with tool definitions
3. Claude responds with text and/or tool calls
4. Executes tools (computer, bash, edit)
5. Returns tool results to Claude
6. Repeat until task complete

### 2. Computer Tool (computer_macos.py)

Replaces Linux `xdotool` with macOS `PyAutoGUI`:

| Action | Implementation |
|--------|---------------|
| `screenshot` | `pyautogui.screenshot()` |
| `mouse_move` | `pyautogui.moveTo(x, y)` |
| `left_click` | `pyautogui.click()` |
| `type` | `pyautogui.write(text)` |
| `key` | `pyautogui.hotkey(*keys)` |
| `scroll` | `pyautogui.scroll(amount)` |

### 3. Bash Tool (bash.py)

Executes shell commands in a persistent bash session. **Unchanged from original**.

### 4. Edit Tool (edit.py)

File operations: view, create, str_replace, insert. **Unchanged from original**.

## Safety & Security

### Isolation Recommendations

1. **Use a separate macOS user account** for running the agent
2. **Don't store sensitive data** on the same machine
3. **Monitor the first few runs** to see what the agent does
4. **Review bash commands** before the agent executes them (future feature)
5. **Use Screen Recording** to log all actions

### Permissions Required

- **Accessibility** - Required for keyboard/mouse control
- **Screen Recording** - Required for screenshots (may be auto-granted)

### What Can Go Wrong

- **Unintended clicks** - Agent might click wrong elements
- **File modifications** - Agent has full file system access
- **Command execution** - Agent can run any bash command
- **Cost** - API usage can add up with many screenshots

### Emergency Stop

- **Click the Streamlit "Stop" button** in the UI
- **Press Ctrl+C** in the terminal running the agent
- **Close the terminal window**
- **Move mouse to corner** - PyAutoGUI has a failsafe (disabled by default)

## Troubleshooting

### "Accessibility permissions denied"

Go to **System Settings** > **Privacy & Security** > **Accessibility** and enable Terminal/Python.

### "ModuleNotFoundError: No module named 'pyautogui'"

Run `./setup.sh` again or manually:
```bash
source .venv/bin/activate
uv pip install pyautogui pillow
```

### "Failed to take screenshot"

Check Screen Recording permissions in **System Settings** > **Privacy & Security** > **Screen Recording**.

### Agent clicks wrong elements

- Increase `_screenshot_delay` in [computer_macos.py](computer_use_demo/tools/computer_macos.py#L136)
- Use lower screen resolution
- Provide more explicit coordinates in prompts

### Agent is slow

- Screenshots are large - use lower resolution
- Reduce `max_tokens` in Streamlit sidebar
- Use `claude-haiku-4-5` for faster (but less capable) responses

### PyAutoGUI fails

Make sure you're running on the main thread. If errors persist:
```bash
# Reinstall PyAutoGUI
uv pip uninstall pyautogui
uv pip install pyautogui --no-cache-dir
```

## Development

### Running Tests

```bash
source .venv/bin/activate
pytest
```

### Linting

```bash
ruff check .
ruff format .
```

### Adding Custom Tools

Create a new tool in `computer_use_demo/tools/`:

```python
from .base import BaseAnthropicTool, ToolResult

class MyCustomTool(BaseAnthropicTool):
    name = "my_tool"
    api_type = "custom_tool"

    async def __call__(self, **kwargs):
        # Your tool logic here
        return ToolResult(output="Success!")
```

Then add it to [tools/groups.py](computer_use_demo/tools/groups.py):

```python
from .my_custom_tool import MyCustomTool

TOOL_GROUPS = [
    ToolGroup(
        version="computer_use_20250124",
        tools=[ComputerToolMacOS20250124, MyCustomTool, BashTool20250124],
    ),
]
```

## API Providers

### Anthropic (Default)

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
./run.sh
```

### AWS Bedrock

```bash
export API_PROVIDER=bedrock
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2
./run.sh
```

### Google Vertex AI

```bash
export API_PROVIDER=vertex
export VERTEX_REGION=us-central1
export VERTEX_PROJECT_ID=your-project-id
gcloud auth application-default login
./run.sh
```

## Limitations

1. **Single screen only** - Doesn't support multi-monitor setups well
2. **No window management** - Can't reliably detect/switch windows
3. **macOS-specific** - Won't work on Linux/Windows without modifications
4. **No sandboxing** - Runs with your user permissions
5. **Screenshot latency** - 2-second delay after each action
6. **Text recognition** - Claude analyzes pixels, not actual text

## Performance Tips

1. **Use lower resolution** - Faster screenshots, cheaper API calls
2. **Limit screenshot frequency** - Modify `_screenshot_delay`
3. **Use prompt caching** - Enabled by default for Anthropic API
4. **Batch actions** - Ask agent to plan multiple steps
5. **Use Haiku for simple tasks** - Much faster and cheaper

## Comparison to Docker Version

| Feature | Docker (Original) | macOS Native (This) |
|---------|------------------|---------------------|
| Setup complexity | High (Docker + build) | Low (just uv) |
| Performance | Good (isolated) | Excellent (native) |
| Security | High (sandboxed) | Low (full access) |
| Screen control | Virtual display | Real desktop |
| Multi-platform | Linux only | macOS only |
| Development | Slow (rebuild) | Fast (hot reload) |

## Contributing

This is a personal adaptation of Anthropic's demo. For issues/improvements:

1. **For original demo issues** - Report to [anthropics/anthropic-quickstarts](https://github.com/anthropics/anthropic-quickstarts)
2. **For macOS-specific issues** - Modify the code yourself or ask Claude to help!

## License

MIT License - Same as original Anthropic quickstarts

## Acknowledgments

- **Anthropic** for the original computer-use-demo
- **PyAutoGUI** team for the excellent automation library
- **Astral** for the uv package manager

## Resources

- [Anthropic Computer Use Documentation](https://docs.anthropic.com/en/docs/agents/computer-use)
- [PyAutoGUI Documentation](https://pyautogui.readthedocs.io/)
- [Original Computer Use Demo](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)
- [Claude API Docs](https://docs.anthropic.com/)

---

**⚠️ Remember: This agent has full control of your desktop. Use responsibly!**
