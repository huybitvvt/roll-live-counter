"""Unauthenticated public download + SHA-256 verification."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

root = Path(__file__).resolve().parents[1]
folder = root/'artifacts/public-download'
folder.mkdir(exist_ok=True)
name = 'RollLiveCounter-Setup.exe'
url = 'https://github.com/huybitvvt/roll-live-counter/releases/download/v0.1.0/'+name
expected = next(line.split()[0] for line in (root/'dist/installer/SHA256SUMS.txt').read_text().splitlines() if line.endswith('  '+name))
target = folder/name
with urllib.request.urlopen(url,timeout=90) as response, target.open('wb') as out:
    shutil.copyfileobj(response,out,length=1024*1024)
actual = hashlib.sha256(target.read_bytes()).hexdigest()
assert actual==expected,'Public download checksum mismatch'
with urllib.request.urlopen('https://api.github.com/repos/huybitvvt/roll-live-counter',timeout=30) as response:
    repo = json.load(response)
assert repo['private'] is False
report = {'url':url,'sha256':actual,'bytes':target.stat().st_size,'public_repository':True,'verified':True}
(folder/'verification.json').write_text(json.dumps(report,indent=2),'utf-8')
print(json.dumps(report))
