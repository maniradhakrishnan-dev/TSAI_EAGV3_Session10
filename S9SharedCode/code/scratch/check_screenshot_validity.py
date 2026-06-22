import os
from PIL import Image

def main():
    session_dir = "state/sessions/s8-54b84f0c/computer"
    path = os.path.join(session_dir, "vision_turn_01.png")
    if not os.path.exists(path):
        print(f"File {path} does not exist!")
        return

    img = Image.open(path)
    print(f"Image mode: {img.mode}, size: {img.size}")
    
    # Calculate pixel stats
    pixels = img.convert("L").getdata()
    min_val = min(pixels)
    max_val = max(pixels)
    avg_val = sum(pixels) / len(pixels)
    print(f"Grayscale stats: min={min_val}, max={max_val}, avg={avg_val:.2f}")
    
    # Copy to artifacts directory
    target = "/home/mani_radhakrishnan/.gemini/antigravity/brain/1127d650-97f7-4389-a0d0-0c4991946c47/vision_turn_01.png"
    import shutil
    shutil.copy(path, target)
    print(f"Copied to {target}")

if __name__ == "__main__":
    main()
