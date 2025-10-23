# Migration Notes: Docker/Linux → macOS Native

This document explains what was changed to adapt the original computer-use-demo to run natively on macOS.

## Summary of Changes

### Core Architecture: UNCHANGED ✅
- Agent loop logic ([loop.py](computer_use_demo/loop.py))
- Tool collection system ([tools/collection.py](computer_use_demo/tools/collection.py))
- API integration with Anthropic/Bedrock/Vertex
- Message handling and prompt caching
- Streamlit UI structure

### Tools: MIXED Changes

#### Unchanged Tools ✅
- **Bash Tool** ([tools/bash.py](computer_use_demo/tools/bash.py))
  - Works identically on macOS
  - Executes bash commands in persistent session
  - No modifications needed

- **Edit Tool** ([tools/edit.py](computer_use_demo/tools/edit.py))
  - File operations (view, create, str_replace, insert, undo)
  - Cross-platform by nature
  - No modifications needed

- **Tool Infrastructure**
  - [tools/base.py](computer_use_demo/tools/base.py) - Base classes
  - [tools/collection.py](computer_use_demo/tools/collection.py) - Tool management
  - [tools/run.py](computer_use_demo/tools/run.py) - Command runner

#### Replaced Tool 🔄
- **Computer Tool** ([tools/computer_macos.py](computer_use_demo/tools/computer_macos.py))
  - **Original:** Linux-specific using `xdotool`, `scrot`, X11
  - **New:** macOS-native using PyAutoGUI
  - **Interface:** Identical API, different implementation

#### Updated Configuration 📝
- **Tool Groups** ([tools/groups.py](computer_use_demo/tools/groups.py))
  - Changed imports from `computer.py` → `computer_macos.py`
  - Updated class references: `ComputerTool*` → `ComputerToolMacOS*`

### System Prompt: UPDATED 📝

**Original (Ubuntu):**
```python
* You are utilising an Ubuntu virtual machine...
* To open firefox, please just click on the firefox icon...
* Using bash tool you can start GUI applications, but you need to set export DISPLAY=:1...
```

**New (macOS):**
```python
* You are controlling a macOS machine...
* Common browsers: Safari, Chrome, Firefox...
* Use `open -a AppName` or click Dock icons...
* macOS uses Command (Cmd) key instead of Ctrl...
```

### Removed Components ❌

1. **Docker Infrastructure**
   - Dockerfile
   - Docker Compose
   - Container startup scripts

2. **Virtual Display Stack**
   - Xvfb (X virtual framebuffer)
   - x11vnc (VNC server)
   - noVNC (browser VNC client)
   - mutter (window manager)
   - tint2 (taskbar)

3. **Desktop Environment Scripts**
   - `image/entrypoint.sh`
   - `image/start_all.sh`
   - `image/xvfb_startup.sh`
   - `image/x11vnc_startup.sh`
   - `image/novnc_startup.sh`
   - `image/tint2_startup.sh`
   - `image/mutter_startup.sh`
   - `image/http_server.py`

4. **UI Code for Docker**
   - Xvfb restart functionality in Streamlit
   - Desktop environment reset logic

### New Components ✨

1. **macOS Computer Tool** ([tools/computer_macos.py](computer_use_demo/tools/computer_macos.py))
   - PyAutoGUI-based implementation
   - macOS keyboard mapping (Ctrl → Command)
   - Native screenshot capture
   - All original actions supported

2. **Modern Package Management**
   - [pyproject.toml](pyproject.toml) - uv/pip compatible
   - Replaced pip requirements.txt

3. **Setup Scripts**
   - [setup.sh](setup.sh) - Environment setup with uv
   - [run.sh](run.sh) - Simple launcher

4. **Documentation**
   - [README.md](README.md) - Comprehensive guide
   - [QUICKSTART.md](QUICKSTART.md) - 5-minute getting started
   - [MIGRATION_NOTES.md](MIGRATION_NOTES.md) - This file

## Technical Deep Dive

### Computer Tool Implementation Comparison

#### Linux (xdotool)
```bash
# Mouse move
xdotool mousemove --sync 100 200

# Click
xdotool click 1

# Type
xdotool type --delay 12 "Hello"

# Screenshot
scrot -p screenshot.png
convert screenshot.png -resize 1024x768! screenshot.png
```

#### macOS (PyAutoGUI)
```python
# Mouse move
pyautogui.moveTo(100, 200, duration=0.2)

# Click
pyautogui.click()

# Type
pyautogui.write("Hello", interval=0.012)

# Screenshot
screenshot = pyautogui.screenshot()
screenshot.resize((1024, 768), Image.LANCZOS)
```

### Key Translation

The most critical change was keyboard key translation:

```python
MACOS_KEY_MAPPING = {
    "ctrl": "command",          # macOS primary modifier
    "Control_L": "command",
    "alt": "option",            # macOS option key
    "Alt_L": "option",
    "super": "command",         # Windows key → Command
    "Return": "enter",
    "BackSpace": "backspace",
    # ... 40+ mappings
}
```

### Screenshot Scaling

Both implementations scale screenshots to optimize API costs:

**Original:**
```python
# Using ImageMagick convert
await shell(f"convert {path} -resize {x}x{y}! {path}")
```

**macOS:**
```python
# Using Pillow
screenshot = screenshot.resize(
    (target_width, target_height),
    Image.LANCZOS
)
```

### Async Execution

Both use async/await, but PyAutoGUI requires thread wrapping:

```python
# Run PyAutoGUI in thread to avoid blocking
await asyncio.to_thread(pyautogui.click)
await asyncio.to_thread(pyautogui.screenshot)
```

## Dependency Changes

### Removed Dependencies
- Docker-specific: N/A (not in Python requirements)
- System packages installed in Dockerfile: xdotool, scrot, xvfb, etc.

### Added Dependencies
- `pyautogui>=0.9.54` - Desktop automation
- `pillow>=10.0.0` - Image processing (required by pyautogui)

### Unchanged Dependencies
- `streamlit>=1.41.0` - UI framework
- `anthropic[bedrock,vertex]>=0.39.0` - Claude API
- `jsonschema>=4.22.0` - Validation
- `boto3>=1.28.57` - AWS SDK
- `google-auth>=2,<3` - Google Cloud auth

## Configuration Differences

### Environment Variables

**Docker/Linux:**
```bash
DISPLAY_NUM=1           # X11 display number
WIDTH=1024              # Virtual display size
HEIGHT=768
ANTHROPIC_API_KEY       # API key
```

**macOS:**
```bash
WIDTH=1440              # Actual screen size (auto-detected)
HEIGHT=900
ANTHROPIC_API_KEY       # API key
# DISPLAY_NUM removed (not needed)
```

### Storage

**Both versions:**
- Config directory: `~/.anthropic/`
- API key storage: `~/.anthropic/api_key`
- Screenshot output: `/tmp/outputs/`

## File-by-File Changes

| File | Status | Changes |
|------|--------|---------|
| `loop.py` | Modified | System prompt updated for macOS |
| `streamlit.py` | Modified | Removed Xvfb restart code |
| `tools/__init__.py` | Unchanged | No changes |
| `tools/base.py` | Unchanged | No changes |
| `tools/bash.py` | Unchanged | No changes |
| `tools/edit.py` | Unchanged | No changes |
| `tools/collection.py` | Unchanged | No changes |
| `tools/run.py` | Unchanged | No changes |
| `tools/computer.py` | Removed | Replaced by computer_macos.py |
| `tools/computer_macos.py` | **NEW** | PyAutoGUI implementation |
| `tools/groups.py` | Modified | Import paths updated |
| `pyproject.toml` | **NEW** | Modern package config |
| `setup.sh` | **NEW** | uv-based setup |
| `run.sh` | **NEW** | Launch script |
| `README.md` | **NEW** | macOS documentation |

## Testing Checklist

Before using this implementation, verify:

- [ ] uv is installed
- [ ] Python 3.11+ available
- [ ] Virtual environment created (`./setup.sh`)
- [ ] Dependencies installed
- [ ] Accessibility permissions granted
- [ ] Screen Recording permissions granted
- [ ] API key configured
- [ ] Streamlit starts without errors
- [ ] Screenshots work (test with "take a screenshot")
- [ ] Mouse movement works (test with "move mouse to center")
- [ ] Keyboard typing works (test with "open TextEdit and type hello")
- [ ] Bash commands work (test with "run ls in terminal")
- [ ] File editing works (test with "create a file on Desktop")

## Known Differences in Behavior

### 1. Screen Control
- **Docker:** Controls virtual display, isolated from host
- **macOS:** Controls actual desktop, visible to user

### 2. Application Launch
- **Docker:** Apps already installed in container
- **macOS:** May need to install apps via Homebrew

### 3. Browser Default
- **Docker:** Firefox ESR pre-installed
- **macOS:** Safari is default, Chrome/Firefox optional

### 4. Coordinate Precision
- **Docker:** Virtual display, perfect control
- **macOS:** Real desktop, may have timing issues

### 5. Performance
- **Docker:** Slower (virtualization overhead)
- **macOS:** Faster (native execution)

### 6. Security
- **Docker:** Isolated container
- **macOS:** Full system access ⚠️

## Future Improvements

Potential enhancements for the macOS version:

1. **Window Management Tool**
   - Detect active window
   - Switch between applications
   - Manage window positions

2. **AppleScript Integration**
   - Native macOS automation
   - Better app control
   - System-level operations

3. **Accessibility API**
   - Direct UI element access
   - More reliable than pixel-based control

4. **Safe Mode**
   - Confirmation prompts before destructive actions
   - Undo functionality
   - Action logging

5. **Multi-Monitor Support**
   - Detect multiple displays
   - Choose which screen to control

6. **Improved Error Handling**
   - Better recovery from failed actions
   - Retry logic for clicks
   - Fallback strategies

## Questions & Answers

**Q: Why PyAutoGUI instead of AppleScript?**
A: PyAutoGUI provides a cross-platform API similar to the original xdotool, making migration easier. AppleScript could be added as an enhancement.

**Q: Can I run this alongside the Docker version?**
A: Yes, they're completely independent. This version doesn't require Docker at all.

**Q: Will this work on Linux?**
A: No, this version is macOS-specific. Use the original Docker version for Linux.

**Q: Can I contribute this back to the original repo?**
A: This is a personal adaptation. The official repo focuses on the Docker version for consistency across platforms.

**Q: What about Windows support?**
A: PyAutoGUI works on Windows too! You'd need to adapt the system prompt and ensure all tools work on Windows, but the core logic should transfer.

## Credits

- **Original implementation:** Anthropic (computer-use-demo)
- **macOS adaptation:** Custom implementation
- **Libraries used:** PyAutoGUI, Streamlit, Anthropic SDK, Pillow

---

*Last updated: 2025-10-22*
