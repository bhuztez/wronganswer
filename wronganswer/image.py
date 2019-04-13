from shutil import get_terminal_size
from PIL import Image, ImageFile

def fit(im, size=None):
    w, h = size or get_terminal_size()
    h *= 2
    x, y = im.size
    if w * y > x * h:
      size = x * h // y, h
    else:
      size = w, y * w // x
    return im.resize(size, Image.HAMMING)


def display(data):
    p = ImageFile.Parser()
    p.feed(data)
    im = fit(p.close(), get_terminal_size())
    w, h = im.size

    for y in range(0,h,2):
        for x in range(w):
            r,g,b = im.getpixel((x,y))
            print(f"\x1b[38;2;{r};{g};{b}m", end="")
            if y+1 < h:
                r,g,b = im.getpixel((x,y+1))
                print(f"\x1b[48;2;{r};{g};{b}m", end="")
            print("\u2580", end="")
        print("\x1b[39m\x1b[49m")
