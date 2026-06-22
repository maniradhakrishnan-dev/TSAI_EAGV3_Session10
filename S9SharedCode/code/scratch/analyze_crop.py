import os
from PIL import Image

def main():
    path = "/home/mani_radhakrishnan/.gemini/antigravity/brain/1127d650-97f7-4389-a0d0-0c4991946c47/calc_region.png"
    if not os.path.exists(path):
        return
    img = Image.open(path)
    colors = img.getcolors(maxcolors=100000)
    print(f"Number of unique colors in Calculator region: {len(colors) if colors else '>100000'}")
    
    # Check if there are edges/contrast
    from PIL import ImageFilter
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_pixels = list(edges.getdata())
    print(f"Max edge pixel intensity: {max(edge_pixels)}")

if __name__ == "__main__":
    main()
