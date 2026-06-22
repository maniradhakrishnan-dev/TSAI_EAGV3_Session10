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
    for app in desktop:
        if app and app.name in ["gnome-calculator", "Calculator"]:
            calc_app = app
            break
            
    if not calc_app:
        print("Calculator not found!")
        return

    for name in ["Mode selection", "Angle", "⇆", "Basic Mode", "4", "7"]:
        el = find_element(calc_app, name)
        if el:
            comp = el.queryComponent()
            ext = comp.getExtents(pyatspi.XY_SCREEN)
            print(f"'{name}' bounds: {ext}")
        else:
            print(f"'{name}' not found!")

if __name__ == "__main__":
    main()
