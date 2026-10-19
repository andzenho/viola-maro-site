"""Снимает нарисованную «шахматку прозрачности» с картинки (так присылают
картинки из генераторов) и делает настоящий прозрачный фон.

    python3 build-assets/glavnaya/ubrat-kletku.py исходник.webp build-assets/glavnaya/planshet.png

Фон ищется как серая клетка с периодом ~9 px, связанная с краем кадра."""
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
im=Image.open(__import__('sys').argv[1]).convert('RGB'); a=np.asarray(im).astype(np.float32)
L=a.mean(2); h,w=L.shape
neutral=(a.max(2)-a.min(2))<14
def sh(x,dy,dx):
    return np.roll(np.roll(x,dy,0),dx,1)
def per(axis):
    best=np.zeros_like(L,bool)
    for half in (4,5):
        for full in (9,10):
            if axis==1: d1=np.abs(L-sh(L,0,-half)); d2=np.abs(L-sh(L,0,-full))
            else: d1=np.abs(L-sh(L,-half,0)); d2=np.abs(L-sh(L,-full,0))
            best|=(d1>22)&(d2<d1*0.5)
    return best
cand=neutral&(per(1)|per(0))
def box(x,r):
    p=np.pad(x,r+1,mode='edge'); c=p.cumsum(0).cumsum(1); k=2*r+1
    s=c[k:k+h,k:k+w]-c[0:h,k:k+w]-c[k:k+h,0:w]+c[0:h,0:w]; return s/(k*k)
dens=box(cand.astype(np.float32),5)
bgc=(dens>0.35)&neutral
bgc=box(bgc.astype(np.float32),2)>0.5
mk=Image.fromarray((bgc*255).astype(np.uint8)).copy()
for s in [(x,0) for x in range(0,w,5)]+[(x,h-1) for x in range(0,w,5)]+[(0,y) for y in range(0,h,5)]+[(w-1,y) for y in range(0,h,5)]:
    if mk.getpixel(s)==255: ImageDraw.floodfill(mk,s,128)
bg=np.asarray(mk)==128
# fill small holes of bg near edges: dilate bg 2 within neutral
bgd=(box(bg.astype(np.float32),2)>0.3)&neutral
bg=bg|bgd
print('bg', bg.mean())
al=Image.fromarray(((~bg)*255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(0.7))
out=im.convert('RGBA'); out.putalpha(al); out.save(__import__('sys').argv[2])
