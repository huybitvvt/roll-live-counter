"""Check real multiprocessing camera I/O with a generated video, no hardware."""
import json
import multiprocessing as mp
from pathlib import Path
from queue import Empty
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roll_counter.workers import capture_worker


def main():
    root = Path(__file__).resolve().parents[1]
    ctx = mp.get_context('spawn')
    frames,status = ctx.Queue(maxsize=2),ctx.Queue(maxsize=4)
    stop,beat = ctx.Event(),ctx.Value('d',time.monotonic())
    process = ctx.Process(target=capture_worker,args=(str(root/'artifacts/demo.avi'),frames,status,stop,beat))
    process.start()
    deadline = time.monotonic()+12
    previous = 0
    received = 0
    shape = None
    while time.monotonic()<deadline and received<30:
        try:
            seq,stamp,frame = frames.get(timeout=.5)
        except Empty:
            continue
        assert seq>previous
        previous = seq
        assert time.monotonic()-stamp < 3
        shape = frame.shape
        received += 1
    stop.set()
    process.join(timeout=3)
    if process.is_alive():
        process.terminate()
        process.join(timeout=2)
    assert received>=30
    assert shape == (720,1280,3)
    result = {'frames_received':received,'shape':shape,'exit_code':process.exitcode,'queue_capacity':2}
    (root/'artifacts/capture-check.json').write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    mp.freeze_support()
    main()
