#!/usr/bin/env python3
"""Tests for the mouse-debounce filter's button state, with no real devices.

Run: python3 tools/mouse-debounce/test_mouse_debounce.py
Works without python3-evdev installed, by faking the few codes it needs.
"""
import importlib.machinery
import importlib.util
import os
import sys
import types
import unittest
from collections import namedtuple

try:
    import evdev  # noqa: F401
except ImportError:
    fake_ecodes = types.SimpleNamespace(
        EV_SYN=0, EV_KEY=1, EV_REL=2, SYN_REPORT=0, SYN_DROPPED=3,
        REL_X=0, REL_Y=1, BTN_LEFT=272, BTN_RIGHT=273)
    sys.modules["evdev"] = types.SimpleNamespace(ecodes=fake_ecodes)
    sys.modules["evdev.ecodes"] = fake_ecodes

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "mouse-debounce")
loader = importlib.machinery.SourceFileLoader("mouse_debounce", SCRIPT)
spec = importlib.util.spec_from_loader("mouse_debounce", loader)
mouse_debounce = importlib.util.module_from_spec(spec)
loader.exec_module(mouse_debounce)
ecodes = mouse_debounce.ecodes

Event = namedtuple("Event", "type code value")
LEFT = ecodes.BTN_LEFT
RIGHT = ecodes.BTN_RIGHT


class FakeVirtualMouse:
    """Records what reaches GNOME, deduplicated the way the kernel does."""

    def __init__(self):
        self.keys_down = set()
        self.key_events = []

    def write(self, event_type, code, value):
        self.write_event(Event(event_type, code, value))

    def write_event(self, event):
        if event.type != ecodes.EV_KEY:
            return
        if (event.code in self.keys_down) == bool(event.value):
            return  # the input core drops a key event that changes nothing
        self.key_events.append((event.code, event.value))
        if event.value:
            self.keys_down.add(event.code)
        else:
            self.keys_down.discard(event.code)

    def syn(self):
        pass


SETTINGS = {
    "hold_seconds": 0.150,
    "click_hold_seconds": 0,
    "drag_distance": 10,
    "long_hold_seconds": 0.300,
    "log": False,
}


def key(code, value):
    return Event(ecodes.EV_KEY, code, value)


def move(distance):
    return Event(ecodes.EV_REL, ecodes.REL_X, distance)


SYN = Event(ecodes.EV_SYN, ecodes.SYN_REPORT, 0)
DROPPED = Event(ecodes.EV_SYN, ecodes.SYN_DROPPED, 0)


class DebouncerTest(unittest.TestCase):
    def setUp(self):
        self.virtual = FakeVirtualMouse()
        self.debouncer = mouse_debounce.Debouncer(self.virtual, SETTINGS)

    def feed(self, now, *events):
        resync_needed = False
        for event in events:
            resync_needed |= self.debouncer.handle(event, now)
        return resync_needed

    def test_click_passes_at_once(self):
        self.feed(0.0, key(LEFT, 1), SYN)
        self.feed(0.08, key(LEFT, 0), SYN)
        self.assertEqual(self.virtual.key_events, [(LEFT, 1), (LEFT, 0)])

    def test_chatter_in_a_drag_is_hidden(self):
        self.feed(0.0, key(LEFT, 1), SYN, move(30), SYN)
        self.feed(0.5, key(LEFT, 0), SYN)
        self.feed(0.55, key(LEFT, 1), SYN)
        self.feed(1.0, key(LEFT, 0), SYN)
        self.debouncer.flush_expired_releases(1.1)
        self.assertEqual(self.virtual.key_events, [(LEFT, 1)])
        self.debouncer.flush_expired_releases(1.2)
        self.assertEqual(self.virtual.key_events, [(LEFT, 1), (LEFT, 0)])

    def test_resync_releases_a_stuck_button(self):
        self.feed(0.0, key(LEFT, 1), SYN)  # the release was lost
        self.debouncer.resync([], 2.0)
        self.assertEqual(self.virtual.keys_down, set())
        self.feed(3.0, key(LEFT, 1), SYN)
        self.feed(3.1, key(LEFT, 0), SYN)
        self.assertEqual(self.virtual.key_events[-2:],
                         [(LEFT, 1), (LEFT, 0)])

    def test_resync_leaves_a_held_back_release_alone(self):
        self.feed(0.0, key(LEFT, 1), SYN, move(30), SYN)
        self.feed(0.5, key(LEFT, 0), SYN)
        self.debouncer.resync([], 0.55)
        self.assertEqual(self.virtual.keys_down, {LEFT})
        self.debouncer.flush_expired_releases(0.66)
        self.assertEqual(self.virtual.keys_down, set())

    def test_resync_presses_a_button_the_virtual_mouse_missed(self):
        self.debouncer.resync([LEFT], 0.0)
        self.assertEqual(self.virtual.keys_down, {LEFT})
        self.feed(0.1, key(LEFT, 0), SYN)
        self.assertEqual(self.virtual.keys_down, set())

    def test_dropped_events_are_skipped_and_ask_for_a_resync(self):
        self.feed(0.0, key(LEFT, 1), SYN)
        self.assertFalse(self.feed(0.1, DROPPED, key(LEFT, 0)))
        self.assertEqual(self.virtual.keys_down, {LEFT})
        self.assertTrue(self.feed(0.1, SYN))
        self.debouncer.resync([], 0.1)
        self.assertEqual(self.virtual.keys_down, set())

    def test_other_buttons_are_tracked_too(self):
        self.feed(0.0, key(RIGHT, 1), SYN)
        self.debouncer.resync([], 1.0)
        self.assertEqual(self.virtual.keys_down, set())

    def test_release_all_lets_go_of_everything(self):
        self.feed(0.0, key(LEFT, 1), key(RIGHT, 1), SYN, move(30), SYN)
        self.feed(0.5, key(LEFT, 0), SYN)  # held back
        self.debouncer.release_all()
        self.assertEqual(self.virtual.keys_down, set())
        self.assertIsNone(self.debouncer.next_deadline())


if __name__ == "__main__":
    unittest.main()
