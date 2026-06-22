import asyncio
import time
from Xlib import X, display
from Xlib.ext import xtest

def test_click():
    d = display.Display()
    # Let's get current pointer position
    res = d.screen().root.query_pointer()
    orig_x, orig_y = res.root_x, res.root_y
    print(f"Original pointer position: {orig_x}, {orig_y}")

    # Let's move to (200, 200) and click
    target_x, target_y = 200, 200
    print(f"Moving to absolute coordinates ({target_x}, {target_y})")
    
    # Detail=0 means absolute coordinate
    xtest.fake_input(d, X.MotionNotify, detail=0, x=target_x, y=target_y)
    d.sync()
    time.sleep(0.5)

    # Perform click
    print("Pressing button 1")
    xtest.fake_input(d, X.ButtonPress, detail=1)
    d.sync()
    time.sleep(0.1)
    
    print("Releasing button 1")
    xtest.fake_input(d, X.ButtonRelease, detail=1)
    d.sync()
    time.sleep(0.5)

    # Restore position
    print(f"Restoring pointer position to ({orig_x}, {orig_y})")
    xtest.fake_input(d, X.MotionNotify, detail=0, x=orig_x, y=orig_y)
    d.sync()

if __name__ == "__main__":
    test_click()
