import os
from PIL import Image

def main():
    path = "/home/mani_radhakrishnan/.gemini/antigravity/brain/1127d650-97f7-4389-a0d0-0c4991946c47/vision_turn_01.png"
    if not os.path.exists(path):
        print("Image not found")
        return
        
    img = Image.open(path)
    # Check pixel color at (19, 399)
    p_19_399 = img.getpixel((19, 399))
    print(f"Pixel at (19, 399): {p_19_399}")
    
    # Check pixel color at key 4: (972, 367)
    p_4 = img.getpixel((972, 367))
    print(f"Pixel at (972, 367): {p_4}")

    # Let's count unique colors in the entire image
    colors = img.getcolors(maxcolors=200000)
    print(f"Total unique colors in full screenshot: {len(colors) if colors else '>200000'}")

if __name__ == "__main__":
    main()
