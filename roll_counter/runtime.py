"""Bounded queues, native capture, isolated inference, recovery watchdog."""
from dataclasses import asdict
import multiprocessing as mp
from queue import Empty,Full
import time

from .workers import capture_worker,infer_worker,latest_put


class Runtime:
    def __init__(self,folder,settings):
        self.ctx = mp.get_context('spawn')
        self.folder,self.settings = str(folder),settings
        self.capture = self.inference = None
        self.latest = None
        self.last_sent = 0.
        self.last_seq = -1
        self.last_capture_start = 0.
        self.retries = []
        self.ended = False
        self.running = False
        self.notice = ''

    def start(self):
        self.stop()
        self.running = True
        self.latest = None
        self.last_seq = -1
        self.ended = False
        self.retries = []
        self.frames = self.ctx.Queue(maxsize=2)
        self.camera_status = self.ctx.Queue(maxsize=4)
        self.inbox = self.ctx.Queue(maxsize=1)
        self.results = self.ctx.Queue(maxsize=2)
        self.commands = self.ctx.Queue(maxsize=20)
        self.capture_stop,self.infer_stop = self.ctx.Event(),self.ctx.Event()
        self.capture_beat = self.ctx.Value('d',time.monotonic())
        self.infer_beat = self.ctx.Value('d',time.monotonic())
        self._camera()
        self.inference = self.ctx.Process(target=infer_worker,args=(self.inbox,self.results,self.commands,self.infer_stop,
                           self.infer_beat,self.folder,asdict(self.settings)),daemon=True)
        self.inference.start()

    def _camera(self):
        self.capture_beat.value = time.monotonic()
        self.last_capture_start = time.monotonic()
        self.capture = self.ctx.Process(target=capture_worker,args=(self.settings.source,self.frames,self.camera_status,
                            self.capture_stop,self.capture_beat),daemon=True)
        self.capture.start()

    def send(self,kind,**kwargs):
        if not self.running:
            return False
        try:
            self.commands.put_nowait({'kind':kind,**kwargs})
            return True
        except Full:
            self.notice = 'Đang bận; thử thao tác lại sau.'
            return False

    def poll(self):
        result = None
        if not self.running:
            return self.latest,result
        now = time.monotonic()
        while True:
            try:
                self.latest = self.frames.get_nowait()
            except Empty:
                break
        while True:
            try:
                kind,text = self.camera_status.get_nowait()
                self.notice = text
                if kind == 'ended':
                    self.ended = True
            except Empty:
                break
        if self.latest and self.latest[0] != self.last_seq and now-self.latest[1] < 1.5 and now-self.last_sent >= 1/self.settings.scan_fps:
            latest_put(self.inbox,self.latest)
            self.last_sent = now
            self.last_seq = self.latest[0]
        while True:
            try:
                result = self.results.get_nowait()
            except Empty:
                break
        if result and 'error' in result:
            self.notice = result['error']
        camera_bad = not self.ended and (not self.capture.is_alive() or now-self.capture_beat.value > 12.)
        infer_bad = not self.inference.is_alive() or now-self.infer_beat.value > 35.
        if (camera_bad or infer_bad) and now-self.last_capture_start > 4:
            self.retries = [t for t in self.retries if now-t<60]
            if len(self.retries) >= 3:
                self.stop()
                self.notice = 'Đã dừng sau 3 lỗi/phút. Kiểm tra nguồn và bấm Mở nguồn.'
            elif infer_bad:
                retries = self.retries+[now]
                self.stop()
                self.start()
                self.retries = retries
                self.notice = 'Đang khôi phục bộ nhận diện. Tổng được giữ; danh tính sẽ được kiểm tra lại.'
            else:
                self.retries.append(now)
                self._kill(self.capture)
                for name in ('frames','camera_status'):
                    old_queue = getattr(self,name)
                    old_queue.cancel_join_thread()
                    old_queue.close()
                    setattr(self,name,self.ctx.Queue(maxsize=2 if name=='frames' else 4))
                self.latest = None
                self.notice = 'Đang kết nối lại camera...'
                self._camera()
        return self.latest,result

    @staticmethod
    def _kill(process):
        if process is None:
            return
        process.join(timeout=.15)
        if process.is_alive():
            process.terminate()
            process.join(timeout=1.)
        if process.is_alive():
            process.kill()
            process.join(timeout=1.)

    def stop(self):
        if self.running:
            self.capture_stop.set()
            self.infer_stop.set()
            self._kill(self.capture)
            self._kill(self.inference)
            for name in ('frames','camera_status','inbox','results','commands'):
                queue = getattr(self,name)
                queue.cancel_join_thread()
                queue.close()
        self.running = False
        self.capture = self.inference = None
