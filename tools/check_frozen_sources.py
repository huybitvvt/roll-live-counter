"""Prove the frozen Python modules match the public source being released."""
import argparse
import hashlib
import json
from pathlib import Path
import types
from PyInstaller.archive.readers import CArchiveReader


def structural(code):
    fields = ['co_argcount','co_posonlyargcount','co_kwonlyargcount','co_flags',
              'co_names','co_varnames','co_freevars','co_cellvars']
    result = {field:getattr(code,field) for field in fields}
    result['bytecode'] = code.co_code.hex()
    result['exceptions'] = code.co_exceptiontable.hex()
    result['constants'] = [structural(x) if isinstance(x,types.CodeType) else repr(x) for x in code.co_consts]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exe')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    archive = CArchiveReader(args.exe)
    key = next(k for k in archive.toc if k.endswith('.pyz'))
    pyz = archive.open_embedded_archive(key)
    checked = []
    for path in (root/'roll_counter').glob('*.py'):
        name = 'roll_counter' if path.stem=='__init__' else 'roll_counter.'+path.stem
        frozen = pyz.extract(name)
        source = compile(path.read_text('utf-8'),str(path),'exec',optimize=0)
        assert structural(frozen)==structural(source),f'Frozen source mismatch: {name}'
        checked.append(name)
    report = {'matches':checked,'modules':len(checked),'exe_sha256':hashlib.sha256(Path(args.exe).read_bytes()).hexdigest()}
    (root/'artifacts/frozen-sources.json').write_text(json.dumps(report,indent=2),'utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    main()
