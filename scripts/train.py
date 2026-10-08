import argparse
from pathlib import Path
from ultralytics import YOLO
from dataset_utils import validate,resolved_yaml

def main():
    p=argparse.ArgumentParser(description='Train a configurable drone detector on validated YOLO labels')
    p.add_argument('--data',default='dataset/data.yaml');p.add_argument('--model',default='yolov8n.pt')
    p.add_argument('--epochs',type=int,default=100);p.add_argument('--imgsz',type=int,default=640)
    p.add_argument('--batch',type=int,default=8);p.add_argument('--device',default='cpu')
    p.add_argument('--workers',type=int,default=0);p.add_argument('--seed',type=int,default=42)
    p.add_argument('--project',default='runs/train');p.add_argument('--name',default='drone')
    a=p.parse_args();_,summary=validate(a.data);print(summary)
    data=resolved_yaml(a.data,Path(a.project)/'resolved-data.yaml')
    YOLO(a.model).train(data=data,epochs=a.epochs,imgsz=a.imgsz,batch=a.batch,device=a.device,
        workers=a.workers,seed=a.seed,deterministic=True,project=a.project,name=a.name)
    print('Copy the resulting weights/best.pt to weights/drone_detector.pt. Validate on held-out flights before use.')
if __name__=='__main__':main()
