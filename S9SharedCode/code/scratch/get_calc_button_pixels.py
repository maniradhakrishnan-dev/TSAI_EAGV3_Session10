#!/usr/bin/env python3
import pyatspi
import sys
import os
import subprocess
import json
import time

def find_element(element, name):
    if not element:
        return None
    try:
        el_name = element.name
    except Exception:
        el_name = ""
    if el_name == name:
        return element
    try:
        child_count = element.childCount
    except Exception:
        child_count = 0
    for i in range(child_count):
        try:
            child = element.getChildAtIndex(i)
            res = find_element(child, name)
            if res:
                return res
        except Exception:
            continue
    return None

def main():
    # Make sure calculator is open
    subprocess.run(["killall", "gnome-calculator"], capture_output=True)
    time.sleep(0.5)
    subprocess.Popen(["gnome-calculator"])
    time.sleep(2.0)
    
    # Ensure it's in Basic Mode
    subprocess.run(["python3", "computer/switch_calc_mode.py"], capture_output=True)
    time.sleep(0.5)

    reg = pyatspi.Registry
    desktop = reg.getDesktop(0)
    calc_app = None
    for app in desktop:
        if app and app.name in ["gnome-calculator", "Calculator"]:
            calc_app = app
            break
            
    if not calc_app:
        print("Calculator not found!")
        sys.exit(1)

    for btn_name in ["7", "8", "×", "="]:
        btn = find_element(calc_app, btn_name)
        if btn:
            comp = btn.queryComponent()
            ext = comp.getExtents(pyatspi.XY_SCREEN)
            cx = ext.x + ext.width // 2
            cy = ext.y + ext.height // 2
            print(f"Button '{btn_name}': center=({cx}, {cy}), bounds=({ext.x}, {ext.y}, {ext.width}, {ext.height})")
        else:
            print(f"Button '{btn_name}' not found!")

    subprocess.run(["killall", "gnome-calculator"], capture_output=True)

if __name__ == "__main__":
    main()
