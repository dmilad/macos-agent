# Architecture Overview - macOS Agent

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                     (Streamlit Web UI)                          │
│                   http://localhost:8501                         │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ User input / Display output
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                      Agent Loop (loop.py)                       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Receive user input                                   │  │
│  │  2. Query vector DB for similar past tasks (optional)    │  │
│  │  3. Build messages with system prompt + history          │  │
│  │  4. Call Claude API with tool definitions                │  │
│  │  5. Process Claude's response                            │  │
│  │  6. Execute tool calls (if any)                          │  │
│  │  7. Record actions (action_recorder.py)                  │  │
│  │  8. Return tool results to Claude                        │  │
│  │  9. Repeat until task complete                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Tool execution requests
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                  Tool Collection (collection.py)                │
│                                                                 │
│  Routes tool calls to appropriate tool implementation          │
└────────┬───────────────────────┬────────────────────┬──────────┘
         │                       │                    │
         │                       │                    │
┌────────▼──────────┐  ┌────────▼────────┐  ┌───────▼──────────┐
│  Computer Tool    │  │   Bash Tool     │  │   Edit Tool      │
│ (computer_macos)  │  │   (bash.py)     │  │   (edit.py)      │
└────────┬──────────┘  └────────┬────────┘  └───────┬──────────┘
         │                       │                    │
         │ PyAutoGUI            │ subprocess          │ File I/O
         │                       │                    │
┌────────▼──────────────────────▼────────────────────▼──────────┐
│                        macOS System                            │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Desktop     │  │  Terminal    │  │  File System       │  │
│  │  Control     │  │  (bash)      │  │  (read/write)      │  │
│  │              │  │              │  │                    │  │
│  │ • Mouse      │  │ • Commands   │  │ • Create files     │  │
│  │ • Keyboard   │  │ • Scripts    │  │ • Edit files       │  │
│  │ • Screenshots│  │ • Apps       │  │ • View files       │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
└────────────────────────────────────────────────────────────────┘

                              ▲
                              │
                              │ Records successful actions
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│               Action Recording & Learning System                │
│                                                                 │
│  ┌─────────────────────┐         ┌──────────────────────────┐  │
│  │  Action Recorder    │────────▶│   Vector Database        │  │
│  │ (action_recorder.py)│         │   (vector_db.py)         │  │
│  │                     │         │                          │  │
│  │ • Record actions    │         │ • Annoy index            │  │
│  │ • Filter successful │         │ • Sentence transformers  │  │
│  │ • Generate narrative│         │ • Semantic search        │  │
│  └─────────────────────┘         │ • Deduplication          │  │
│                                  └──────────────────────────┘  │
│           │                                   │                │
│           │                                   │                │
│           ▼                                   ▼                │
│  recordings/action_log_*.json        recordings/actions.ann   │
│                                      recordings/index_metadata │
└─────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Streamlit UI (`streamlit.py`)
**Responsibilities:**
- Display chat interface
- Manage session state (messages, API key, settings)
- Render Claude's responses and tool outputs
- Handle API response logging
- Provide configuration sidebar

**Key Functions:**
- `setup_state()` - Initialize session variables
- `main()` - Main async event loop
- `_render_message()` - Display chat messages
- `_tool_output_callback()` - Handle tool execution results
- `_api_response_callback()` - Log API requests/responses

### 2. Agent Loop (`loop.py`)
**Responsibilities:**
- Orchestrate interaction between Claude API and tools
- Manage message history and prompt caching
- Handle API provider selection (Anthropic/Bedrock/Vertex)
- Inject system prompt with macOS context
- Scale screenshots for optimal API performance

**Key Functions:**
- `sampling_loop()` - Main agent execution loop
- `_response_to_params()` - Convert API response to parameters
- `_inject_prompt_caching()` - Add cache breakpoints
- `_maybe_filter_to_n_most_recent_images()` - Optimize image count

**System Prompt:**
```python
SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
* You are controlling a macOS machine...
* macOS uses Command (Cmd) key instead of Ctrl...
* Screen resolution is 1440x900 pixels
</SYSTEM_CAPABILITY>"""
```

### 3. Tool Collection (`tools/collection.py`)
**Responsibilities:**
- Maintain registry of available tools
- Route tool calls by name
- Execute tools and return results
- Handle tool errors gracefully

**Tool Registry:**
```python
{
    "computer": ComputerToolMacOS20250124(),
    "bash": BashTool20250124(),
    "str_replace_based_edit_tool": EditTool20250728()
}
```

### 4. Computer Tool (`tools/computer_macos.py`)
**Responsibilities:**
- Control macOS desktop via PyAutoGUI
- Take screenshots and encode as base64
- Scale coordinates between API and actual screen
- Translate Linux/X11 keys to macOS keys
- Execute mouse and keyboard actions

**Actions Supported:**
| Action | Description | Implementation |
|--------|-------------|----------------|
| `screenshot` | Capture screen | `pyautogui.screenshot()` |
| `mouse_move` | Move cursor | `pyautogui.moveTo(x, y)` |
| `left_click` | Click mouse | `pyautogui.click()` |
| `right_click` | Right click | `pyautogui.rightClick()` |
| `double_click` | Double click | `pyautogui.doubleClick()` |
| `triple_click` | Triple click | `pyautogui.click(clicks=3)` |
| `middle_click` | Middle click | `pyautogui.middleClick()` |
| `left_click_drag` | Drag mouse | `pyautogui.drag(dx, dy)` |
| `left_mouse_down` | Press mouse | `pyautogui.mouseDown()` |
| `left_mouse_up` | Release mouse | `pyautogui.mouseUp()` |
| `type` | Type text | `pyautogui.write(text)` |
| `key` | Press key combo | `pyautogui.hotkey(*keys)` |
| `hold_key` | Hold key | `keyDown()` + sleep + `keyUp()` |
| `scroll` | Scroll wheel | `pyautogui.scroll(amount)` |
| `wait` | Wait duration | `asyncio.sleep(duration)` |
| `cursor_position` | Get cursor pos | `pyautogui.position()` |

**Key Translation Example:**
```python
translate_key("ctrl") → "command"
translate_key("alt") → "option"
translate_key("Return") → "enter"
```

### 5. Bash Tool (`tools/bash.py`)
**Responsibilities:**
- Maintain persistent bash session
- Execute shell commands
- Capture stdout/stderr
- Handle command timeouts
- Support session restart

**Session Management:**
```python
class _BashSession:
    async def run(self, command: str, timeout: int = 120):
        # Send command with sentinel
        self.stdin.write(f"{command}; echo '<<exit>>'\n")

        # Read output until sentinel
        output = await self._read_until_sentinel()

        return CLIResult(output=stdout, error=stderr)
```

### 6. Edit Tool (`tools/edit.py`)
**Responsibilities:**
- View files and directories
- Create new files
- Edit files with string replacement
- Insert lines at specific positions
- Undo edits (with history tracking)

**Commands:**
- `view` - Display file contents or directory listing
- `create` - Create new file with content
- `str_replace` - Replace single occurrence of string
- `insert` - Insert lines at line number
- `undo_edit` - Revert to previous version

### 7. Action Recorder (`action_recorder.py`)
**Responsibilities:**
- Record all actions during a task session
- Filter out failed attempts and screenshots
- Use Claude to analyze and create a narrative
- Save recordings to JSON files

**Key Functions:**
- `record_user_message()` - Record initial user request
- `record_thinking()` - Record Claude's thinking blocks
- `record_tool_use()` - Record tool executions and results
- `process_and_save()` - Analyze with Claude and save to file
- `_analyze_with_claude()` - Generate filtered actions and narrative

**Recording Structure:**
```json
{
  "session_id": "2025-10-23T17:05:56",
  "recorded_at": "2025-10-23T17:10:23",
  "request": {
    "type": "user_message",
    "content": {"text": "Check p44 messages in Notes"}
  },
  "all_actions": [...],
  "successful_actions": [...],
  "narrative": "The task was to determine how many p44-related messages..."
}
```

### 8. Vector Database (`vector_db.py`)
**Responsibilities:**
- Embed requests using sentence transformers
- Index embeddings with Annoy for fast similarity search
- Query for similar past tasks
- Deduplicate recordings by request text
- Save/load index from disk

**Key Functions:**
- `build_index_from_logs()` - Build index from all recordings
- `add_to_index()` - Add new recording to index
- `query_similar()` - Find similar past tasks
- `save_index()` / `load_index()` - Persist to disk

**Implementation Details:**
```python
# Uses sentence-transformers for embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")
embedding = model.encode(request_text)  # 384-dim vector

# Annoy for fast approximate nearest neighbor search
index = AnnoyIndex(384, "angular")
index.add_item(idx, embedding)
index.build(n_trees=10)

# Query returns similar requests with cosine similarity
results = index.get_nns_by_vector(query_embedding, k=1)
```

### 9. Build Index Utility (`build_index.py`)
**Responsibilities:**
- CLI utility to build or rebuild vector index
- Process all action logs in recordings directory
- Deduplicate by request text (keep latest)
- Save index and metadata to disk

**Usage:**
```bash
python -m computer_use_demo.build_index [--force] [--recordings-dir DIR]
```

## Data Flow

### Complete Task Execution Flow

```
1. User types prompt in UI
   │
   ├─→ Streamlit captures input
   │
2. Agent loop builds API request
   │
   ├─→ System prompt + message history + tool definitions
   │
3. Call Claude API
   │
   ├─→ Anthropic/Bedrock/Vertex endpoint
   │
4. Claude responds with:
   │
   ├─→ Text (thinking/explanation)
   └─→ Tool calls (actions to take)
   │
5. Execute tools
   │
   ├─→ computer: Take screenshot, click, type
   ├─→ bash: Run commands
   └─→ edit: Modify files
   │
6. Collect tool results
   │
   ├─→ Screenshots (base64)
   ├─→ Command output
   └─→ File changes
   │
7. Send results back to Claude
   │
   ├─→ Append to message history
   │
8. Claude processes results
   │
   ├─→ More tool calls OR final response
   │
9. Display to user
   │
   └─→ Render in Streamlit UI
```

### Screenshot Pipeline

```
1. Claude decides to take screenshot
   │
2. computer tool called with action="screenshot"
   │
3. PyAutoGUI captures screen
   │
   pyautogui.screenshot()
   │
4. Scale to optimal resolution
   │
   1440x900 → 800x450 (if scaling enabled)
   │
5. Convert to base64 PNG
   │
   base64.b64encode(img_bytes)
   │
6. Return in ToolResult
   │
   ToolResult(base64_image="iVBORw0KGgo...")
   │
7. Append to messages as image block
   │
   {type: "image", source: {type: "base64", data: "..."}}
   │
8. Claude sees the screenshot
   │
   Analyzes visual content
   │
9. Decides next action
   │
   Click button, type text, etc.
```

### Action Recording Pipeline

```
1. Task begins
   │
   ├─→ ActionRecorder initialized in session state
   │
2. User sends message
   │
   ├─→ record_user_message(message)
   │
3. Agent loop iteration
   │
   ├─→ Claude thinks → record_thinking(content)
   ├─→ Claude calls tool → record_tool_use(name, input, result)
   │
4. Task completes
   │
   ├─→ User clicks "Record this session" button
   │
5. Process recording
   │
   ├─→ ActionRecorder.process_and_save(api_key)
   │
6. Filter and analyze
   │
   ├─→ Send all actions to Claude
   ├─→ Claude removes failed attempts, screenshots, backtracking
   ├─→ Claude generates narrative with successful actions
   │
7. Save to file
   │
   ├─→ recordings/action_log_20251023_170556.json
   │   {
   │     "request": {...},
   │     "all_actions": [...],
   │     "successful_actions": [...],
   │     "narrative": "..."
   │   }
   │
8. Build index (manual step)
   │
   ├─→ python -m computer_use_demo.build_index
   ├─→ Read all action_log_*.json files
   ├─→ Deduplicate by request text (keep latest)
   ├─→ Embed requests with sentence-transformers
   ├─→ Build Annoy index
   ├─→ Save to recordings/actions.ann + index_metadata.json
   │
9. Future task with similar request
   │
   ├─→ User enables "Use vector DB" in sidebar
   ├─→ VectorDB.query_similar(new_request, k=1)
   ├─→ Find most similar past request (cosine similarity)
   ├─→ Inject narrative as reference context
   ├─→ Claude uses it to guide current task
   │
10. Result: Faster, more consistent execution
```

### Vector Search Flow

```
User request: "How many project-x messages in Notes?"
   │
   ├─→ Embed with sentence-transformers
   │   query_embedding = model.encode(request)  # 384-dim
   │
   ├─→ Search Annoy index
   │   indices, distances = index.get_nns_by_vector(query_embedding, k=1)
   │
   ├─→ Convert angular distance to cosine similarity
   │   similarity = 1.0 - (distance^2 / 2.0)
   │
   ├─→ Filter by threshold (default: 0.5)
   │   if similarity >= 0.5: return result
   │
   ├─→ Retrieved: "How many p44 messages in Notes?" (similarity: 0.87)
   │   narrative: "The task was to determine how many p44-related
   │              messages exist in Notes. The agent opened Notes
   │              using 'open -a Notes', clicked the #p44 tag..."
   │
   ├─→ Inject into system prompt
   │   "Reference: I found a similar past task. Here's how it was done:
   │    [narrative with successful actions]"
   │
   └─→ Claude follows similar approach for current task
```

## File Organization

```
macos-agent/
│
├── pyproject.toml          # Package configuration
├── setup.sh                # Environment setup script
├── run.sh                  # Launch script
├── .gitignore              # Git ignore patterns
│
├── README.md               # Main documentation
├── QUICKSTART.md           # Getting started guide
├── ARCHITECTURE.md         # This file
├── MIGRATION_NOTES.md      # Docker → macOS changes
│
├── computer_use_demo/
│   ├── __init__.py         # Package marker
│   │
│   ├── loop.py             # Core agent loop
│   │   ├── sampling_loop() - Main orchestration
│   │   ├── SYSTEM_PROMPT - macOS context
│   │   └── APIProvider - Anthropic/Bedrock/Vertex
│   │
│   ├── streamlit.py        # Web UI
│   │   ├── main() - Entry point
│   │   ├── setup_state() - Session management
│   │   └── _render_message() - Display logic
│   │
│   ├── action_recorder.py  # Action recording
│   │   ├── ActionRecorder - Record task actions
│   │   ├── record_user_message() - Record requests
│   │   ├── record_thinking() - Record thinking blocks
│   │   ├── record_tool_use() - Record tool executions
│   │   └── process_and_save() - Filter and save recording
│   │
│   ├── vector_db.py        # Vector database for learning
│   │   ├── ActionVectorDB - Semantic search over logs
│   │   ├── build_index_from_logs() - Build Annoy index
│   │   ├── query_similar() - Find similar past tasks
│   │   └── save_index() / load_index() - Persistence
│   │
│   ├── build_index.py      # CLI utility to build index
│   │   └── main() - Build vector index from recordings
│   │
│   ├── test_query.py       # Test vector DB queries
│   │
│   └── tools/
│       ├── __init__.py     # Tool exports
│       │
│       ├── base.py         # Base classes
│       │   ├── BaseAnthropicTool - Tool interface
│       │   ├── ToolResult - Execution result
│       │   └── ToolError - Error handling
│       │
│       ├── collection.py   # Tool registry
│       │   └── ToolCollection - Route and execute tools
│       │
│       ├── groups.py       # Version management
│       │   └── TOOL_GROUPS_BY_VERSION - Tool combinations
│       │
│       ├── computer_macos.py - macOS desktop control
│       │   ├── ComputerToolMacOS20241022 - Oct 2024 version
│       │   ├── ComputerToolMacOS20250124 - Jan 2025 version
│       │   ├── MACOS_KEY_MAPPING - Key translation
│       │   └── PyAutoGUI integration
│       │
│       ├── bash.py         # Shell execution
│       │   ├── _BashSession - Persistent session
│       │   ├── BashTool20241022 - Oct 2024 version
│       │   └── BashTool20250124 - Jan 2025 version
│       │
│       ├── edit.py         # File operations
│       │   ├── EditTool20241022 - Oct 2024 version
│       │   ├── EditTool20250124 - Jan 2025 version
│       │   ├── EditTool20250429 - Apr 2025 version
│       │   └── EditTool20250728 - Jul 2025 version
│       │
│       └── run.py          # Command execution helper
│           └── run() - Async subprocess wrapper
│
├── recordings/             # Action logs and vector index
│   ├── action_log_*.json  # Individual task recordings
│   ├── actions.ann        # Annoy vector index file
│   └── index_metadata.json # Index metadata and embeddings info
```

## Tool Versioning

Different Claude models support different tool versions:

```
┌─────────────────────────────────────────────────────────────┐
│                     Tool Version Timeline                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  computer_use_20241022 (Oct 2024)                          │
│  ├─ ComputerToolMacOS20241022                              │
│  ├─ EditTool20241022                                       │
│  └─ BashTool20241022                                       │
│                                                             │
│  computer_use_20250124 (Jan 2025) ← RECOMMENDED            │
│  ├─ ComputerToolMacOS20250124                              │
│  │   └─ Adds: scroll, hold_key, wait, triple_click         │
│  ├─ EditTool20250728                                       │
│  └─ BashTool20250124                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## API Integration

### Message Format

```json
{
  "role": "user" | "assistant",
  "content": [
    {
      "type": "text",
      "text": "User's prompt"
    },
    {
      "type": "image",
      "source": {
        "type": "base64",
        "media_type": "image/png",
        "data": "iVBORw0KG..."
      }
    },
    {
      "type": "tool_use",
      "id": "toolu_01...",
      "name": "computer",
      "input": {
        "action": "left_click",
        "coordinate": [640, 450]
      }
    },
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01...",
      "content": [
        {
          "type": "text",
          "text": "Clicked at (640, 450)"
        },
        {
          "type": "image",
          "source": {...}
        }
      ]
    }
  ]
}
```

### Prompt Caching

The agent uses prompt caching to reduce costs:

```python
# System prompt cached
system = {
    "type": "text",
    "text": SYSTEM_PROMPT,
    "cache_control": {"type": "ephemeral"}  # Cached
}

# Last 3 user messages cached
for message in recent_messages:
    message["content"][-1]["cache_control"] = {"type": "ephemeral"}
```

**Cache Hit Rates:**
- System prompt: ~99% hit rate (changes rarely)
- Recent messages: ~80% hit rate (repeated screenshots)
- Cost savings: ~90% on cached tokens

## Performance Characteristics

### Latency Breakdown

```
Total Task Time: 10-30 seconds
│
├─ Screenshot capture: 0.1-0.3s (PyAutoGUI)
├─ Image encoding: 0.1-0.2s (base64)
├─ API request: 2-5s (network + Claude processing)
├─ Tool execution: 0.2-1s (click/type/bash)
├─ Screenshot delay: 2s (wait for UI to settle)
└─ Multiple rounds: 3-5 iterations typical
```

### Token Usage

```
Simple task (1 round):
├─ System prompt: ~500 tokens (cached)
├─ User input: ~50 tokens
├─ Screenshot: ~1500 tokens (1440x900 scaled to 800x450)
├─ Claude response: ~200 tokens
└─ Total: ~2250 tokens (~$0.01)

Complex task (5 rounds):
├─ System prompt: ~500 tokens (cached, hits 90%)
├─ User input: ~100 tokens
├─ Screenshots: ~7500 tokens (5 screenshots)
├─ Claude responses: ~1000 tokens
├─ Tool results: ~500 tokens
└─ Total: ~10,000 tokens (~$0.03-$0.05)
```

### Memory Usage

```
Runtime Memory:
├─ Python process: ~200MB
├─ Streamlit: ~100MB
├─ PyAutoGUI: ~50MB
├─ Screenshot buffers: ~10MB
└─ Total: ~360MB
```

## Security Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Threat Surface                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Desktop Control (HIGH RISK)                                │
│  ├─ Can click anywhere on screen                           │
│  ├─ Can type any text (including passwords)                │
│  ├─ Can see everything visible                             │
│  └─ No sandboxing - full user permissions                  │
│                                                             │
│  Bash Access (HIGH RISK)                                    │
│  ├─ Can run any command                                    │
│  ├─ Can modify system files (if permissions allow)         │
│  ├─ Can install software                                   │
│  └─ Can access network                                     │
│                                                             │
│  File System (MEDIUM RISK)                                  │
│  ├─ Can read any user-accessible file                      │
│  ├─ Can write any user-accessible file                     │
│  ├─ Can delete files                                       │
│  └─ Respects file permissions                              │
│                                                             │
│  API Key (MEDIUM RISK)                                      │
│  ├─ Stored in ~/.anthropic/api_key (chmod 600)            │
│  ├─ Transmitted over HTTPS                                 │
│  └─ No local logging of API key                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Mitigations:**
1. Run in separate user account
2. Use Screen Recording to audit actions
3. Don't run on machine with sensitive data
4. Review prompts before execution
5. Monitor API usage for anomalies

## Extension Points

### Adding Custom Tools

```python
# 1. Create tool in tools/my_tool.py
from .base import BaseAnthropicTool, ToolResult

class MyCustomTool(BaseAnthropicTool):
    name = "my_tool"
    api_type = "my_tool_20250101"

    def to_params(self):
        return {
            "name": self.name,
            "description": "My custom tool",
            "input_schema": {...}
        }

    async def __call__(self, **kwargs):
        # Your logic here
        return ToolResult(output="Success!")

# 2. Add to tools/groups.py
from .my_tool import MyCustomTool

TOOL_GROUPS = [
    ToolGroup(
        version="computer_use_20250124",
        tools=[
            ComputerToolMacOS20250124,
            BashTool20250124,
            EditTool20250728,
            MyCustomTool,  # Added
        ],
    ),
]
```

### Customizing System Prompt

Edit `loop.py`:

```python
SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
* You are controlling a macOS machine...
* Custom instruction 1
* Custom instruction 2
</SYSTEM_CAPABILITY>

<CUSTOM_SECTION>
* Your custom rules here
</CUSTOM_SECTION>"""
```

---

*For more details, see individual source files or README.md*
