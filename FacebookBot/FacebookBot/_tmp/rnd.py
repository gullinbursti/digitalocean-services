# !/usr/bin/env python
# -*- coding: UTF-8 -*-


import random
import statistics
import sys

from PIL import Image, ImageDraw, ImageFont

def image_graph(amt=100, mode="uniform"):
    font = ImageFont.truetype("Consolas.ttf", 16)
    image = Image.new('RGBA', (500, 150), (256, 256, 256))
    draw = ImageDraw.Draw(image)

    #-- bounds
    draw.rectangle((1, 50, image.size[0] - 1, image.size[1] - 1), (226, 226, 226, 0), (64, 64, 64))
    draw.line((1, (image.size[1] + 50) * 0.5, image.size[0] - 1, (image.size[1] + 50) * 0.5), (64, 64, 64))

    step = (image.size[0] / amt)

    mu = 0.5 if len(sys.argv) == 2 else float(sys.argv[2])
    sigma = mu * (1 / float(3))
    # sigma = 0.05

    caption = "{mode} - mu={mu:.2f}, sigma={sigma:.2f}".format(mode=mode, mu=mu, sigma=sigma)
    title_size = draw.textsize(caption.upper(), font)
    draw.text(((image.size[0] - title_size[0]) * 0.5, 6), caption.upper(), (32, 32, 32), font)

    # -- grid
    for i in range(amt):
        draw.line((i * step, 50, i * step, 150), (192, 192, 192))

    #-- plot
    vals = []
    prev_pt = (0, image.size[1])
    for i in range(amt):
        if mode == "uniform":
            val = min(max(random.uniform(0, 1), 0), 1)
        elif mode == "triangular":
            val = min(max(random.triangular(0, 1), 0), 1)
        elif mode == "expovariate":
            val = min(max(random.expovariate(1.0 / mu), 0), 1)
        elif mode == "lognormvariate":
            val = min(max(random.lognormvariate(mu, sigma), 0), 1)
        elif mode == "gauss":
            val = min(max(random.gauss(mu, sigma), 0), 1)

        vals.append(val)

        draw.line((prev_pt[0], prev_pt[1], (i + 1) * (image.size[0] / amt), 50 + (val * 100)), (32, 32, 128), width=2)
        prev_pt = ((i + 1) * step, 50 + (val * 100))

    font = ImageFont.truetype("Consolas.ttf", 12)
    caption = "{deviated:.2f}%".format(deviated=(statistics.stdev(vals) * 100))
    subtitle_size = draw.textsize(caption, font)
    draw.text(((image.size[0] - subtitle_size[0]) * 0.5, 12 + (title_size[1])), caption, (32, 32, 32), font)


    print ("Deviation: {percent:.2f}%".format(percent=(statistics.stdev(vals) * 100)))
    image.show(mode.upper())
    return image




image_graph(mode=sys.argv[1])
