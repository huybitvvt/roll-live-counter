"""Offline ONNX inference for the prompt-baked YOLOE-11 segmentation model.

The detector is zero-shot for rolls, NOT a model fine-tuned on factory data.
The runtime never imports Ultralytics/PyTorch or downloads models.
"""
import hashlib
import json
import time
import cv2
import numpy as np
import onnxruntime as ort

from .settings import resource


def letterbox(frame, size):
    h, w = frame.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = round(w * scale), round(h * scale)
    left, top = (size - nw) // 2, (size - nh) // 2
    canvas = np.full((size, size, 3), 114, np.uint8)
    canvas[top:top + nh, left:left + nw] = cv2.resize(frame, (nw, nh))
    return canvas, scale, left, top


class Detector:
    def __init__(self, folder=None):
        folder = folder or resource('assets/models')
        self.manifest = json.loads((folder / 'manifest.json').read_text('utf-8'))
        path = folder / self.manifest['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != self.manifest['sha256']:
            raise RuntimeError('Model bị thiếu hoặc sai SHA-256. Cài lại bộ cài chính thức.')
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        opts.inter_op_num_threads = 1
        opts.log_severity_level = 3
        self.session = ort.InferenceSession(str(path), opts, providers=['CPUExecutionProvider'])
        self.input = self.session.get_inputs()[0].name
        self.size = self.manifest['size']
        self.classes = len(self.manifest['prompts'])

    def detect(self, frame, confidence=.22):
        start = time.perf_counter()
        padded, scale, left, top = letterbox(frame, self.size)
        tensor = np.ascontiguousarray(padded[..., ::-1].transpose(2, 0, 1)[None], dtype=np.float32) / 255.
        outputs = self.session.run(None, {self.input: tensor})
        predictions, proto = outputs[0][0].T, outputs[1][0]
        scores = predictions[:, 4:4+self.classes].max(axis=1)
        selected = predictions[scores >= confidence]
        scores = scores[scores >= confidence]
        if not len(selected):
            return [], (time.perf_counter()-start)*1000
        xywh = selected[:, :4].copy()
        xywh[:, :2] -= xywh[:, 2:] / 2
        indexes = np.asarray(cv2.dnn.NMSBoxes(xywh.tolist(), scores.tolist(), confidence, .45)).flatten()[:100]
        h, w = frame.shape[:2]
        found = []
        ph, pw = proto.shape[1:]
        for i in indexes:
            x, y, bw, bh = xywh[i]
            box = np.array([(x-left)/scale, (y-top)/scale, (x+bw-left)/scale, (y+bh-top)/scale])
            box[[0, 2]] = box[[0, 2]].clip(0, w)
            box[[1, 3]] = box[[1, 3]].clip(0, h)
            if box[2]-box[0] < 5 or box[3]-box[1] < 8:
                continue
            logits = selected[i, 4+self.classes:] @ proto.reshape(proto.shape[0], -1)
            mask = cv2.resize(logits.reshape(ph, pw), (self.size, self.size))
            nh, nw = round(h*scale), round(w*scale)
            mask = cv2.resize(mask[top:top+nh, left:left+nw], (w, h)) > 0
            bx = box.astype(int)
            crop_mask = mask[bx[1]:bx[3], bx[0]:bx[2]]
            found.append({'box': box, 'score': float(scores[i]), 'mask': crop_mask})
        return found, (time.perf_counter()-start)*1000


def descriptor(frame, box, mask=None):
    """Generic HOG/texture + color evidence, not a trained instance ReID model.

    Never used alone to silently merge two identities. Ambiguous cross-ID
    matches are sent to an operator. No claim of unique visual fingerprints.
    """
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = np.asarray(box, int)
    crop = frame[max(0,y1):min(h,y2), max(0,x1):min(w,x2)]
    if not crop.size:
        return np.zeros(144, np.float32)
    if mask is not None and mask.shape == crop.shape[:2] and np.count_nonzero(mask) > 20:
        crop = crop.copy()
        crop[~mask] = 0
    gray = cv2.cvtColor(cv2.resize(crop, (32, 48)), cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    magnitude, angle = cv2.cartToPolar(gx, gy)
    cells = []
    bins = np.int32(angle * (8/(2*np.pi))) % 8
    for yy in range(0,48,16):
        for xx in range(0,32,8):
            hist = np.bincount(bins[yy:yy+16,xx:xx+8].ravel(), weights=magnitude[yy:yy+16,xx:xx+8].ravel(), minlength=8)
            cells.extend(hist/(np.linalg.norm(hist)+1e-6))
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0,1], None, [6,8], [0,180,0,256]).ravel()
    hist /= np.linalg.norm(hist)+1e-6
    feat = np.concatenate([np.asarray(cells)*.8, hist*2.])
    return (feat/(np.linalg.norm(feat)+1e-6)).astype(np.float32)
