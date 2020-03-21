from PIL import Image
import glob

cards = glob.glob("*.png")
percent = 0.5

for filename in cards:
    img = Image.open( filename )
    out = img.resize( [int(percent * s) for s in img.size] )
    out.save("small/{}".format(filename))


