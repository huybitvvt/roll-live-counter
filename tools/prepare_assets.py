import importlib.metadata as metadata
from pathlib import Path
import shutil
import sys
import urllib.request
from PIL import Image,ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main():
    assets = ROOT/'assets'
    assets.mkdir(exist_ok=True)
    licenses = assets/'licenses'
    licenses.mkdir(exist_ok=True)
    if not (ROOT/'LICENSE').exists():
        urllib.request.urlretrieve('https://www.gnu.org/licenses/agpl-3.0.txt',ROOT/'LICENSE')
    icon = Image.new('RGB',(256,256),'#0f172a')
    draw = ImageDraw.Draw(icon)
    for x in (40,105,170):
        draw.rounded_rectangle((x,65,x+46,200),radius=12,fill='#10b981')
        draw.ellipse((x,48,x+46,85),fill='#d1fae5')
        draw.ellipse((x+12,57,x+34,74),fill='#0f172a')
    icon.save(assets/'app.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    # Preserve full distribution licenses for every packaged dependency.
    for dist in metadata.distributions():
        name = dist.metadata['Name'] or 'unknown'
        if name.lower() in ('torch','torchvision','onnx','onnxslim','ultralytics-thop','polars-runtime-32'):
            continue
        for file in dist.files or []:
            if any(s in file.name.lower() for s in ('license','copyright','notice')):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = licenses/name
                    target.mkdir(exist_ok=True)
                    filename = str(file).replace('..','_').replace('/','__').replace('\\','__')
                    shutil.copyfile(source,target/filename)
    for source in [Path(sys.base_prefix)/'LICENSE.txt',*Path(sys.base_prefix).glob('tcl/*/license.terms')]:
        if source.is_file():
            shutil.copyfile(source,licenses/f'{source.parent.name}-{source.name}')
    print('Assets and third-party licenses ready.')


if __name__ == '__main__':
    main()
