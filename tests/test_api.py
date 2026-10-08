from fastapi.testclient import TestClient
from app.main import app

def test_health_and_config():
    with TestClient(app) as c:
        assert c.get('/health').json()['ok']
        assert c.get('/config').json()['model_path']
        assert c.post('/config',json={'image_size':319}).status_code==422
        assert c.post('/stream/pause').status_code==409
        assert c.post('/stream/start',json={'source':'video','upload_id':'../../secret'}).status_code==422
        assert c.post('/stream/start',json={'source':'rtsp','rtsp_alias':'SECRET'}).status_code==422
        assert c.post('/upload-video',files={'file':('bad.mp4',b'not a video')}).status_code==422
        assert c.post('/config',json={},headers={'Origin':'https://untrusted.example'}).status_code==403

def test_websocket_status():
    with TestClient(app) as c:
        with c.websocket_connect('/ws/tracking') as ws:
            assert ws.receive_json()['type']=='status'

def test_report_validation():
    with TestClient(app) as c:
        report={'model':'trusted.pt','dataset':'held-out','split':'test','precision':.8,'recall':.7,'map50':.6,'map50_95':.4}
        assert c.post('/research/report',json=report).status_code==200
        assert c.get('/stats').json()['evaluation']['precision']==.8
        assert c.get('/reports/json').status_code==200
        assert c.post('/research/report',json={**report,'precision':2}).status_code==422
