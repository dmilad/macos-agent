#!/usr/bin/env python3
"""
Debug script to test screenshot permissions and capture on macOS.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

import pyautogui
from PIL import Image

# Test different screenshot methods
def test_pyautogui_screenshot():
    """Test PyAutoGUI screenshot."""
    print("\n" + "="*60)
    print("Test 1: PyAutoGUI Screenshot")
    print("="*60)

    screen_size = pyautogui.size()
    print(f"Reported screen size: {screen_size.width}x{screen_size.height}")

    screenshot = pyautogui.screenshot()
    print(f"Actual screenshot size: {screenshot.size[0]}x{screenshot.size[1]}")

    # Check pixel diversity (if all pixels are the same, probably permission issue)
    pixels = list(screenshot.getdata())
    unique_colors = len(set(pixels[:1000]))  # Sample first 1000 pixels
    print(f"Unique colors in first 1000 pixels: {unique_colors}")

    if unique_colors < 10:
        print("⚠️  WARNING: Very low color diversity - might be permission issue!")

    # Save
    output_dir = Path("/tmp/screenshot_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"debug_pyautogui_{timestamp}.png"
    screenshot.save(path)
    print(f"Saved to: {path}")

    return screenshot


def test_pil_screenshot():
    """Test PIL ImageGrab (alternative method)."""
    print("\n" + "="*60)
    print("Test 2: PIL ImageGrab Screenshot")
    print("="*60)

    try:
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        print(f"Screenshot size: {screenshot.size[0]}x{screenshot.size[1]}")

        # Check pixel diversity
        pixels = list(screenshot.getdata())
        unique_colors = len(set(pixels[:1000]))
        print(f"Unique colors in first 1000 pixels: {unique_colors}")

        if unique_colors < 10:
            print("⚠️  WARNING: Very low color diversity - might be permission issue!")

        # Save
        output_dir = Path("/tmp/screenshot_tests")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"debug_pil_{timestamp}.png"
        screenshot.save(path)
        print(f"Saved to: {path}")

        return screenshot
    except Exception as e:
        print(f"❌ PIL ImageGrab failed: {e}")
        return None


def check_permissions():
    """Check macOS permissions."""
    print("\n" + "="*60)
    print("Checking macOS Permissions")
    print("="*60)

    print("\nFor screenshots to capture windows (not just desktop background),")
    print("this application needs Screen Recording permission.")
    print("\nTo grant permission:")
    print("1. Open System Settings (System Preferences)")
    print("2. Go to 'Privacy & Security'")
    print("3. Click 'Screen Recording' (or 'Screen & System Audio Recording')")
    print("4. Add and enable:")
    print(f"   - Terminal (if running from terminal)")
    print(f"   - Python (if running directly)")
    print(f"   - Your IDE (if running from IDE)")
    print(f"   - Current: {sys.executable}")
    print("\n5. You may need to restart the application after granting permission")


def test_region_screenshot():
    """Test screenshot of a specific region."""
    print("\n" + "="*60)
    print("Test 3: Region Screenshot (top-left 500x500)")
    print("="*60)

    try:
        screenshot = pyautogui.screenshot(region=(0, 0, 500, 500))
        print(f"Screenshot size: {screenshot.size[0]}x{screenshot.size[1]}")

        # Save
        output_dir = Path("/tmp/screenshot_tests")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"debug_region_{timestamp}.png"
        screenshot.save(path)
        print(f"Saved to: {path}")

    except Exception as e:
        print(f"❌ Region screenshot failed: {e}")


def main():
    """Run all diagnostic tests."""
    print("\n" + "#"*60)
    print("# macOS Screenshot Permission Diagnostic")
    print("#"*60)

    # Run tests
    test_pyautogui_screenshot()
    test_pil_screenshot()
    test_region_screenshot()
    check_permissions()

    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("All test screenshots saved to: /tmp/screenshot_tests/")
    print("\nOpen the screenshots and check if they show:")
    print("  ✓ Active windows and content")
    print("  ✗ Only desktop background (permission issue)")
    print("\nIf only showing desktop background, grant Screen Recording permission.")


if __name__ == "__main__":
    main()
