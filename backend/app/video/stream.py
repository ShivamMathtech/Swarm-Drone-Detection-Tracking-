import math
import time
import cv2
import numpy as np

class DemoSource:
    """Procedural scene; intentionally separate from measured real-camera data."""
    names = {0: "drone"}
    fps = 30.0
    def __init__(self): self.index = 0
    def read(self):
        t = self.index / self.fps; self.index += 1
        h,w=720,1280
        sky=np.linspace(48,91,h,dtype=np.uint8)[:,None]
        f=np.repeat(np.repeat(sky,w,axis=1)[:,:,None],3,axis=2)
        for layer in range(3):
            points=[(0,h)]+[(x,int(480+layer*52+35*math.sin(x/160+layer)+18*math.sin(x/51))) for x in range(0,w+20,20)]+[(w,h)]
            cv2.fillPoly(f,[np.array(points,np.int32)],(42-layer*9,)*3)
        for i in range(6):
            # Brief occlusion exercises LOST/reacquisition in the same tracker.
            if i==2 and 6 < t%12 < 6.4: continue
            x=int(190+i*165+60*math.sin(t*.24+i)); y=int(210+85*math.sin(t*.39+i*.82))
            s=12+i%3*3
            cv2.line(f,(x-s,y-5),(x+s,y+5),(210,)*3,2)
            cv2.line(f,(x-s,y+5),(x+s,y-5),(210,)*3,2)
            cv2.ellipse(f,(x,y),(5,4),0,0,360,(230,)*3,-1)
            for dx in [-s,s]: cv2.ellipse(f,(x+dx,y),(6,2),0,0,360,(225,)*3,1)
        return True,f
    def release(self): pass

class DemoDetector:
    names = DemoSource.names
    def detect(self, frame):
        mask=cv2.inRange(frame[:,:,0],150,255)
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        boxes=[]
        for cnt in contours:
            x,y,w,h=cv2.boundingRect(cnt)
            if w>=12 and h>=5: boxes.append([x,y,x+w,y+h,1.0,0])
        return np.asarray(boxes,dtype=np.float32).reshape(-1,6)

class VideoSource:
    def __init__(self, source, kind):
        self.kind=kind
        if kind == "rtsp":
            self.cap=cv2.VideoCapture(source, cv2.CAP_FFMPEG,
                [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,5000,cv2.CAP_PROP_READ_TIMEOUT_MSEC,5000])
        else: self.cap=cv2.VideoCapture(source)
        if not self.cap.isOpened():
            self.cap.release()
            raise ValueError("CAMERA ERROR: unable to open source; check device, file codec or RTSP environment alias")
        fps=self.cap.get(cv2.CAP_PROP_FPS)
        self.fps=fps if math.isfinite(fps) and 1<=fps<=240 else 30.0
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
    def read(self): return self.cap.read()
    def release(self): self.cap.release()


class LatestLiveSource:
    """Continuously drain live capture; inference consumes only the newest frame."""
    def __init__(self, source, kind):
        import threading
        self.source=VideoSource(source,kind);self.fps=self.source.fps
        self.condition=threading.Condition();self.stop=threading.Event()
        self.latest=None;self.sequence=0;self.consumed=0;self.failed=False
        self.thread=threading.Thread(target=self._read_loop,daemon=True);self.thread.start()
    def _read_loop(self):
        try:
            while not self.stop.is_set():
                ok,frame=self.source.read()
                with self.condition:
                    if not ok: self.failed=True;self.condition.notify_all();break
                    self.latest=frame;self.sequence+=1;self.condition.notify_all()
        finally: self.source.release()
    def read(self):
        with self.condition:
            self.condition.wait_for(lambda:self.sequence!=self.consumed or self.failed or self.stop.is_set(),timeout=7)
            if self.sequence==self.consumed:return False,None
            self.consumed=self.sequence
            return True,self.latest
    def release(self):
        self.stop.set()
        with self.condition:self.condition.notify_all()
        self.thread.join(timeout=.5)
