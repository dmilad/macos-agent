"""
macOS-native computer control tool using PyAutoGUI.
Replaces xdotool-based Linux implementation with native macOS automation.
"""

import asyncio
import base64
import os
from io import BytesIO
from pathlib import Path
from enum import StrEnum
from typing import Literal, TypedDict, cast, get_args
from uuid import uuid4

from anthropic.types.beta import BetaToolUnionParam

import pyautogui
from PIL import Image
from .base import BaseAnthropicTool, ToolError, ToolResult

OUTPUT_DIR = "/tmp/outputs"

TYPING_DELAY_MS = 0.012  # Convert to seconds for PyAutoGUI
TYPING_GROUP_SIZE = 50

Action_20241022 = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "screenshot",
    "cursor_position",
]

Action_20250124 = (
    Action_20241022
    | Literal[
        "left_mouse_down",
        "left_mouse_up",
        "scroll",
        "hold_key",
        "wait",
        "triple_click",
    ]
)

ScrollDirection = Literal["up", "down", "left", "right"]


class Resolution(TypedDict):
    width: int
    height: int


# sizes above XGA/WXGA are not recommended (see README.md)
# scale down to one of these targets if ComputerTool._scaling_enabled is set
MAX_SCALING_TARGETS: dict[str, Resolution] = {
    "XGA": Resolution(width=1024, height=768),  # 4:3
    "WXGA": Resolution(width=1280, height=800),  # 16:10
    "FWXGA": Resolution(width=1366, height=768),  # ~16:9
}


class ScalingSource(StrEnum):
    COMPUTER = "computer"
    API = "api"


class ComputerToolOptions(TypedDict):
    display_height_px: int
    display_width_px: int
    display_number: int | None


def chunks(s: str, chunk_size: int) -> list[str]:
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]


# macOS keyboard mapping from X11/Linux keys to PyAutoGUI keys
MACOS_KEY_MAPPING = {
    # Modifier keys
    "ctrl": "command",  # macOS uses Command instead of Ctrl
    "Control_L": "command",
    "Control_R": "command",
    "alt": "option",
    "Alt_L": "option",
    "Alt_R": "option",
    "super": "command",
    "Super_L": "command",
    "Super_R": "command",
    "Meta_L": "command",
    "Meta_R": "command",
    # Special keys
    "Return": "enter",
    "KP_Enter": "enter",
    "BackSpace": "backspace",
    "Tab": "tab",
    "Escape": "esc",
    "Delete": "delete",
    "Home": "home",
    "End": "end",
    "Page_Up": "pageup",
    "Page_Down": "pagedown",
    "Prior": "pageup",
    "Next": "pagedown",
    # Arrow keys
    "Up": "up",
    "Down": "down",
    "Left": "left",
    "Right": "right",
    # Function keys
    **{f"F{i}": f"f{i}" for i in range(1, 13)},
    # Lock keys
    "Caps_Lock": "capslock",
    "Num_Lock": "numlock",
    # Other
    "Insert": "insert",
    "Print": "printscreen",
    "space": "space",
}


def translate_key(key: str) -> str:
    """Translate X11/Linux key names to macOS/PyAutoGUI key names."""
    return MACOS_KEY_MAPPING.get(key, key.lower())


class BaseComputerToolMacOS:
    """
    A tool that allows the agent to interact with the screen, keyboard, and mouse of the macOS computer.
    Uses PyAutoGUI for native macOS automation instead of xdotool.
    """

    name: Literal["computer"] = "computer"
    width: int
    height: int
    display_num: int | None

    _screenshot_delay = 1.0
    _scaling_enabled = True

    @property
    def options(self) -> ComputerToolOptions:
        width, height = self.scale_coordinates(
            ScalingSource.COMPUTER, self.width, self.height
        )
        return {
            "display_width_px": width,
            "display_height_px": height,
            "display_number": self.display_num,
        }

    def __init__(self):
        super().__init__()

        # Get screen dimensions - default to environment vars or actual screen size
        self.width = int(os.getenv("WIDTH") or 0)
        self.height = int(os.getenv("HEIGHT") or 0)

        if not self.width or not self.height:
            # Auto-detect screen size using PyAutoGUI
            screen_size = pyautogui.size()
            self.width = screen_size.width
            self.height = screen_size.height

        # Display number not used on macOS (no X11)
        self.display_num = None

        # Configure PyAutoGUI
        pyautogui.FAILSAFE = False  # Disable failsafe for automation
        pyautogui.PAUSE = 0.01  # Small pause between PyAutoGUI calls

    async def __call__(
        self,
        *,
        action: Action_20241022,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        **kwargs,
    ):
        if action in ("mouse_move", "left_click_drag"):
            if coordinate is None:
                raise ToolError(f"coordinate is required for {action}")
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")

            x, y = self.validate_and_get_coordinates(coordinate)

            if action == "mouse_move":
                await asyncio.to_thread(pyautogui.moveTo, x, y, duration=0.2)
                return ToolResult(output=f"Moved mouse to ({x}, {y})")
            elif action == "left_click_drag":
                current_pos = pyautogui.position()
                await asyncio.to_thread(pyautogui.drag, x - current_pos[0], y - current_pos[1], duration=0.5, button='left')
                return await self.screenshot()

        if action in ("key", "type"):
            if text is None:
                raise ToolError(f"text is required for {action}")
            if coordinate is not None:
                raise ToolError(f"coordinate is not accepted for {action}")
            if not isinstance(text, str):
                raise ToolError(output=f"{text} must be a string")

            if action == "key":
                # Handle key combinations (e.g., "ctrl+c" becomes "command+c")
                keys = [translate_key(k.strip()) for k in text.split("+")]
                try:
                    await asyncio.to_thread(pyautogui.hotkey, *keys)
                    return ToolResult(output=f"Pressed key: {' + '.join(keys)}")
                except Exception as e:
                    raise ToolError(f"Failed to press keys {keys}: {str(e)}")

            elif action == "type":
                results: list[ToolResult] = []
                for chunk in chunks(text, TYPING_GROUP_SIZE):
                    await asyncio.to_thread(pyautogui.write, chunk, interval=TYPING_DELAY_MS)
                    results.append(ToolResult(output=f"Typed: {chunk}"))

                await asyncio.sleep(self._screenshot_delay)
                screenshot_base64 = (await self.screenshot()).base64_image
                return ToolResult(
                    output="".join(result.output or "" for result in results),
                    base64_image=screenshot_base64,
                )

        if action in (
            "left_click",
            "right_click",
            "double_click",
            "middle_click",
            "screenshot",
            "cursor_position",
        ):
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            if coordinate is not None:
                raise ToolError(f"coordinate is not accepted for {action}")

            if action == "screenshot":
                return await self.screenshot()
            elif action == "cursor_position":
                pos = await asyncio.to_thread(pyautogui.position)
                x, y = self.scale_coordinates(ScalingSource.COMPUTER, pos[0], pos[1])
                return ToolResult(output=f"X={x},Y={y}")
            elif action == "left_click":
                await asyncio.to_thread(pyautogui.click)
                await asyncio.sleep(self._screenshot_delay)
                return await self.screenshot()
            elif action == "right_click":
                await asyncio.to_thread(pyautogui.rightClick)
                await asyncio.sleep(self._screenshot_delay)
                return await self.screenshot()
            elif action == "middle_click":
                await asyncio.to_thread(pyautogui.middleClick)
                await asyncio.sleep(self._screenshot_delay)
                return await self.screenshot()
            elif action == "double_click":
                await asyncio.to_thread(pyautogui.doubleClick)
                await asyncio.sleep(self._screenshot_delay)
                return await self.screenshot()

        raise ToolError(f"Invalid action: {action}")

    def validate_and_get_coordinates(self, coordinate: tuple[int, int] | None = None):
        if not isinstance(coordinate, list) or len(coordinate) != 2:
            raise ToolError(f"{coordinate} must be a tuple of length 2")
        if not all(isinstance(i, int) and i >= 0 for i in coordinate):
            raise ToolError(f"{coordinate} must be a tuple of non-negative ints")

        return self.scale_coordinates(ScalingSource.API, coordinate[0], coordinate[1])

    async def screenshot(self):
        """Take a screenshot of the current screen and return the base64 encoded image."""
        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"screenshot_{uuid4().hex}.png"

        # Take screenshot using PyAutoGUI
        screenshot = await asyncio.to_thread(pyautogui.screenshot)

        # Scale if needed
        if self._scaling_enabled:
            target_width, target_height = self.scale_coordinates(
                ScalingSource.COMPUTER, self.width, self.height
            )
            # Only resize if scaling is actually needed
            if target_width != self.width or target_height != self.height:
                screenshot = screenshot.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS
                )

        # Save screenshot
        await asyncio.to_thread(screenshot.save, path, "PNG")

        # Convert to base64
        buffered = BytesIO()
        await asyncio.to_thread(screenshot.save, buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        return ToolResult(base64_image=img_base64)

    def scale_coordinates(self, source: ScalingSource, x: int, y: int):
        """Scale coordinates to a target maximum resolution."""
        if not self._scaling_enabled:
            return x, y
        ratio = self.width / self.height
        target_dimension = None
        for dimension in MAX_SCALING_TARGETS.values():
            # allow some error in the aspect ratio - not all ratios are exactly 16:9
            if abs(dimension["width"] / dimension["height"] - ratio) < 0.02:
                if dimension["width"] < self.width:
                    target_dimension = dimension
                break
        if target_dimension is None:
            return x, y
        # should be less than 1
        x_scaling_factor = target_dimension["width"] / self.width
        y_scaling_factor = target_dimension["height"] / self.height
        if source == ScalingSource.API:
            if x > self.width or y > self.height:
                raise ToolError(f"Coordinates {x}, {y} are out of bounds")
            # scale up
            return round(x / x_scaling_factor), round(y / y_scaling_factor)
        # scale down
        return round(x * x_scaling_factor), round(y * y_scaling_factor)


class ComputerToolMacOS20241022(BaseComputerToolMacOS, BaseAnthropicTool):
    api_type: Literal["computer_20241022"] = "computer_20241022"

    def to_params(self):
        return {"name": self.name, "type": self.api_type, **self.options}


class ComputerToolMacOS20250124(BaseComputerToolMacOS, BaseAnthropicTool):
    api_type: Literal["computer_20250124"] = "computer_20250124"

    def to_params(self):
        return cast(
            BetaToolUnionParam,
            {"name": self.name, "type": self.api_type, **self.options},
        )

    async def __call__(
        self,
        *,
        action: Action_20250124,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        scroll_direction: ScrollDirection | None = None,
        scroll_amount: int | None = None,
        duration: int | float | None = None,
        key: str | None = None,
        **kwargs,
    ):
        if action in ("left_mouse_down", "left_mouse_up"):
            if coordinate is not None:
                raise ToolError(f"coordinate is not accepted for {action=}.")

            if action == "left_mouse_down":
                await asyncio.to_thread(pyautogui.mouseDown)
            else:
                await asyncio.to_thread(pyautogui.mouseUp)
            return ToolResult(output=f"Mouse button {'down' if action == 'left_mouse_down' else 'up'}")

        if action == "scroll":
            if scroll_direction is None or scroll_direction not in get_args(ScrollDirection):
                raise ToolError(
                    f"{scroll_direction=} must be 'up', 'down', 'left', or 'right'"
                )
            if not isinstance(scroll_amount, int) or scroll_amount < 0:
                raise ToolError(f"{scroll_amount=} must be a non-negative int")

            # Move to coordinate if provided
            if coordinate is not None:
                x, y = self.validate_and_get_coordinates(coordinate)
                await asyncio.to_thread(pyautogui.moveTo, x, y, duration=0.2)

            # Press modifier key if provided
            if text:
                translated_key = translate_key(text)
                await asyncio.to_thread(pyautogui.keyDown, translated_key)

            # Perform scroll
            # PyAutoGUI uses positive for up/right, negative for down/left
            if scroll_direction == "up":
                await asyncio.to_thread(pyautogui.scroll, scroll_amount * 10)
            elif scroll_direction == "down":
                await asyncio.to_thread(pyautogui.scroll, -scroll_amount * 10)
            elif scroll_direction == "left":
                await asyncio.to_thread(pyautogui.hscroll, -scroll_amount * 10)
            elif scroll_direction == "right":
                await asyncio.to_thread(pyautogui.hscroll, scroll_amount * 10)

            # Release modifier key
            if text:
                await asyncio.to_thread(pyautogui.keyUp, translated_key)

            await asyncio.sleep(self._screenshot_delay)
            return await self.screenshot()

        if action in ("hold_key", "wait"):
            if duration is None or not isinstance(duration, (int, float)):
                raise ToolError(f"{duration=} must be a number")
            if duration < 0:
                raise ToolError(f"{duration=} must be non-negative")
            if duration > 100:
                raise ToolError(f"{duration=} is too long.")

            if action == "hold_key":
                if text is None:
                    raise ToolError(f"text is required for {action}")
                translated_keys = [translate_key(k.strip()) for k in text.split("+")]

                # Press keys down
                for k in translated_keys:
                    await asyncio.to_thread(pyautogui.keyDown, k)

                # Hold
                await asyncio.sleep(duration)

                # Release keys
                for k in reversed(translated_keys):
                    await asyncio.to_thread(pyautogui.keyUp, k)

                await asyncio.sleep(self._screenshot_delay)
                return await self.screenshot()

            if action == "wait":
                await asyncio.sleep(duration)
                return await self.screenshot()

        if action == "triple_click":
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")

            # Move to coordinate if provided
            if coordinate is not None:
                x, y = self.validate_and_get_coordinates(coordinate)
                await asyncio.to_thread(pyautogui.moveTo, x, y, duration=0.2)

            # Press modifier key if provided
            if key:
                translated_key = translate_key(key)
                await asyncio.to_thread(pyautogui.keyDown, translated_key)

            # Triple click
            await asyncio.to_thread(pyautogui.click, clicks=3)

            # Release modifier key
            if key:
                await asyncio.to_thread(pyautogui.keyUp, translated_key)

            await asyncio.sleep(self._screenshot_delay)
            return await self.screenshot()

        if action in ("left_click", "right_click", "double_click", "middle_click"):
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")

            # Move to coordinate if provided
            if coordinate is not None:
                x, y = self.validate_and_get_coordinates(coordinate)
                await asyncio.to_thread(pyautogui.moveTo, x, y, duration=0.2)

            # Press modifier key if provided
            if key:
                translated_key = translate_key(key)
                await asyncio.to_thread(pyautogui.keyDown, translated_key)

            # Perform click
            if action == "left_click":
                await asyncio.to_thread(pyautogui.click)
            elif action == "right_click":
                await asyncio.to_thread(pyautogui.rightClick)
            elif action == "middle_click":
                await asyncio.to_thread(pyautogui.middleClick)
            elif action == "double_click":
                await asyncio.to_thread(pyautogui.doubleClick)

            # Release modifier key
            if key:
                await asyncio.to_thread(pyautogui.keyUp, translated_key)

            await asyncio.sleep(self._screenshot_delay)
            return await self.screenshot()

        # Fall back to base implementation for other actions
        return await super().__call__(
            action=action, text=text, coordinate=coordinate, key=key, **kwargs
        )
