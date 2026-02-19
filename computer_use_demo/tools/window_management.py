"""
macOS Window Management Tool using the Accessibility API via AppleScript.

Provides reliable window discovery and focus operations without coordinate guessing.
Complements the computer tool: use this for navigation/focus, use computer for
pixel-level interaction with content that isn't in the accessibility tree (e.g. web pages).
"""

import asyncio
import subprocess
from typing import Any, Literal

from .base import BaseAnthropicTool, ToolError, ToolResult

WindowAction = Literal[
    "list_apps",
    "list_windows",
    "get_frontmost",
    "focus_app",
    "focus_window",
]


def _sanitize(value: str) -> str:
    """Strip characters that could break AppleScript string literals."""
    return value.replace('"', "").replace("\\", "").replace("\n", " ")


async def _run_applescript(script: str) -> str:
    """Run an AppleScript string via osascript and return stdout."""
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise ToolError(f"AppleScript error: {result.stderr.strip()}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise ToolError("Window management command timed out after 10 seconds")


class WindowManagementTool(BaseAnthropicTool):
    """
    Manage macOS windows via the Accessibility API (AppleScript/osascript).

    Use this instead of screenshot + coordinate clicking for all window navigation:
    listing apps, switching focus, raising specific windows. Fall back to the
    computer tool only for content not exposed by the accessibility tree (web pages,
    canvas UIs, games).
    """

    name: Literal["window_management"] = "window_management"

    def to_params(self) -> Any:
        return {
            "name": self.name,
            "description": (
                "Manage macOS windows using the Accessibility API. "
                "Use this for: listing running apps, listing open windows, "
                "finding the frontmost app/window, bringing an app to the front, "
                "and raising a specific window. "
                "Prefer this over screenshots + coordinate clicking for all window "
                "navigation tasks — it is faster, more reliable, and uses no screenshot tokens."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "list_apps",
                            "list_windows",
                            "get_frontmost",
                            "focus_app",
                            "focus_window",
                        ],
                        "description": (
                            "list_apps: List all running GUI applications. "
                            "list_windows: List open windows; filter by app_name if provided. "
                            "get_frontmost: Return the currently focused app and window title. "
                            "focus_app: Bring an app to the front by name (no window required). "
                            "focus_window: Raise a specific window by app_name; use window_title "
                            "to disambiguate when an app has multiple windows."
                        ),
                    },
                    "app_name": {
                        "type": "string",
                        "description": (
                            "Application name exactly as shown in the Dock or Activity Monitor "
                            "(e.g. 'Finder', 'Google Chrome', 'Notes', 'Terminal'). "
                            "Required for focus_app and focus_window."
                        ),
                    },
                    "window_title": {
                        "type": "string",
                        "description": (
                            "Substring to match against window titles. "
                            "Used by focus_window to select among multiple windows of the same app. "
                            "If omitted, the frontmost window of app_name is raised."
                        ),
                    },
                },
                "required": ["action"],
            },
        }

    async def __call__(
        self,
        *,
        action: WindowAction,
        app_name: str | None = None,
        window_title: str | None = None,
        **kwargs,
    ) -> ToolResult:
        if action == "list_apps":
            return await self._list_apps()
        elif action == "list_windows":
            return await self._list_windows(app_name)
        elif action == "get_frontmost":
            return await self._get_frontmost()
        elif action == "focus_app":
            if not app_name:
                raise ToolError("app_name is required for focus_app")
            return await self._focus_app(app_name)
        elif action == "focus_window":
            if not app_name:
                raise ToolError("app_name is required for focus_window")
            return await self._focus_window(app_name, window_title)
        else:
            raise ToolError(f"Invalid action: {action}")

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    async def _list_apps(self) -> ToolResult:
        script = """
tell application "System Events"
    set appNames to name of every process where background only is false
    set output to ""
    repeat with appName in appNames
        set output to output & appName & "\n"
    end repeat
    return output
end tell
"""
        result = await _run_applescript(script)
        apps = sorted(line.strip() for line in result.splitlines() if line.strip())
        if not apps:
            return ToolResult(output="No running GUI applications found.")
        return ToolResult(output="Running applications:\n" + "\n".join(f"  • {a}" for a in apps))

    async def _list_windows(self, app_name: str | None) -> ToolResult:
        if app_name:
            safe_name = _sanitize(app_name)
            script = f"""
tell application "System Events"
    set output to ""
    try
        tell process "{safe_name}"
            repeat with win in every window
                set winName to name of win
                if winName is "" then set winName to "(untitled)"
                set output to output & "{safe_name} | " & winName & "\\n"
            end repeat
        end tell
    on error errMsg
        set output to "Error accessing " & "{safe_name}" & ": " & errMsg
    end try
    return output
end tell
"""
        else:
            script = """
tell application "System Events"
    set output to ""
    repeat with proc in (every process where background only is false)
        set appName to name of proc
        try
            repeat with win in every window of proc
                set winName to name of win
                if winName is "" then set winName to "(untitled)"
                set output to output & appName & " | " & winName & "\\n"
            end repeat
        end try
    end repeat
    return output
end tell
"""
        result = await _run_applescript(script)
        lines = [line.strip() for line in result.splitlines() if line.strip()]
        if not lines:
            label = (
                f"No windows found for '{app_name}'."
                if app_name
                else "No open windows found."
            )
            return ToolResult(output=label)
        header = "Open windows  (format: App | Window Title):"
        return ToolResult(output=header + "\n" + "\n".join(f"  • {l}" for l in lines))

    async def _get_frontmost(self) -> ToolResult:
        script = """
tell application "System Events"
    set frontProc to first process where frontmost is true
    set appName to name of frontProc
    set winTitle to ""
    try
        set winTitle to name of front window of frontProc
    end try
    return appName & " | " & winTitle
end tell
"""
        result = await _run_applescript(script)
        parts = result.split(" | ", 1)
        app = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ""
        return ToolResult(
            output=f"Frontmost app:    {app}\n"
            f"Frontmost window: {title or '(no window title)'}"
        )

    async def _focus_app(self, app_name: str) -> ToolResult:
        safe_name = _sanitize(app_name)
        script = f"""
tell application "System Events"
    set matches to every process where name is "{safe_name}"
    if (count of matches) is 0 then
        error "No running process named \\"{safe_name}\\""
    end if
    set frontmost of first item of matches to true
end tell
"""
        await _run_applescript(script)
        return ToolResult(output=f"Focused app: {app_name}")

    async def _focus_window(self, app_name: str, window_title: str | None) -> ToolResult:
        safe_name = _sanitize(app_name)

        if window_title:
            safe_title = _sanitize(window_title)
            script = f"""
tell application "System Events"
    tell process "{safe_name}"
        set frontmost to true
        repeat with win in every window
            if name of win contains "{safe_title}" then
                perform action "AXRaise" of win
                return "Raised: " & name of win
            end if
        end repeat
        return "No window matching \\"{safe_title}\\" found in {safe_name}"
    end tell
end tell
"""
        else:
            # No title filter — raise frontmost window of the app
            script = f"""
tell application "System Events"
    tell process "{safe_name}"
        set frontmost to true
        try
            perform action "AXRaise" of front window
            return "Raised front window of {safe_name}"
        on error
            return "Brought {safe_name} to front"
        end try
    end tell
end tell
"""
        result = await _run_applescript(script)
        return ToolResult(output=result)
