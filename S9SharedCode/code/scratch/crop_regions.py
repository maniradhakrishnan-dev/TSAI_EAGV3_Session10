import os
from PIL import Image

def main():
    path = "/home/mani_radhakrishnan/.gemini/antigravity/brain/1127d650-97f7-4389-a0d0-0c4991946c47/vision_turn_01.png"
    if not os.path.exists(path):
        print("Screenshot not found in artifacts!")
        return

    img = Image.open(path)
    # Calculator coordinates from previous list_windows: x=934, y=73, w=402, h=446
    # Let's crop it with some padding: x: 900..1360, y: 50..550
    crop_area = (900, 50, 1360, 550)
    cropped = img.crop(crop_area)
    target = "/home/mani_radhakrishnan/.gemini/antigravity/brain/1127d650-97f7-4389-a0d0-0c4991946c47/calc_region.png"
    cropped.save(target)
    print(f"Calculator region crop saved to {target}")

    # Let's also check if there is any window in the left area (0..800)
    crop_left = (0, 0, 900, 1080)
    cropped_left = img.crop(crop_left)
    target_left = "/home/mani_radhakrishnan/.gemini/antigravity/brain/1127d650-97f7-4389-a0d0-0c4991946c47/left_region.png"
    cropped_left.save(target_left)
    print(f"Left region crop saved to {target_left}")

if __name__ == "__main__":
    main()
