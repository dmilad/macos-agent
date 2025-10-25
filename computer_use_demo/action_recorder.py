"""
Action recording module for capturing and processing agent actions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types.beta import BetaContentBlockParam

from .tools import ToolResult


class ActionRecorder:
    """Records and processes agent actions during a session."""

    def __init__(self):
        self.request: dict[str, Any]
        self.actions: list[dict[str, Any]] = []
        self.session_id = datetime.now().isoformat()

    def record_user_message(self, message: str):
        """Record a user message."""
        self.actions.append({
            "type": "user_message",
            "content": {
                "text": message
            }
        })

    def record_thinking(self, thinking_content: str):
        """Record Claude's thinking block."""
        # Skip vectordb injected messages
        if thinking_content.startswith("Reference: I found a similar past task."):
            return

        self.actions.append({
            "type": "text",
            "content": {
                "text": thinking_content
            }
        })

    def record_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: ToolResult
    ):
        """Record a tool execution."""
        # Extract action name from tool_input if available
        action = tool_input.get("action", tool_input.get("command", ""))

        self.actions.append({
            "type": "tool_use",
            "content": {
                "tool_name": tool_name,
                "action": action,
                "inputs": tool_input,
                "output": tool_result.output,
                "error": tool_result.error
            }
        })

    def clear(self):
        """Clear all recorded actions and start a new session."""
        self.actions = []
        self.session_id = datetime.now().isoformat()

    async def process_and_save(self, api_key: str, output_dir: str = "recordings") -> str:
        """
        Process recorded actions using Claude to filter and create narrative,
        then save to JSON file.

        Returns the path to the saved file.
        """
        if not self.actions:
            raise ValueError("No actions to record")
        
        self.request = self.actions[0]

        # Use Claude to analyze and process the actions
        processed_data = await self._analyze_with_claude(api_key)

        # Prepare final JSON structure
        output = {
            "session_id": self.session_id,
            "recorded_at": datetime.now().isoformat(),
            "request": self.request,
            "all_actions": self.actions[1:],
            "successful_actions": processed_data["successful_actions"],
            "narrative": processed_data["narrative"]
        }

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"action_log_{timestamp}.json"
        filepath = Path(output_dir) / filename

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)

        return str(filepath)

    async def _analyze_with_claude(self, api_key: str) -> dict[str, Any]:
        """Use Claude to analyze actions and generate narrative."""
        client = AsyncAnthropic(api_key=api_key)

        # Create a prompt for Claude to analyze the actions
        prompt = self._create_analysis_prompt()

        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse Claude's response (expecting JSON)
        response_text = response.content[0].text

        # Extract JSON from the response (Claude might wrap it in markdown)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        return json.loads(response_text)

    def _create_analysis_prompt(self) -> str:
        """Create a prompt for Claude to analyze the recorded actions."""
        request_json = json.dumps(self.request, indent=2)
        actions_json = json.dumps(self.actions, indent=2)

        # Create the one-shot example
        example_input = [
            {"type": "thinking", "content": {"thinking": "I'll help you check how many p44 related messages you have in Notes. Let me start by taking a screenshot to see the current state of your screen, then open the Notes app."}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "screenshot", "inputs": {"action": "screenshot"}, "output": None, "error": None}},
            {"type": "thinking", "content": {"thinking": "I can see your desktop with a Terminal window and what appears to be a Chat application open. Now let me open the Notes app to search for p44 related messages. I'll use Spotlight to open Notes."}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "key", "inputs": {"action": "key", "text": "cmd+space"}, "output": "Pressed key: cmd + space", "error": None}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "screenshot", "inputs": {"action": "screenshot"}, "output": None, "error": None}},
            {"type": "thinking", "content": {"thinking": "It seems Spotlight didn't open. Let me try again and wait a moment."}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "key", "inputs": {"action": "key", "text": "cmd+space"}, "output": "Pressed key: cmd + space", "error": None}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "wait", "inputs": {"action": "wait", "duration": 1}, "output": None, "error": None}},
            {"type": "thinking", "content": {"thinking": "I can see there's a search bar at the top of the Chat window showing 'python3 - sh run.sh'. Let me try to open Notes using the bash command or by clicking in the Dock. Let me first try to use bash to open Notes."}},
            {"type": "tool_use", "content": {"tool_name": "bash", "action": "open -a Notes", "inputs": {"command": "open -a Notes"}, "output": "", "error": ""}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "wait", "inputs": {"action": "wait", "duration": 2}, "output": None, "error": None}},
            {"type": "thinking", "content": {"thinking": "Perfect! The Notes app is now open. I can see the sidebar with various folders and tags, including a '#p44' tag in the left sidebar. I can see there are 106 notes total in the 'Notes' folder. Now let me click on the #p44 tag to see how many notes are tagged with p44."}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "left_click", "inputs": {"action": "left_click", "coordinate": [35, 363]}, "output": None, "error": None}},
            {"type": "thinking", "content": {"thinking": "Excellent! I clicked on the #p44 tag and can see a message that says 'Show notes that match the selected tag: #p44.' at the top. I can see several notes listed in the middle column..."}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "scroll", "inputs": {"action": "scroll", "coordinate": [210, 400], "scroll_direction": "down", "scroll_amount": 5}, "output": None, "error": None}},
            {"type": "thinking", "content": {"thinking": "The view is the same. Let me scroll down in the note list column (the middle column) to see all the p44 notes. Let me scroll in that specific area."}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "scroll", "inputs": {"action": "scroll", "coordinate": [210, 450], "scroll_direction": "down", "scroll_amount": 10}, "output": None, "error": None}},
            {"type": "thinking", "content": {"thinking": "The list hasn't changed. It seems I can only see 6 notes in the middle column. However, I notice the #p44 tag is highlighted in the left sidebar. Let me try to use the search function to search for 'p44' to get a more accurate count. Let me click on the search box in the top right."}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "left_click", "inputs": {"action": "left_click", "coordinate": [1113, 45]}, "output": None, "error": None}},
            {"type": "thinking", "content": {"thinking": "Good! The search box is now active and showing suggested search categories. Let me type 'p44' in the search box."}},
            {"type": "tool_use", "content": {"tool_name": "computer", "action": "type", "inputs": {"action": "type", "text": "p44"}, "output": "Typed: p44", "error": None}},
            {"type": "thinking", "content": {"thinking": "Excellent! Now I can see the search results for 'p44'. The middle column shows different sections..."}}
        ]

        example_narrative = """The task was to determine how many p44-related messages exist in the Notes application on a macOS system.

The user wanted a count of all notes that contain references to 'p44', which appears to be a tag or project identifier used to organize their notes.

The agent approached this systematically by first opening the Notes application using the bash command 'open -a Notes':

{
  "type": "tool_use",
  "content": {
    "tool_name": "bash",
    "action": "open -a Notes",
    "inputs": {
      "command": "open -a Notes"
    },
    "output": "",
    "error": ""
  }
}

{
  "type": "tool_use",
  "content": {
    "tool_name": "computer",
    "action": "wait",
    "inputs": {
      "action": "wait",
      "duration": 2
    },
    "output": null,
    "error": null
  }
}

After waiting for the application to launch, the agent noticed that Notes had a sidebar with various folders and tags, including a '#p44' tag that was visible in the left sidebar. The agent clicked on this tag to filter notes by that specific tag.

{
  "type": "tool_use",
  "content": {
    "tool_name": "computer",
    "action": "left_click",
    "inputs": {
      "action": "left_click",
      "coordinate": [
        35,
        363
      ]
    },
    "output": null,
    "error": null
  }
}

To get a more comprehensive view of all p44-related content, the agent then used the search functionality.

{
  "type": "tool_use",
  "content": {
    "tool_name": "computer",
    "action": "left_click",
    "inputs": {
      "action": "left_click",
      "coordinate": [
        1113,
        45
      ]
    },
    "output": null,
    "error": null
  }
}

{
  "type": "tool_use",
  "content": {
    "tool_name": "computer",
    "action": "type",
    "inputs": {
      "action": "type",
      "text": "p44"
    },
    "output": "Typed: p44",
    "error": null
  }
}

By clicking on the search box in the top right corner of the Notes window and typing 'p44', the search results displayed all notes containing 'p44' in their content or tags. The results showed 7 notes organized into 'Top Hits' and 'Notes' sections, including items like '#p44 performance', '#p44 knowledge b...', 'interview notes', 'Belgrade', 'ethics point Report', 'ask anju for design', and 'NEXT 3'."""

        return f"""You are analyzing a log of actions taken by an AI agent to accomplish a task. Your job is to:

1. Identify the successful execution path by filtering out:
   - Failed attempts (actions with errors)
   - Retries and redundant actions
   - Exploratory actions that didn't contribute to the final solution
   - Any actions that were later corrected or superseded
   - All screenshots (The AI agent is instructed to confirm success at every step by taking a screenshot. You can ignore these.)

2. Create a clean list of only the successful actions that directly contributed to accomplishing the task.

3. Generate a narrative that is commentary interspersed with the critical path actions. The narrative should:
   - Explain what task was being accomplished
   - Provide explanatory text between action JSON objects
   - Include the actual JSON action objects inline (formatted properly with proper indentation)
   - Explain the reasoning and context for each action or group of actions
   - Focus on the "why" and "how", not just listing what happened

Here is an example to follow:

EXAMPLE INPUT (actions):
{json.dumps(example_input, indent=2)}

EXAMPLE OUTPUT (narrative):
{example_narrative}

Now analyze this task:

TASK:
{request_json}

RECORDED ACTIONS:
{actions_json}

Please respond with a JSON object in this exact format:
{{
  "successful_actions": [
    // Array of action objects (same structure as input) that were part of the successful path
  ],
  "narrative": "Commentary text explaining the task and approach...\\n\\n{{\\n  \\"type\\": \\"tool_use\\",\\n  \\"content\\": {{...}}\\n}}\\n\\nMore commentary explaining what happened next..."
}}

Important:
- Only include actions that directly contributed to the successful completion of the task
- Remove screenshots, thinking blocks, and any failed attempts, errors, or backtracking from successful_actions
- The narrative must interleave explanatory text with JSON action objects
- Format the JSON objects properly within the narrative string (use proper indentation as shown in the example)
- The narrative should tell a coherent story of how the task was accomplished
"""

    def get_action_count(self) -> int:
        """Return the number of recorded actions."""
        return len(self.actions)
