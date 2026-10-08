import argparse
import csv
import json
from pathlib import Path
from ultralytics import YOLO
from dataset_utils import validate,resolved_yaml

def main():
    p=argparse.ArgumentParser(description='Export real held-out YOLO metrics; no synthetic accuracy estimates')
    p.add_argument('--data',default='dataset/data.yaml');p.add_argument('--model',required=True)
    p.add_argument('--split',choices=['val','test'],default='test');p.add_argument('--imgsz',type=int,default=1280)
    p.add_argument('--device',default='cpu');p.add_argument('--output',default='reports/evaluation')
    a=p.parse_args();validate(a.data,(a.split,));out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    data=resolved_yaml(a.data,out.parent/'resolved-data.yaml')
    result=YOLO(a.model).val(data=data,split=a.split,imgsz=a.imgsz,device=a.device,plots=True,project=str(out.parent),name='validation')
    report={'schema_version':1,'model':str(Path(a.model).resolve()),'dataset':str(Path(a.data).resolve()),'split':a.split,
        'precision':float(result.box.mp),'recall':float(result.box.mr),'map50':float(result.box.map50),'map50_95':float(result.box.map)}
    out.with_suffix('.json').write_text(json.dumps(report,indent=2))
    with out.with_suffix('.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=report);writer.writeheader();writer.writerow(report)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
