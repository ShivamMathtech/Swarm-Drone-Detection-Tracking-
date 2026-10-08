import json
import struct
import numpy as np
import pytest
from app.config import Config
from app.detection.yolo_detector import parse_boxes
from app.tracking.tracker import DetectionBatch,MultiTracker,TrackHistory
from app.video.stream import DemoSource,DemoDetector
from app.video.pipeline import pack_frame
from app.analytics.metrics import summarize
from evaluate_tracking import evaluate

def test_box_parser():
    rows=np.array([[-2,-3,100,80,.9,0],[4,3,1,5,.8,0],[0,0,2,2,np.nan,0]])
    a=parse_boxes(rows,50,50);assert a.shape==(1,6);np.testing.assert_allclose(a[0],[0,0,50,50,.9,0])
    assert parse_boxes([],50,50).shape==(0,6)

def test_xywh():
    d=DetectionBatch([[10,20,30,60,.9,1]])
    np.testing.assert_allclose(d.xywh,[[20,40,20,40]])
    assert len(d[d.conf>.95])==0

@pytest.mark.parametrize('algorithm',['bytetrack','botsort'])
def test_real_tracker_association(algorithm):
    tracker=MultiTracker(Config(tracker=algorithm));frame=np.zeros((200,300,3),np.uint8)
    a=tracker.update([[20,20,50,50,.95,0],[150,20,180,50,.9,0]],frame)
    assert len(a)==2
    b=tracker.update([[22,20,52,50,.95,0],[152,20,182,50,.9,0]],frame)
    assert [x['track_id'] for x in a]==[x['track_id'] for x in b]
    tracker.update([],frame)
    c=tracker.update([[24,20,54,50,.95,0],[154,20,184,50,.9,0]],frame)
    assert [x['track_id'] for x in a]==[x['track_id'] for x in c]

def test_history_lost_reacquired_expired():
    h=TrackHistory(Config(track_buffer=2,trajectory_length=2));r={'track_id':1,'class_id':0,'bbox':[1,2,11,12],'confidence':.9}
    h.update([r],0,{0:'drone'});a,_=h.update([],1,{0:'drone'});assert a[0]['status']=='LOST'
    a,e=h.update([r],2,{0:'drone'});assert a[0]['status']=='REACQUIRED';assert e==['DR-01 reacquired']
    for i in range(3,7):a,e=h.update([r],i,{0:'drone'})
    assert len(a[0]['trajectory'])==2
    for i in range(7,10):a,e=h.update([],i,{0:'drone'})
    assert a==[];assert e==['DR-01 expired']

def test_packet_and_demo():
    frame=DemoSource().read()[1];assert len(DemoDetector().detect(frame))==6
    packet=pack_frame({'frame_id':3},b'jpeg');n=struct.unpack('!I',packet[:4])[0]
    assert json.loads(packet[4:4+n])=={'frame_id':3};assert packet[4+n:]==b'jpeg'

def test_no_fabricated_metrics():
    s=summarize([],0,0);assert s['precision'] is None;assert s['id_switches'] is None

def test_config_bounds():
    for kwargs in [{'image_size':641},{'confidence_threshold':2},{'device':'cuda-magic'},{'zoom':8}]:
        with pytest.raises(ValueError):Config(**kwargs)

def test_mot_id_switch():
    gt={1:[(1,[0,0,10,10],'drone')],2:[(1,[1,0,11,10],'drone')]}
    pred={1:[(3,[0,0,10,10],'drone')],2:[(4,[1,0,11,10],'drone')]}
    r=evaluate(gt,pred);assert r['id_switches']==1;assert r['detection_recall']==1


def test_new_class_does_not_recycle_existing_ids():
    tracker=MultiTracker(Config());frame=np.zeros((200,300,3),np.uint8)
    first=tracker.update([[20,20,50,50,.95,0]],frame)[0]['track_id']
    for _ in range(3):
        result=tracker.update([[20,20,50,50,.95,0],[100,20,130,50,.95,1],[180,20,210,50,.95,0]],frame)
    assert len({t['track_id'] for t in result})==3
    assert next(t['track_id'] for t in result if t['bbox'][0]<50)==first
