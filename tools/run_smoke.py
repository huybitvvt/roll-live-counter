"""Run source/frozen/installed UI with an isolated, generated test scene."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe')
    parser.add_argument('--name',default='smoke')
    parser.add_argument('--seconds',type=int,default=30)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    folder = root/'artifacts'/args.name
    folder.mkdir(exist_ok=True)
    settings = {'source':str(root/'artifacts/demo.png'),'confidence':.15,'scan_fps':2.,
                'zone':[.1875,.243,.8125,.792],'collect':True,'armed':True}
    (folder/'settings.json').write_text(json.dumps(settings),'utf-8')
    env = dict(os.environ,ROLL_COUNTER_DATA=str(folder))
    command = [args.exe] if args.exe else [sys.executable,'-m','roll_counter']
    command += ['--analysis-view','--source',settings['source'],'--exit-after',str(args.seconds),
                '--screenshot',str(folder/'window.png'),'--screenshot-after',str(args.seconds-5),
                '--report',str(folder/'report.json')]
    subprocess.run(command,cwd=root,env=env,timeout=args.seconds+45,check=True,
                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    report = json.loads((folder/'report.json').read_text('utf-8'))
    assert report['last_result'].get('raw',0)>0,report
    assert report['confirmed']>0,report
    assert list((folder/'samples').glob('*.jpg')),'Sample collection did not run'
    print(json.dumps({'ok':True,'name':args.name,'confirmed':report['confirmed'],
                      'last_inference_ms':report['last_result'].get('ms'),
                      'samples':len(list((folder/'samples').glob('*.jpg')))}))


if __name__=='__main__':
    main()
