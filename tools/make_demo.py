"""Code-drawn software smoke-test input, NOT factory accuracy evidence."""
from pathlib import Path
import cv2
import numpy as np

root = Path(__file__).resolve().parents[1]
folder = root/'artifacts'
folder.mkdir(exist_ok=True)
frame = np.full((720,1280,3),(205,212,217),np.uint8)
for y in range(0,480,80):
    cv2.line(frame,(0,y),(1280,y),(160,170,180),2)
for x in range(0,1280,160):
    cv2.line(frame,(x,0),(x,480),(160,170,180),2)
cv2.rectangle(frame,(0,480),(1280,720),(165,172,180),-1)
cv2.putText(frame,'SOFTWARE DEMO - NOT FACTORY DATA',(32,52),cv2.FONT_HERSHEY_SIMPLEX,.8,(50,65,80),2)
cv2.rectangle(frame,(230,545),(1070,560),(55,62,70),-1)
for x in (280,1000):
    cv2.circle(frame,(x,580),24,(40,45,50),-1)
for i in range(8):
    x = 260+i*95
    y = 190+((i%2)*35)
    for dx in range(70):
        value = int(150+90*np.sin(np.pi*dx/70))
        cv2.line(frame,(x+dx,y+12),(x+dx,540),(value,value,value),1)
    cv2.ellipse(frame,(x+35,y+12),(35,14),0,0,360,(225,228,230),-1)
    cv2.ellipse(frame,(x+35,y+12),(10,6),0,0,360,(75,80,85),-1)
    cv2.ellipse(frame,(x+35,540),(35,14),0,0,180,(150,155,160),2)
cv2.imwrite(str(folder/'demo.png'),frame)
out = cv2.VideoWriter(str(folder/'demo.avi'),cv2.VideoWriter_fourcc(*'MJPG'),20,(1280,720))
for _ in range(400):
    out.write(frame)
out.release()
print(folder/'demo.png')
