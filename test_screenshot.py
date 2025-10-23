#!/usr/bin/env python3
"""
Test script for debugging screenshot functionality.
This script captures screenshots and displays detailed information about the capture.
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime

import pyautogui
from PIL import Image

# Import the computer tool
import sys
sys.path.insert(0, str(Path(__file__).parent))
from computer_use_demo.tools.computer_macos import ComputerToolMacOS20241022, ComputerToolMacOS20250124


async def test_screenshot_basic():
    """Test basic PyAutoGUI screenshot functionality."""
    print("\n" + "="*60)
    print("Testing PyAutoGUI Screenshot (No Scaling)")
    print("="*60)

    # Get actual screen size
    screen_size = pyautogui.size()
    print(f"Screen size detected: {screen_size.width}x{screen_size.height}")

    # Take screenshot
    screenshot = pyautogui.screenshot()
    print(f"Screenshot size: {screenshot.size[0]}x{screenshot.size[1]}")

    # Save to test outputs
    output_dir = Path("/tmp/screenshot_tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"pyautogui_raw_{timestamp}.png"
    screenshot.save(path)
    print(f"Saved to: {path}")

    # Check if sizes match
    if screenshot.size[0] == screen_size.width and screenshot.size[1] == screen_size.height:
        print("✓ Screenshot matches screen size")
    else:
        print(f"✗ SIZE MISMATCH! Expected {screen_size.width}x{screen_size.height}, got {screenshot.size[0]}x{screenshot.size[1]}")

    return screenshot


async def test_computer_tool_screenshot(tool_class, tool_name):
    """Test screenshot using the ComputerTool implementation."""
    print("\n" + "="*60)
    print(f"Testing {tool_name}")
    print("="*60)

    # Create tool instance
    tool = tool_class()

    print(f"Tool dimensions: {tool.width}x{tool.height}")
    print(f"Scaling enabled: {tool._scaling_enabled}")
    print(f"Tool options: {tool.options}")

    # Take screenshot
    result = await tool.screenshot()

    # Save the base64 image
    import base64
    from io import BytesIO

    img_data = base64.b64decode(result.base64_image)
    img = Image.open(BytesIO(img_data))

    print(f"Screenshot size: {img.size[0]}x{img.size[1]}")

    output_dir = Path("/tmp/screenshot_tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{tool_name.lower().replace(' ', '_')}_{timestamp}.png"
    img.save(path)
    print(f"Saved to: {path}")

    # Check scaling
    screen_size = pyautogui.size()
    if img.size[0] != screen_size.width or img.size[1] != screen_size.height:
        print(f"ℹ Screenshot was scaled from {screen_size.width}x{screen_size.height} to {img.size[0]}x{img.size[1]}")
        scaling_factor = img.size[0] / screen_size.width
        print(f"  Scaling factor: {scaling_factor:.2f}x")
    else:
        print("✓ Screenshot matches screen size (no scaling)")

    return img


async def test_with_scaling_disabled(tool_class, tool_name):
    """Test screenshot with scaling disabled."""
    print("\n" + "="*60)
    print(f"Testing {tool_name} (Scaling Disabled)")
    print("="*60)

    # Create tool instance and disable scaling
    tool = tool_class()
    tool._scaling_enabled = False

    print(f"Tool dimensions: {tool.width}x{tool.height}")
    print(f"Scaling enabled: {tool._scaling_enabled}")
    print(f"Tool options: {tool.options}")

    # Take screenshot
    result = await tool.screenshot()

    # Save the base64 image
    import base64
    from io import BytesIO

    img_data = base64.b64decode(result.base64_image)
    img = Image.open(BytesIO(img_data))

    print(f"Screenshot size: {img.size[0]}x{img.size[1]}")

    output_dir = Path("/tmp/screenshot_tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{tool_name.lower().replace(' ', '_')}_no_scaling_{timestamp}.png"
    img.save(path)
    print(f"Saved to: {path}")

    # Check if full screen captured
    screen_size = pyautogui.size()
    if img.size[0] == screen_size.width and img.size[1] == screen_size.height:
        print("✓ Screenshot matches screen size - full screen captured")
    else:
        print(f"✗ SIZE MISMATCH! Expected {screen_size.width}x{screen_size.height}, got {img.size[0]}x{img.size[1]}")

    return img


async def test_environment_variables():
    """Test screenshot with custom environment variables."""
    print("\n" + "="*60)
    print("Testing with Custom Environment Variables")
    print("="*60)

    screen_size = pyautogui.size()

    # Set custom dimensions
    os.environ["WIDTH"] = str(screen_size.width)
    os.environ["HEIGHT"] = str(screen_size.height)

    print(f"Set WIDTH={os.environ['WIDTH']}, HEIGHT={os.environ['HEIGHT']}")

    tool = ComputerToolMacOS20241022()
    print(f"Tool dimensions: {tool.width}x{tool.height}")

    # Clean up
    del os.environ["WIDTH"]
    del os.environ["HEIGHT"]


async def main():
    """Run all screenshot tests."""
    print("\n" + "#"*60)
    print("# macOS Screenshot Functionality Test")
    print("#"*60)

    try:
        # Test 1: Basic PyAutoGUI screenshot
        await test_screenshot_basic()

        # Test 2: Environment variables
        await test_environment_variables()

        # Test 3: ComputerTool with default settings
        await test_computer_tool_screenshot(ComputerToolMacOS20241022, "ComputerTool 20241022")

        # Test 4: ComputerTool with scaling disabled
        await test_with_scaling_disabled(ComputerToolMacOS20241022, "ComputerTool 20241022")

        # Test 5: Newer version
        await test_computer_tool_screenshot(ComputerToolMacOS20250124, "ComputerTool 20250124")

        # Test 6: Newer version with scaling disabled
        await test_with_scaling_disabled(ComputerToolMacOS20250124, "ComputerTool 20250124")

        print("\n" + "="*60)
        print("Summary")
        print("="*60)
        print("All screenshots saved to: /tmp/screenshot_tests/")
        print("\nTo view the screenshots:")
        print("  open /tmp/screenshot_tests/")
        print("\nCompare the images to see if any content is missing.")
        print("Check the dimensions printed above to identify scaling issues.")

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
