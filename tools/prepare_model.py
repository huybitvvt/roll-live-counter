"""Build-only: bake roll prompts into official pretrained YOLOE, no training."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ['cylinder', 'roll', 'insulation roll', 'foil roll', 'plastic roll', 'paper roll']


def main():
    import torch
    from ultralytics import YOLOE
    torch.set_num_threads(2)
    target = ROOT / 'assets/models'
    target.mkdir(parents=True, exist_ok=True)
    model = YOLOE('yoloe-11s-seg.pt')
    model.set_classes(PROMPTS, model.get_text_pe(PROMPTS))
    # Export after fusing text; deployment needs no text encoder or network.
    exported = model.export(format='onnx', imgsz=640, opset=17, simplify=True, dynamic=False, nms=False, device='cpu')
    dest = target / 'roll-yoloe-11s.onnx'
    shutil.copyfile(exported, dest)
    manifest = {'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                'size':640,'prompts':PROMPTS,'source':'https://github.com/ultralytics/assets/releases',
                'checkpoint':'yoloe-11s-seg.pt','license':'AGPL-3.0','fine_tuned':False}
    (target/'manifest.json').write_text(json.dumps(manifest, indent=2), 'utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
