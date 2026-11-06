"""Actual ONNX inference smoke check; no assertion of factory accuracy."""
import argparse
import json
from pathlib import Path
import statistics
import sys

import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roll_counter.detector import Detector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image',required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    image = cv2.imdecode(np.fromfile(args.image,np.uint8),cv2.IMREAD_COLOR)
    assert image is not None
    detector = Detector()
    found,timing = detector.detect(image,.15)
    times = []
    for _ in range(5):
        found,ms = detector.detect(image,.15)
        times.append(ms)
    report = {'source_filename':Path(args.image).name,'input_shape':list(image.shape),
              'model':detector.manifest,'warm_median_ms':statistics.median(times),
              'first_inference_ms':timing,'detections':[
                  {'box':x['box'].tolist(),'score':x['score'],'mask_pixels':int(np.count_nonzero(x['mask']))}
                  for x in found], 'factory_accuracy_verified':False}
    (root/'artifacts/model-check.json').write_text(json.dumps(report,indent=2),'utf-8')
    for obj in found:
        a,b,c,d = np.int32(obj['box'])
        cv2.rectangle(image,(a,b),(c,d),(0,220,0),2)
        cv2.putText(image,f"{obj['score']:.2f}",(a,max(16,b-5)),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,220,0),2)
    cv2.imencode('.jpg',image)[1].tofile(root/'artifacts/model-check.jpg')
    print(json.dumps({'detections':len(found),'warm_median_ms':statistics.median(times),
                      'providers':detector.session.get_providers()}))


if __name__=='__main__':
    main()
