# Quick Start Guide - macOS Agent

Get up and running in 5 minutes!

## Prerequisites Check

```bash
# Check if you have uv installed
uv --version

# If not, install it:
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

```bash
# 1. Navigate to the project
cd macos-agent

# 2. Run setup script
./setup.sh

# 3. Set your API key (get one at console.anthropic.com)
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

## First Run

```bash
# Start the agent
./run.sh
```

This will:
1. Activate the virtual environment
2. Set screen dimensions (1440x900)
3. Start Streamlit at http://localhost:8501

**Open your browser to http://localhost:8501**

## Grant Permissions

On first run, macOS will ask for permissions:

### Accessibility Permission (Required)
1. System Settings > Privacy & Security > Accessibility
2. Click lock icon to make changes
3. Toggle ON for Terminal (or Python)
4. Restart the agent

### Screen Recording (Auto-granted)
May automatically grant, or you'll see a prompt.

## Try Your First Task

In the Streamlit UI:

1. **Enter your API key** if not set as environment variable
2. **Type a prompt** in the chat input:
   ```
   Open Calculator and compute 42 * 137
   ```
3. **Watch Claude work!** It will:
   - Take a screenshot to see the desktop
   - Find and click the Calculator icon
   - Type the numbers
   - Return the result

## Example Prompts

### Simple (Quick Test)
```
Take a screenshot and describe what you see
```

### Basic Automation
```
Open TextEdit and write "Hello from Claude!"
```

### Web Browsing
```
Open Chrome and search for "latest macOS features"
```

### File Operations
```
Create a file called test.txt on the Desktop with the text "Agent test"
```

### Multi-Step Task
```
Open Notes, create a new note titled "My Tasks", and add:
- Check email
- Review code
- Meeting at 3pm
```

## Configuration

### Use a different model
In the Streamlit sidebar:
- Default: `claude-sonnet-4-5-20250929`
- Faster: `claude-haiku-4-5-20251001`
- Most capable: `claude-opus-4-20250514`

### Adjust output tokens
In the Streamlit sidebar:
- Lower (1024) = faster, cheaper, less complex tasks
- Higher (16384) = slower, more expensive, complex tasks

### Tool version
- `computer_use_20250124` (recommended) - Full features
- `computer_use_20241022` - Original version

## Stopping the Agent

- **In browser:** Click the "Stop" button in Streamlit UI
- **In terminal:** Press `Ctrl+C`
- **Emergency:** Close terminal window

## Common Issues

### "Permission denied" for Accessibility
→ Grant in System Settings > Privacy & Security > Accessibility

### "ModuleNotFoundError"
→ Run `./setup.sh` again

### "API key not found"
→ `export ANTHROPIC_API_KEY='your-key'` before running

### Agent clicks wrong things
→ Lower screen resolution or be more specific in prompts

### Screenshots failing
→ Grant Screen Recording permission in System Settings

## Learning from Tasks (Optional)

The agent can record successful tasks and learn from them:

### Record a Task
After completing a task successfully:
1. Click the "Record this session" button in the UI
2. The agent saves the successful actions to `recordings/`

### Build the Knowledge Base
```bash
# After recording several tasks
python -m computer_use_demo.build_index
```

### Enable Learning
1. In the Streamlit sidebar, toggle "Use vector DB for similar tasks"
2. The agent will now retrieve similar past solutions for new requests

See [README.md](README.md#action-recording--learning) for full details.

## What's Next?

1. **Read the full README.md** for detailed documentation
2. **Try more complex tasks** like web scraping or file management
3. **Record successful tasks** to build up a knowledge base
4. **Customize the system prompt** in `computer_use_demo/loop.py`
5. **Build your own tools** - see README.md "Development" section
6. **Monitor API usage** at console.anthropic.com

## Cost Awareness

- Each screenshot ≈ 1,500 tokens (at 1440x900, scaled to 800x450)
- Each agent turn ≈ 3-5 screenshots
- Simple task ≈ 10,000-20,000 tokens (~$0.03-$0.06 with Sonnet 4)
- Complex task ≈ 50,000-100,000 tokens (~$0.15-$0.30 with Sonnet 4)

Use Haiku for simple tasks to reduce costs by ~90%!

## Safety Reminder

⚠️ **This agent controls your actual desktop!**

- Start with simple tasks
- Don't run on a machine with sensitive data
- Monitor what it's doing
- Use a separate user account for isolation (recommended)

## Support

- **Issues with the agent:** Check README.md troubleshooting section
- **API questions:** https://docs.anthropic.com/
- **PyAutoGUI questions:** https://pyautogui.readthedocs.io/

---

**Ready to build amazing agents? Let's go! 🚀**
