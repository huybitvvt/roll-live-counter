import hashlib
import json
from pathlib import Path
import urllib.request

root = Path(__file__).resolve().parents[1]
folder = root/'assets/models'
manifest = json.loads((folder/'manifest.json').read_text('utf-8'))
path = folder/manifest['file']
temporary = path.with_suffix('.download')
url = f'https://github.com/huybitvvt/roll-live-counter/releases/download/v0.1.0/{path.name}'
urllib.request.urlretrieve(url,temporary)
if hashlib.sha256(temporary.read_bytes()).hexdigest() != manifest['sha256']:
    raise RuntimeError('Model SHA-256 mismatch')
temporary.replace(path)
print('Verified model:',path)
