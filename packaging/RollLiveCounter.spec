# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs,copy_metadata

root = Path(SPECPATH).parent
datas = [(str(root/'assets'),'assets'),(str(root/'LICENSE'),'.'),
         (str(root/'THIRD-PARTY-NOTICES.md'),'.')]
binaries = collect_dynamic_libs('onnxruntime')
hiddenimports = []
for package in ('trackers','supervision'):
    datas += copy_metadata(package)
a = Analysis([str(root/'launcher.py')],pathex=[str(root)],binaries=binaries,
    datas=datas,hiddenimports=hiddenimports,hookspath=[],runtime_hooks=[],
    hooksconfig={'matplotlib':{'backends':['Agg']}},
    excludes=['torch','torchvision','ultralytics','onnx','onnxslim','pytest',
              'pandas','tensorflow','transformers','IPython','notebook','polars'],noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='RollLiveCounter',
          console=False,upx=False,strip=False,icon=str(root/'assets/app.ico'))
coll = COLLECT(exe,a.binaries,a.datas,name='RollLiveCounter',upx=False,strip=False)
