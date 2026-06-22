import pyatspi
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
    reg = pyatspi.Registry
    desktop = reg.getDesktop(0)
    calc_app = None
    
    # List all apps first
    print("Applications found in AT-SPI:")
    for app in desktop:
        if app:
            print(f"- {app.name}")
            if app.name in ["gnome-calculator", "Calculator"]:
                calc_app = app

    if not calc_app:
        print("Calculator application not found!")
        return

    print(f"\nFound Calculator: {calc_app.name}")
    
    # Find "Mode selection"
    mode_sel = find_element(calc_app, "Mode selection")
    if mode_sel:
        comp = mode_sel.queryComponent()
        ext = comp.getExtents(pyatspi.XY_SCREEN)
        print(f"Mode selection bounds: {ext}")
    else:
        print("Mode selection element not found!")

    # Find "Basic Mode"
    basic_mode = find_element(calc_app, "Basic Mode")
    if basic_mode:
        comp = basic_mode.queryComponent()
        ext = comp.getExtents(pyatspi.XY_SCREEN)
        print(f"Basic Mode bounds: {ext}")
    else:
        print("Basic Mode element not found!")

if __name__ == "__main__":
    main()
