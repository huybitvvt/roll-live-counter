import hashlib
import json
import logging
from pathlib import Path
from queue import Empty, Full
import time

import cv2
import numpy as np


def latest_put(queue, item):
    try:
        queue.put_nowait(item)
    except Full:
        try:
            queue.get_nowait()
        except Empty:
            pass
        try:
            queue.put_nowait(item)
        except Full:
            pass


def capture_worker(source, frames, status, stop, heartbeat, generation=0):
    cv2.setNumThreads(1)
    frames.cancel_join_thread()
    status.cancel_join_thread()
    heartbeat.value = time.monotonic()
    camera = None
    try:
        path = Path(source)
        still = None
        if path.suffix.lower() in ('.jpg','.jpeg','.png','.bmp','.webp') and path.is_file():
            still = cv2.imdecode(np.fromfile(path,np.uint8),cv2.IMREAD_COLOR)
            if still is None:
                raise ValueError('Không đọc được ảnh.')
        else:
            is_usb = source.isdigit()
            camera = cv2.VideoCapture(int(source), cv2.CAP_DSHOW) if is_usb else cv2.VideoCapture(source)
            if not camera.isOpened():
                raise RuntimeError('Không mở được nguồn. Kiểm tra số camera, đường dẫn hoặc kết nối.')
            if is_usb:
                camera.set(cv2.CAP_PROP_FRAME_WIDTH,1280)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
                camera.set(cv2.CAP_PROP_FPS,25)
            camera.set(cv2.CAP_PROP_BUFFERSIZE,1)
        is_file = still is None and path.is_file()
        fps = camera.get(cv2.CAP_PROP_FPS) if is_file else 20.
        fps = min(30.,max(1.,fps or 20.))
        seq = 0
        last_publish = 0.
        last_read = time.monotonic()
        pause_epoch = 0
        latest_put(status, ('ready', 'Ảnh tĩnh' if still is not None else ('Video' if is_file else 'Camera')))
        while not stop.is_set():
            began = time.monotonic()
            if still is not None:
                frame = still.copy()
            else:
                ok,frame = camera.read()
                if not ok:
                    latest_put(status,('ended' if is_file else 'error', 'Video đã kết thúc.' if is_file else 'Mất hình camera.'))
                    return
            # Drain native streams at their own rate. Sleeping after every
            # RTSP read would accumulate latency when a 25/30 FPS camera is
            # published to a 20 FPS preview.
            heartbeat.value = time.monotonic()
            if not is_file and still is None and heartbeat.value-last_read > 3.:
                pause_epoch += 1
            last_read = heartbeat.value
            if not is_file and still is None and heartbeat.value-last_publish < .05:
                stop.wait(.001)
                continue
            last_publish = heartbeat.value
            h,w = frame.shape[:2]
            scale = min(1280/w,720/h,1.)
            if scale < 1:
                frame = cv2.resize(frame,(round(w*scale),round(h*scale)))
            seq += 1
            heartbeat.value = time.monotonic()
            latest_put(frames,(seq,heartbeat.value,frame,(generation,pause_epoch)))
            if is_file or still is not None:
                stop.wait(max(0.,1/fps-(time.monotonic()-began)))
    except Exception as exc:
        latest_put(status,('error',str(exc)))
    finally:
        if camera is not None:
            camera.release()


def create_tracker(fps=4.):
    from trackers import BoTSORTTracker
    return BoTSORTTracker(frame_rate=fps, lost_track_buffer=120,
                          minimum_consecutive_frames=2,
                          instant_first_frame_activation=False,enable_cmc=False,
                          track_activation_threshold=.10,high_conf_det_threshold=.10,
                          minimum_iou_threshold_first_assoc=.10,
                          minimum_iou_threshold_unconfirmed_assoc=.10)


def track_detections(tracker, raw, frame):
    import supervision as sv
    from .detector import descriptor
    values = sv.Detections(
        xyxy=np.asarray([d['box'] for d in raw],np.float32).reshape(-1,4),
        confidence=np.asarray([d['score'] for d in raw],np.float32),
        class_id=np.zeros(len(raw),np.int32))
    tracked = tracker.update(values,frame=frame)
    output = []
    if tracked.tracker_id is None:
        return output
    for box,score,tid in zip(tracked.xyxy,tracked.confidence,tracked.tracker_id):
        if int(tid) < 0:
            continue
        nearest = min(raw,key=lambda d:float(np.linalg.norm(np.asarray(d['box'])-box))) if raw else None
        mask = nearest.get('mask') if nearest is not None else None
        output.append({'box':box,'score':float(score),'track':int(tid),
                       'feature':descriptor(frame,box,mask)})
    return output


def infer_worker(inbox, results, commands, stop, heartbeat, folder, settings):
    from logging.handlers import RotatingFileHandler
    logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(
        Path(folder)/'inference.log',maxBytes=1_000_000,backupCount=3,encoding='utf-8')])
    from .detector import Detector
    from .memory import Memory,Store
    cv2.setNumThreads(1)
    results.cancel_join_thread()
    heartbeat.value = time.monotonic()
    store = None
    try:
        latest_put(results,{'status':'Đang nạp model có sẵn...'})
        detector = Detector()
        store = Store(Path(folder)/'history.db')
        memory = Memory(store)
        memory.zone = settings['zone']
        memory.enabled = settings.get('armed',False)
        tracker = create_tracker(settings['scan_fps'])
        last_epoch = None
        last_data = 0.
        files = list((Path(folder)/'samples').glob('*.jpg')) if (Path(folder)/'samples').exists() else []
        sample_count = len(files)
        latest_put(results,{'status':'Model đã sẵn sàng — nhận diện cuộn chưa fine-tune.'})
        while not stop.is_set():
            heartbeat.value = time.monotonic()
            while True:
                try:
                    command = commands.get_nowait()
                except Empty:
                    break
                kind = command['kind']
                if kind == 'settings':
                    settings.update(command['value'])
                    memory.zone = settings['zone']
                    memory.enabled = settings.get('armed',False)
                elif kind == 'reset':
                    store.reset()
                    memory = Memory(store)
                    memory.zone = settings['zone']
                    memory.enabled = settings.get('armed',False)
                    tracker = create_tracker(settings['scan_fps'])
                elif kind == 'resolve':
                    memory.resolve(command['track'],command.get('id'),command.get('ignore',False))
            try:
                seq,stamp,frame,epoch = inbox.get(timeout=.1)
            except Empty:
                continue
            if time.monotonic()-stamp > 3.:
                continue
            if last_epoch is not None and epoch != last_epoch:
                memory.reconnect()
                tracker = create_tracker(settings['scan_fps'])
            last_epoch = epoch
            raw,ms = detector.detect(frame,settings['confidence'])
            # The trolley can occupy a small part of a wide camera view.
            # A second native-pixel crop pass improves sampling of its rolls,
            # while the full pass keeps following previously counted objects.
            if settings['zone']:
                h,w = frame.shape[:2]
                a,b,c,d = settings['zone']
                x1,y1,x2,y2 = int(a*w),int(b*h),int(c*w),int(d*h)
                crop = frame[y1:y2,x1:x2]
                if crop.size and (c-a)*(d-b)<.65:
                    extra,crop_ms = detector.detect(crop,settings['confidence'])
                    ms += crop_ms
                    for obj in extra:
                        obj['box'] = obj['box']+np.array([x1,y1,x1,y1])
                    raw += extra
                    if raw:
                        boxes = [np.asarray(x['box']).copy() for x in raw]
                        for box in boxes:
                            box[2:] -= box[:2]
                        keep = np.asarray(cv2.dnn.NMSBoxes([b.tolist() for b in boxes],
                                      [x['score'] for x in raw],settings['confidence'],.45)).flatten()
                        raw = [raw[i] for i in keep]
            heartbeat.value = time.monotonic()
            if heartbeat.value-stamp > 5.:
                latest_put(results,{'status':'Máy xử lý quá chậm; chưa cộng kết quả từ hình cũ. Hạ nhịp quét.'})
                continue
            tracked = track_detections(tracker,raw,frame)
            # Capture supplies continuity epochs. Slow CPU sampling alone is
            # not evidence that the camera lost its source or identities.
            objects = memory.update(tracked,stamp,frame.shape,continuity_known=True)
            thumbnails = Path(folder)/'identities'
            thumbnails.mkdir(exist_ok=True)
            for obj in objects:
                if obj['id'] and not (thumbnails/f"{obj['id']}.jpg").exists():
                    x1,y1,x2,y2 = np.int32(obj['box'])
                    crop = frame[max(0,y1):max(0,y2),max(0,x1):max(0,x2)]
                    if crop.size:
                        crop = cv2.resize(crop,(96,144))
                        cv2.imencode('.jpg',crop,[cv2.IMWRITE_JPEG_QUALITY,80])[1].tofile(thumbnails/f"{obj['id']}.jpg")
            pending = [{'track':x['track'],'ids':x['ids']} for x in memory.candidates.values()]
            analysis_image = cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,78])[1].tobytes()
            latest_put(results,{'seq':seq,'stamp':stamp,'total':memory.total,'objects':objects,
                                'pending':pending,'ms':round(ms,1),'raw':len(raw),
                                'latency_ms':round((time.monotonic()-stamp)*1000,1),
                                'warning':memory.warning,'status':'Đang nhận diện','image':analysis_image})
            if settings['collect'] and time.monotonic()-last_data >= 10 and sample_count < 500:
                target = Path(folder)/'samples'
                target.mkdir(exist_ok=True)
                if sum(p.stat().st_size for p in target.glob('*') if p.is_file()) < 2_000_000_000:
                    name = f'{time.time_ns()}'
                    cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,92])[1].tofile(target/f'{name}.jpg')
                    (target/f'{name}.json').write_text(json.dumps({'reviewed':False,'objects':objects},ensure_ascii=False),'utf-8')
                    sample_count += 1
                last_data = time.monotonic()
    except Exception:
        logging.exception('Inference worker failed')
        latest_put(results,{'error':'Bộ nhận diện gặp lỗi. Xem app.log trong thư mục dữ liệu.'})
    finally:
        if store is not None:
            store.close()
