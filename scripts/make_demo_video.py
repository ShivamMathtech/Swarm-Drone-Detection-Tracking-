import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import cv2
from app.video.stream import DemoSource

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='samples/synthetic-swarm.avi');p.add_argument('--seconds',type=int,default=12);a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    writer=cv2.VideoWriter(str(out),cv2.VideoWriter_fourcc(*'MJPG'),30,(1280,720))
    if not writer.isOpened():raise RuntimeError('MJPEG encoder unavailable')
    source=DemoSource()
    for _ in range(a.seconds*30):
        frame=source.read()[1]
        cv2.putText(frame,'SYNTHETIC TEST VIDEO - NOT CAMERA FOOTAGE',(24,680),cv2.FONT_HERSHEY_SIMPLEX,.65,(160,160,160),1)
        writer.write(frame)
    writer.release();print(out)
if __name__=='__main__':main()
