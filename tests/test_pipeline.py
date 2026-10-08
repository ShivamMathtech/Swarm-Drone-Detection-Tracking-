import json
import struct
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from ultralytics import YOLO
from app.main import app
from app.config import Config
from app.detection.yolo_detector import YoloDetector

@pytest.mark.integration
def test_video_yolo_tracker_websocket(tmp_path):
    # Untrained network verifies real tensor inference/transport, not drone accuracy.
    weights=tmp_path/'untrained.pt';YOLO('yolov8n.yaml').save(str(weights))
    cfg=Config(model_path=str(weights),image_size=320)
    detector=YoloDetector(cfg)
    assert detector.detect(np.zeros((180,320,3),np.uint8)).shape[1]==6
    video=tmp_path/'fixture.avi';writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),15,(320,180))
    assert writer.isOpened()
    for i in range(60):
        f=np.zeros((180,320,3),np.uint8);cv2.rectangle(f,(i+10,50),(i+35,70),(220,220,220),-1);writer.write(f)
    writer.release()
    with TestClient(app) as client:
        old=client.get('/config').json()
        try:
            assert client.post('/config',json=cfg.model_dump()).status_code==200
            upload=client.post('/upload-video',files={'file':('fixture.avi',video.read_bytes())}).json()
            with client.websocket_connect('/ws/tracking') as ws:
                ws.receive_json()
                assert client.post('/stream/start',json={'source':'video','upload_id':upload['upload_id']}).status_code==200
                while True:
                    message=ws.receive()
                    if message.get('bytes'):
                        b=message['bytes'];n=struct.unpack('!I',b[:4])[0];meta=json.loads(b[4:4+n])
                        assert not meta['demo'];assert meta['model']=='untrained.pt';assert meta['width']==320
                        assert cv2.imdecode(np.frombuffer(b[4+n:],np.uint8),1).shape==(180,320,3)
                        break
                    if message.get('text'):
                        status=json.loads(message['text']);assert status.get('status')!='ERROR',status
                assert client.post('/stream/pause').status_code==200
                assert client.post('/stream/resume').status_code==200
        finally:
            client.post('/stream/stop');client.post('/config',json=old)


@pytest.mark.integration
def test_demo_with_nonempty_tracks_is_serializable():
    with TestClient(app) as client:
        with client.websocket_connect('/ws/tracking') as ws:
            ws.receive_json();client.post('/stream/start',json={'source':'demo'})
            try:
                for _ in range(20):
                    msg=ws.receive()
                    if msg.get('text'):
                        status=json.loads(msg['text']);assert status.get('status')!='ERROR',status
                    if msg.get('bytes'):
                        b=msg['bytes'];n=struct.unpack('!I',b[:4])[0];meta=json.loads(b[4:4+n])
                        assert len(meta['targets'])==6
                        assert meta['demo'] is True
                        assert meta['targets'][0]['class_id']==0
                        break
                else:pytest.fail('No frame received')
            finally:client.post('/stream/stop')
