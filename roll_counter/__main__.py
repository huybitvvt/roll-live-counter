import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import multiprocessing as mp
import sys
import traceback


def main():
    import os
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[name] = '2'
    mp.freeze_support()
    from .settings import data_dir
    folder = data_dir()
    handler = RotatingFileHandler(folder/'app.log',maxBytes=1_000_000,backupCount=3,encoding='utf-8')
    logging.basicConfig(level=logging.INFO,handlers=[handler])
    parser = argparse.ArgumentParser()
    parser.add_argument('--source')
    parser.add_argument('--exit-after',type=float,default=0)
    parser.add_argument('--screenshot')
    parser.add_argument('--screenshot-after',type=float,default=8)
    parser.add_argument('--report')
    parser.add_argument('--diagnose')
    parser.add_argument('--analysis-view',action='store_true')
    args = parser.parse_args()
    if args.diagnose:
        from .detector import Detector
        from .workers import create_tracker,track_detections
        import numpy as np
        from pathlib import Path
        detector = Detector()
        frame = np.full((480,640,3),120,np.uint8)
        raw,ms = detector.detect(frame)
        tracks = track_detections(create_tracker(),raw,frame)
        Path(args.diagnose).write_text(json.dumps({'ok':True,'inference_ms':ms,'detections':len(raw),
                                     'tracker_ok':True,'providers':detector.session.get_providers()}),'utf-8')
        return
    import tkinter as tk
    import ctypes
    mutex = None
    if os.name == 'nt':
        ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
        ctypes.windll.kernel32.CreateMutexW.argtypes = [ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
        ctypes.windll.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        mutex = ctypes.windll.kernel32.CreateMutexW(None,False,'Local\\RollLiveCounter')
        if ctypes.windll.kernel32.GetLastError() == 183:
            ctypes.windll.user32.MessageBoxW(0,'Roll Live Counter đang chạy. Kiểm tra cửa sổ hiện có.','Roll Live Counter',0x40)
            return
    from .ui import App
    root = tk.Tk()
    def callback_error(cls,exception,tb):
        logging.error('UI error',exc_info=(cls,exception,tb))
        from tkinter import messagebox
        messagebox.showerror('Lỗi ứng dụng',f'{exception}\nChi tiết: {folder / "app.log"}')
    root.report_callback_exception = callback_error
    App(root,args)
    root.mainloop()
    if mutex:
        ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == '__main__':
    main()
