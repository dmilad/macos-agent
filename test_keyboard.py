#!/usr/bin/env python3
"""
Test script for keyboard functionality in macOS agent.
Tests various key combinations including cmd+space (Spotlight).
"""

import asyncio
import pyautogui
import time

# Disable failsafe
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01

# Key mapping from computer_macos.py
MACOS_KEY_MAPPING = {
    "cmd": "command",
    "ctrl": "command",
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
    "Return": "enter",
    "BackSpace": "backspace",
    "space": "space",
}

def translate_key(key: str) -> str:
    """Translate X11/Linux key names to macOS/PyAutoGUI key names."""
    return MACOS_KEY_MAPPING.get(key, key.lower())


async def test_single_key(key: str):
    """Test pressing a single key."""
    print(f"\n[TEST] Single key: '{key}'")
    translated = translate_key(key)
    print(f"  Translated: '{translated}'")
    try:
        await asyncio.to_thread(pyautogui.press, translated)
        print(f"  ✓ Successfully pressed: {translated}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {str(e)}")
        return False


async def test_key_combination(text: str):
    """Test pressing a key combination (e.g., cmd+space)."""
    print(f"\n[TEST] Key combination: '{text}'")
    keys = [translate_key(k.strip()) for k in text.split("+")]
    print(f"  Translated: {' + '.join(keys)}")

    # Wait a moment for user to see what's about to happen
    print(f"  Pressing in 2 seconds...")
    await asyncio.sleep(2)

    try:
        await asyncio.to_thread(pyautogui.hotkey, *keys)
        print(f"  ✓ Successfully pressed: {' + '.join(keys)}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {str(e)}")
        return False


async def test_key_down_up(key: str, duration: float = 0.5):
    """Test holding a key for a duration."""
    print(f"\n[TEST] Hold key: '{key}' for {duration}s")
    translated = translate_key(key)
    print(f"  Translated: '{translated}'")
    try:
        await asyncio.to_thread(pyautogui.keyDown, translated)
        await asyncio.sleep(duration)
        await asyncio.to_thread(pyautogui.keyUp, translated)
        print(f"  ✓ Successfully held and released: {translated}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {str(e)}")
        return False


async def test_typing(text: str, interval: float = 0.012):
    """Test typing text with a delay between characters."""
    print(f"\n[TEST] Typing: '{text}'")
    print(f"  Interval: {interval}s per character")
    try:
        await asyncio.to_thread(pyautogui.write, text, interval=interval)
        print(f"  ✓ Successfully typed: {text}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {str(e)}")
        return False


async def diagnostic_info():
    """Print diagnostic information about PyAutoGUI and the system."""
    print("=" * 60)
    print("DIAGNOSTIC INFORMATION")
    print("=" * 60)
    print(f"PyAutoGUI version: {pyautogui.__version__}")
    print(f"Screen size: {pyautogui.size()}")
    print(f"Current mouse position: {pyautogui.position()}")
    print(f"FAILSAFE: {pyautogui.FAILSAFE}")
    print(f"PAUSE: {pyautogui.PAUSE}")

    # Test if we can detect modifier keys
    print("\nTesting key press detection:")
    test_keys = ["command", "option", "shift", "space", "a"]
    for key in test_keys:
        try:
            pyautogui.press(key)
            print(f"  ✓ '{key}' - OK")
        except Exception as e:
            print(f"  ✗ '{key}' - FAILED: {str(e)}")

    print("=" * 60)


async def main():
    """Run all keyboard tests."""
    print("\n" + "=" * 60)
    print("MACOS AGENT KEYBOARD FUNCTIONALITY TEST")
    print("=" * 60)
    print("\nThis test will verify keyboard input functionality.")
    print("\nStarting tests in 2 seconds...")
    await asyncio.sleep(2)

    # Print diagnostic info first
    await diagnostic_info()

    results = []

    # Test 1: cmd+space (Spotlight) - THE CRITICAL TEST
    print("\n" + "-" * 60)
    print("TEST 1: cmd+space (Spotlight) - CRITICAL TEST")
    print("-" * 60)
    print("\nThis will attempt to open Spotlight.")
    print("Watch for the Spotlight search bar to appear!")
    print("Testing in 2 seconds...")
    await asyncio.sleep(2)
    results.append(await test_key_combination("cmd+space"))
    await asyncio.sleep(2)

    # Close Spotlight with Escape
    print("\nClosing Spotlight with Escape...")
    await asyncio.to_thread(pyautogui.press, "escape")
    await asyncio.sleep(1)

    # Test 2: cmd+space again (to verify it's consistent)
    print("\n" + "-" * 60)
    print("TEST 2: cmd+space (Second attempt)")
    print("-" * 60)
    print("Testing again to verify consistency...")
    await asyncio.sleep(2)
    results.append(await test_key_combination("cmd+space"))
    await asyncio.sleep(2)

    # Close Spotlight again
    print("\nClosing Spotlight with Escape...")
    await asyncio.to_thread(pyautogui.press, "escape")
    await asyncio.sleep(1)

    # Test 3: Alternative method - using "command" directly
    print("\n" + "-" * 60)
    print("TEST 3: command+space (using 'command' directly)")
    print("-" * 60)
    print("Testing with explicit 'command' key...")
    await asyncio.sleep(2)
    results.append(await test_key_combination("command+space"))
    await asyncio.sleep(2)

    # Close Spotlight
    print("\nClosing Spotlight with Escape...")
    await asyncio.to_thread(pyautogui.press, "escape")
    await asyncio.sleep(1)

    # Test 4: Other common combinations
    print("\n" + "-" * 60)
    print("TEST 4: Other Key Combinations")
    print("-" * 60)

    # cmd+tab (app switcher)
    print("\nTesting cmd+tab (App Switcher)...")
    results.append(await test_key_combination("cmd+tab"))
    await asyncio.sleep(2)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    spotlight_tests = results[0:3]
    if all(spotlight_tests):
        print("\n✓✓✓ ALL cmd+space (Spotlight) tests PASSED!")
        print("Spotlight is working correctly!")
    elif any(spotlight_tests):
        print(f"\n⚠ PARTIAL: {sum(spotlight_tests)}/3 Spotlight tests passed")
        print("Spotlight is working inconsistently")
    else:
        print("\n✗✗✗ ALL cmd+space (Spotlight) tests FAILED!")
        print("\nPossible issues:")
        print("  1. PyAutoGUI may not have Accessibility permissions")
        print("  2. Check System Settings > Privacy & Security > Accessibility")
        print("  3. Make sure Python/Terminal/VSCode is allowed to control your computer")

    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nTest failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
