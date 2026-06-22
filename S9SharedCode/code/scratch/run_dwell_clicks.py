import time
from Xlib import X, display
from Xlib.ext import xtest

def xclick_with_dwell(screen_x, screen_y):
    d = display.Display()
    # Move
    print(f"Moving cursor to ({screen_x}, {screen_y})...")
    xtest.fake_input(d, X.MotionNotify, detail=0, x=screen_x, y=screen_y)
    d.sync()
    time.sleep(2.0) # DWELL
    
    # Click
    print("Pressing mouse button...")
    xtest.fake_input(d, X.ButtonPress, detail=1)
    d.sync()
    time.sleep(0.1)
    xtest.fake_input(d, X.ButtonRelease, detail=1)
    d.sync()
    time.sleep(1.0)

def main():
    # 1. Click Mode selection (1071, 119)
    xclick_with_dwell(1071, 119)

    # 2. Click Basic Mode (1071, 180)
    xclick_with_dwell(1071, 180)
    print("Dwell clicks completed.")

if __name__ == "__main__":
    main()
