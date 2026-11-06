import numpy as np
from roll_counter.workers import create_tracker,track_detections
from roll_counter.memory import Memory,Store
from roll_counter.detector import letterbox,descriptor
from roll_counter.settings import Settings


def test_botsort_with_count_memory_five_plus_five(tmp_path):
    store = Store(tmp_path/'db')
    memory = Memory(store,confirm_frames=2,confirm_seconds=.1)
    tracker = create_tracker()
    frame = np.full((480,640,3),150,np.uint8)
    first = [np.array([20+40*i,30,45+40*i,120]) for i in range(5)]
    for tick in range(10):
        raw = [{'box':b,'score':.9} for b in first]
        tracks = track_detections(tracker,raw,frame)
        memory.update(tracks,tick*.25,frame.shape)
    assert memory.total == 5
    # Slowly move first five to the right, preserving temporal continuity.
    for tick in range(10,35):
        dx,dy = min(250,(tick-9)*4),min(150,(tick-9)*3)
        shifted = [b+np.array([dx,dy,dx,dy]) for b in first]
        raw = [{'box':b,'score':.9} for b in shifted]
        tracks = track_detections(tracker,raw,frame)
        memory.update(tracks,tick*.25,frame.shape)
    assert memory.total == 5
    for tick in range(35,45):
        raw = [{'box':b,'score':.9} for b in shifted+first]
        tracks = track_detections(tracker,raw,frame)
        memory.update(tracks,tick*.25,frame.shape)
    assert memory.total == 10
    store.close()


def test_letterbox_preserves_geometry():
    image,scale,left,top = letterbox(np.zeros((480,1280,3),np.uint8),640)
    assert image.shape == (640,640,3)
    assert scale == .5 and left == 0 and top == 200


def test_low_confidence_detections_follow_user_detector_threshold():
    tracker = create_tracker()
    frame = np.full((100,100,3),150,np.uint8)
    raw = [{'box':np.array([20,20,50,80]),'score':.24}]
    tracks = []
    for _ in range(4):
        tracks = track_detections(tracker,raw,frame)
    assert len(tracks) == 1


def test_descriptor_is_finite_for_blank_and_masked_crops():
    frame = np.zeros((80,60,3),np.uint8)
    feat = descriptor(frame,[0,0,60,80],np.ones((80,60),bool))
    assert feat.shape == (144,)
    assert np.isfinite(feat).all()


def test_corrupt_settings_recover(tmp_path):
    path = tmp_path/'settings.json'
    path.write_text('{invalid','utf-8')
    assert Settings.load(path).source == '0'
    settings = Settings(source='1',zone=[.1,.2,.8,.9])
    settings.save(path)
    assert Settings.load(path).zone == settings.zone
    path.write_text(path.read_text('utf-8'),encoding='utf-8-sig')
    assert Settings.load(path).zone == settings.zone
