"""Frame-level, class-aware MOT association; reports exact protocol alongside results."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment

def iou(a,b):
    x1,y1=max(a[0],b[0]),max(a[1],b[1]);x2,y2=min(a[2],b[2]),min(a[3],b[3])
    inter=max(0,x2-x1)*max(0,y2-y1)
    union=max(0,a[2]-a[0])*max(0,a[3]-a[1])+max(0,b[2]-b[0])*max(0,b[3]-b[1])-inter
    return inter/union if union else 0

def load(path):
    frames=defaultdict(list)
    with open(path,newline='') as f:
        for r in csv.DictReader(f):
            frame=int(r.get('source_frame') or r['frame_id']);tid=int(r['track_id'])
            box=[float(r[k]) for k in ['x1','y1','x2','y2']]
            if not np.isfinite(box).all() or box[2]<=box[0] or box[3]<=box[1]: raise ValueError('Invalid box')
            if any(x[0]==tid for x in frames[frame]):raise ValueError('Duplicate track ID in frame; evaluate one session at a time')
            frames[frame].append((tid,box,r.get('class_name','drone')))
    return frames

def evaluate(gt,pred,threshold=.5):
    last={};total=0;matches=0;fp=0;misses=0;switches=0;counts=defaultdict(lambda:[0,0])
    for frame in sorted(set(gt)|set(pred)):
        g,p=gt.get(frame,[]),pred.get(frame,[]);total+=len(g)
        for gid,_,_ in g: counts[gid][1]+=1
        costs=np.ones((len(g),len(p))) * 1e6
        for i,(_,b,c) in enumerate(g):
            for j,(_,b2,c2) in enumerate(p):
                overlap=iou(b,b2)
                if c==c2 and overlap>=threshold:costs[i,j]=1-overlap
        rows,cols=linear_sum_assignment(costs);valid=[(i,j) for i,j in zip(rows,cols) if costs[i,j]<1e6]
        matches+=len(valid);fp+=len(p)-len(valid);misses+=len(g)-len(valid)
        for i,j in valid:
            gid,pid=g[i][0],p[j][0];counts[gid][0]+=1
            if gid in last and last[gid]!=pid:switches+=1
            last[gid]=pid
    return {'iou_threshold':threshold,'gt_observations':total,'matched':matches,'false_positives':fp,
        'misses':misses,'id_switches':switches,'detection_precision':matches/(matches+fp) if matches+fp else None,
        'detection_recall':matches/total if total else None,
        'track_coverage':{str(k):a/b for k,(a,b) in counts.items()},
        'protocol':'Class-aware frame Hungarian IoU association; ID switch relative to last matched ID, including gaps. Not HOTA or IDF1.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--gt',required=True);p.add_argument('--pred',required=True)
    p.add_argument('--iou',type=float,default=.5);p.add_argument('--output',default='reports/tracking.json');a=p.parse_args()
    r=evaluate(load(a.gt),load(a.pred),a.iou);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
if __name__=='__main__':main()
