from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

import cv2
import numpy as np
from PIL import Image, ImageTk, ImageGrab

from . import __version__
from .memory import Store
from .runtime import Runtime
from .settings import Settings,data_dir,resource

BG, CARD, INK, MUTED = '#f1f5f9','#ffffff','#0f172a','#475569'
GREEN, AMBER, LINE = '#047857','#92400e','#cbd5e1'


class App:
    def __init__(self,root,args):
        self.root,self.args = root,args
        self.folder = data_dir()
        self.config_path = self.folder/'settings.json'
        self.settings = Settings.load(self.config_path)
        if args.source is not None:
            self.settings.source = args.source
        self.runtime = Runtime(self.folder,self.settings)
        self.last_result = {}
        self.last_frame = None
        self.analyzed_frame = None
        self.show_analysis = args.analysis_view
        self.display_geometry = (0,0,1,1)
        self.selecting = False
        self.drag_start = None
        self.pending = []
        self.last_drawn = None
        self.root.title(f'Roll Live Counter {__version__} — Đếm cuộn camera')
        self.root.geometry('1280x850')
        self.root.minsize(1024,720)
        self.root.configure(bg=BG)
        try:
            self.root.iconbitmap(str(resource('assets/app.ico')))
        except tk.TclError:
            pass
        self.setup_style()
        self.build()
        self.refresh_history()
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.after(150,self.open_source)
        self.root.after(50,self.tick)
        if args.screenshot:
            self.root.after(int(args.screenshot_after*1000),self.screenshot)
        if args.exit_after:
            self.root.after(int(args.exit_after*1000),self.close)

    def setup_style(self):
        for name in ('TkDefaultFont','TkTextFont','TkMenuFont'):
            tkfont.nametofont(name).configure(family='Segoe UI',size=10)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.',font=('Segoe UI',10),background=BG,foreground=INK)
        style.configure('TFrame',background=BG)
        style.configure('Card.TFrame',background=CARD)
        style.configure('TLabel',background=BG,foreground=INK)
        style.configure('Muted.TLabel',foreground=MUTED)
        style.configure('Card.TLabel',background=CARD)
        style.configure('Title.TLabel',font=('Segoe UI',20,'bold'))
        style.configure('Count.TLabel',background=CARD,foreground=GREEN,font=('Segoe UI',60,'bold'))
        style.configure('TButton',padding=(12,9),background='#e2e8f0',foreground=INK,borderwidth=1)
        style.map('TButton',background=[('active','#cbd5e1')])
        style.configure('Primary.TButton',background=GREEN,foreground='white')
        style.map('Primary.TButton',background=[('active','#065f46')])
        style.configure('Treeview',rowheight=28,background=CARD,fieldbackground=CARD,foreground=INK)
        style.configure('Treeview.Heading',background='#e2e8f0',foreground=INK,font=('Segoe UI',10,'bold'))

    def build(self):
        outer = ttk.Frame(self.root,padding=18)
        outer.pack(fill='both',expand=True)
        footer = ttk.Frame(outer)
        footer.pack(side='bottom',fill='x',pady=(6,0))
        self.status = tk.StringVar(value='Khởi động...')
        ttk.Label(footer,textvariable=self.status,style='Muted.TLabel',wraplength=1200).pack(anchor='w')
        ttk.Label(footer,text='Model có sẵn, chưa train tại xưởng. Xanh: đã đếm · Vàng: cần kiểm tra · Xám: đang xác nhận.',
                  style='Muted.TLabel',wraplength=1200).pack(anchor='w',pady=(3,0))
        header = ttk.Frame(outer)
        header.pack(fill='x',pady=(0,12))
        ttk.Label(header,text='ROLL / ĐẾM CUỘN',style='Title.TLabel').pack(side='left')
        ttk.Label(header,text='CAMERA CỐ ĐỊNH  ·  KHÔNG CẦN QR',style='Muted.TLabel').pack(side='right')
        controls = ttk.Frame(outer)
        controls.pack(fill='x',pady=(0,10))
        ttk.Label(controls,text='Nguồn camera / RTSP / video:').pack(side='left')
        self.source = tk.StringVar(value=self.settings.source)
        ttk.Entry(controls,textvariable=self.source,width=38).pack(side='left',padx=8,fill='x',expand=True)
        ttk.Button(controls,text='Chọn tệp',command=self.pick_file).pack(side='left',padx=3)
        ttk.Button(controls,text='Mở nguồn',style='Primary.TButton',command=self.open_source).pack(side='left',padx=3)
        ttk.Button(controls,text='Dừng',command=self.stop).pack(side='left',padx=3)
        body = ttk.Frame(outer)
        body.pack(fill='both',expand=True)
        body.columnconfigure(0,weight=1)
        body.columnconfigure(1,weight=0,minsize=305)
        body.rowconfigure(0,weight=1)
        left = ttk.Frame(body)
        left.grid(row=0,column=0,sticky='nsew',padx=(0,14))
        left.rowconfigure(0,weight=1)
        left.columnconfigure(0,weight=1)
        self.canvas = tk.Canvas(left,bg='#111827',highlightthickness=0,takefocus=True)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        self.canvas.bind('<Button-1>',self.drag_begin)
        self.canvas.bind('<B1-Motion>',self.drag_move)
        self.canvas.bind('<ButtonRelease-1>',self.drag_end)
        self.canvas.bind('<Escape>',lambda _:self.cancel_zone())
        self.canvas.bind('<Configure>',lambda _:self.draw())
        zonebar = ttk.Frame(left)
        zonebar.grid(row=1,column=0,sticky='ew',pady=8)
        ttk.Button(zonebar,text='Chọn vùng bắt đầu đếm',command=self.choose_zone).pack(side='left')
        ttk.Button(zonebar,text='Toàn khung',command=self.clear_zone).pack(side='left',padx=6)
        self.view_button = ttk.Button(zonebar,text='Xem hình trực tiếp' if self.show_analysis else 'Xem khung đã nhận diện',command=self.toggle_analysis)
        self.view_button.pack(side='left',padx=6)
        ttk.Button(zonebar,text='Lưu ảnh',command=self.save_frame).pack(side='right')
        ttk.Label(left,text='Vùng chọn chỉ giới hạn nơi cộng cuộn mới. Cuộn đã đếm vẫn được theo dõi toàn hình.',
                  style='Muted.TLabel',wraplength=740).grid(row=2,column=0,sticky='w',pady=(0,8))
        right_shell = ttk.Frame(body)
        right_shell.grid(row=0,column=1,sticky='nsew')
        tabs = ttk.Notebook(right_shell)
        tabs.pack(fill='both',expand=True)
        count_tab = ttk.Frame(tabs)
        scroll = tk.Canvas(count_tab,bg=CARD,highlightthickness=0,width=290)
        scrollbar = ttk.Scrollbar(count_tab,orient='vertical',command=scroll.yview)
        scroll.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y')
        scroll.pack(side='left',fill='both',expand=True)
        right = ttk.Frame(scroll,style='Card.TFrame',padding=12)
        window = scroll.create_window((0,0),window=right,anchor='nw')
        right.bind('<Configure>',lambda _:scroll.configure(scrollregion=scroll.bbox('all')))
        scroll.bind('<Configure>',lambda event:scroll.itemconfigure(window,width=event.width))
        def scroll_sidebar(event):
            widget = self.root.winfo_containing(event.x_root,event.y_root)
            if widget and str(widget).startswith(str(count_tab)):
                scroll.yview_scroll(-int(event.delta/120),'units')
        self.root.bind_all('<MouseWheel>',scroll_sidebar,add='+')
        options_panel = ttk.Frame(tabs,style='Card.TFrame',padding=12)
        tabs.add(count_tab,text='Đếm & kiểm tra')
        tabs.add(options_panel,text='Thiết lập')
        ttk.Label(right,text='TỔNG ĐÃ XÁC NHẬN',style='Card.TLabel').pack(anchor='w')
        self.total = tk.StringVar(value='0')
        ttk.Label(right,textvariable=self.total,style='Count.TLabel').pack(anchor='w')
        self.detail = tk.StringVar(value='Đang nạp model...')
        ttk.Label(right,textvariable=self.detail,style='Card.TLabel',wraplength=265).pack(anchor='w',pady=(0,12))
        ttk.Separator(right).pack(fill='x',pady=8)
        ttk.Label(right,text='CẦN KIỂM TRA DANH TÍNH',style='Card.TLabel').pack(anchor='w',pady=(0,6))
        self.review = tk.Listbox(right,height=5,exportselection=False,bg='#fffbeb',fg=AMBER,
                                selectbackground='#fde68a',selectforeground=INK,relief='flat',font=('Segoe UI',10))
        self.review.pack(fill='x')
        self.review.bind('<<ListboxSelect>>',self.select_review)
        ttk.Button(right,text='Cuộn mới (+1)',command=lambda:self.resolve('new')).pack(fill='x',pady=(8,4))
        combo = ttk.Frame(right,style='Card.TFrame')
        combo.pack(fill='x')
        self.existing = ttk.Combobox(combo,state='readonly',width=8)
        self.existing.pack(side='left',padx=(0,6))
        ttk.Button(combo,text='Ghép mã đã đếm',command=lambda:self.resolve('merge')).pack(side='left',fill='x',expand=True)
        ttk.Button(right,text='Bỏ qua nhận diện này',command=lambda:self.resolve('ignore')).pack(fill='x',pady=4)
        ttk.Button(right,text='Xem ảnh cuộn đã đếm',command=self.show_reference).pack(fill='x',pady=4)
        ttk.Label(right,text='Chọn track vàng trong danh sách rồi xác nhận. Tổng chưa cộng các mục này.',
                  style='Card.TLabel',wraplength=265).pack(anchor='w',pady=6)
        ttk.Label(options_panel,text='ĐIỀU CHỈNH NHẬN DIỆN',style='Card.TLabel').pack(anchor='w',pady=(0,12))
        options = ttk.Frame(options_panel,style='Card.TFrame')
        options.pack(fill='x')
        ttk.Label(options,text='Ngưỡng:',style='Card.TLabel').pack(side='left')
        self.threshold = tk.StringVar(value=str(self.settings.confidence))
        ttk.Combobox(options,textvariable=self.threshold,values=['0.10','0.15','0.22','0.30','0.40','0.50'],width=5,state='readonly').pack(side='left',padx=4)
        ttk.Label(options,text='Quét/s:',style='Card.TLabel').pack(side='left')
        self.rate = tk.StringVar(value=str(self.settings.scan_fps))
        ttk.Combobox(options,textvariable=self.rate,values=['1.0','2.0','4.0','6.0','8.0'],width=4,state='readonly').pack(side='left',padx=4)
        ttk.Button(options_panel,text='Áp dụng',command=self.apply_settings).pack(fill='x',pady=6)
        self.collect = tk.BooleanVar(value=self.settings.collect)
        ttk.Checkbutton(options_panel,text='Thu ảnh để train sau (10 giây/ảnh)',variable=self.collect,command=self.apply_settings).pack(anchor='w',pady=6)
        ttk.Label(options_panel,text='Thu tối đa 500 ảnh hoặc 2 GB; ảnh và gợi ý nhận diện cần được kiểm tra nhãn trước khi train.',
                  style='Card.TLabel',wraplength=255).pack(anchor='w',pady=8)
        ttk.Button(options_panel,text='Mở thư mục dữ liệu',command=lambda:os.startfile(self.folder)).pack(fill='x',pady=4)
        ttk.Separator(options_panel).pack(fill='x',pady=12)
        ttk.Button(options_panel,text='Đặt lại tổng...',command=self.reset).pack(fill='x',pady=4)
        ttk.Label(options_panel,text='Tổng được giữ khi đóng ứng dụng hoặc mất camera. Không tự đặt lại theo xe. Khi đổi sang nguồn khác, tổng và bộ nhớ vẫn được giữ; đặt lại khi anh muốn bắt đầu một lần đếm mới.',
                  style='Card.TLabel',wraplength=255).pack(anchor='w',pady=8)
        bottom = ttk.Frame(outer)
        bottom.pack(fill='x',pady=(12,0))
        ttk.Label(bottom,text='LỊCH SỬ CỘNG DỒN',font=('Segoe UI',10,'bold')).pack(side='left')
        ttk.Button(bottom,text='Xuất CSV',command=self.export).pack(side='right')
        self.history = ttk.Treeview(outer,columns=('time','kind','id','note'),show='headings',height=3)
        for name,label,width in [('time','Thời gian',180),('kind','Sự kiện',100),('id','Mã cuộn',80),('note','Ghi chú',600)]:
            self.history.heading(name,text=label)
            self.history.column(name,width=width,minwidth=60)
        self.history.pack(fill='x',pady=6)

    def pick_file(self):
        path = filedialog.askopenfilename(filetypes=[('Video / ảnh','*.mp4 *.avi *.mkv *.mov *.jpg *.jpeg *.png'),('Tất cả','*.*')])
        if path:
            self.source.set(path)

    def open_source(self):
        value = self.source.get().strip()
        if not value:
            self.status.set('Nhập số camera (0, 1...), URL RTSP hoặc đường dẫn video.')
            return
        self.settings.source = value
        self.settings.save(self.config_path)
        self.last_result = {}
        self.last_frame = self.analyzed_frame = None
        self.refresh_pending([])
        self.last_drawn = None
        self.runtime.start()
        self.status.set('Đang mở nguồn và nạp model...')

    def stop(self):
        self.runtime.stop()
        self.status.set('Đã dừng. Tổng và bộ nhớ đã được giữ.')
        self.draw()

    def toggle_analysis(self):
        self.show_analysis = not self.show_analysis
        self.view_button.configure(text='Xem hình trực tiếp' if self.show_analysis else 'Xem khung đã nhận diện')
        self.draw()

    def apply_settings(self):
        self.settings.confidence = float(self.threshold.get())
        self.settings.scan_fps = float(self.rate.get())
        self.settings.collect = self.collect.get()
        self.settings.save(self.config_path)
        self.runtime.send('settings',value=asdict(self.settings))

    def choose_zone(self):
        self.selecting = True
        self.canvas.focus_set()
        self.status.set('Kéo chuột trên hình để chọn vùng. Esc để hủy. Không đặt lại tổng.')

    def cancel_zone(self):
        self.selecting = False
        self.drag_start = None
        self.canvas.delete('zone-drag')

    def clear_zone(self):
        self.cancel_zone()
        self.settings.zone = []
        self.settings.armed = True
        self.apply_settings()
        self.draw()

    def point(self,x,y):
        left,top,width,height = self.display_geometry
        return min(1.,max(0.,(x-left)/width)),min(1.,max(0.,(y-top)/height))

    def drag_begin(self,event):
        if self.selecting and self.last_frame is not None:
            self.drag_start = (event.x,event.y)

    def drag_move(self,event):
        if self.drag_start:
            self.canvas.delete('zone-drag')
            self.canvas.create_rectangle(*self.drag_start,event.x,event.y,outline='#38bdf8',width=3,tags='zone-drag')

    def drag_end(self,event):
        if not self.drag_start:
            return
        a,b = self.point(*self.drag_start),self.point(event.x,event.y)
        zone = [min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])]
        self.cancel_zone()
        if zone[2]-zone[0]>.02 and zone[3]-zone[1]>.02:
            self.settings.zone = zone
            self.settings.armed = True
            self.apply_settings()
            self.status.set('Đã chọn vùng bắt đầu đếm. Tiếp tục theo dõi toàn khung.')

    def refresh_pending(self,pending):
        selected = self.selected_track()
        self.pending = pending
        self.review.delete(0,'end')
        for i,item in enumerate(pending):
            self.review.insert('end',f"Track {item['track']} — cũ hay mới?")
            if item['track'] == selected:
                self.review.selection_set(i)
        if not self.review.curselection() and pending:
            self.review.selection_set(0)
        self.select_review()

    def selected_track(self):
        indexes = self.review.curselection()
        if indexes and indexes[0]<len(self.pending):
            return self.pending[indexes[0]]['track']
        return None

    def select_review(self,event=None):
        track = self.selected_track()
        ids = next((p['ids'] for p in self.pending if p['track']==track),[])
        values = [f'#{x}' for x in ids]
        old = self.existing.get()
        self.existing['values'] = values
        self.existing.set(old if old in values else (values[0] if values else ''))

    def resolve(self,kind):
        track = self.selected_track()
        if track is None:
            self.status.set('Chọn một track đang cần kiểm tra.')
            return
        existing = None
        if kind == 'merge':
            if not self.existing.get():
                return
            existing = int(self.existing.get().lstrip('#'))
        if self.runtime.send('resolve',track=track,id=existing,ignore=kind=='ignore'):
            self.status.set('Đã gửi xác nhận. Chờ cập nhật từ hình tiếp theo.')

    def show_reference(self):
        selected = self.existing.get().lstrip('#')
        if not selected:
            self.status.set('Chọn mã cuộn đã đếm trong ô bên cạnh nút Ghép.')
            return
        path = self.folder/'identities'/f'{int(selected)}.jpg'
        if not path.is_file():
            self.status.set('Chưa có ảnh tham chiếu của mã này.')
            return
        dialog = tk.Toplevel(self.root)
        dialog.title(f'Đối chiếu cuộn #{selected}')
        container = ttk.Frame(dialog,padding=16)
        container.pack(fill='both',expand=True)
        images = [('Cuộn đã đếm #'+selected,Image.open(path).convert('RGB'))]
        track = self.selected_track()
        obj = next((x for x in self.last_result.get('objects',[]) if x['track']==track),None)
        if obj and self.analyzed_frame is not None:
            x1,y1,x2,y2 = np.int32(obj['box'])
            crop = self.analyzed_frame[max(0,y1):max(0,y2),max(0,x1):max(0,x2)]
            if crop.size:
                images.append((f'Track hiện tại {track}',Image.fromarray(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB))))
        dialog.photos = []
        for column,(title,image) in enumerate(images):
            ttk.Label(container,text=title).grid(row=0,column=column,padx=12,pady=6)
            image.thumbnail((220,300))
            photo = ImageTk.PhotoImage(image)
            dialog.photos.append(photo)
            ttk.Label(container,image=photo).grid(row=1,column=column,padx=12,pady=6)
        ttk.Button(container,text='Đóng',command=dialog.destroy).grid(row=2,column=0,columnspan=2,pady=12)

    def reset(self):
        if messagebox.askyesno('Đặt lại bộ đếm','Đưa tổng về 0 và xóa bộ nhớ danh tính hiện tại? Lịch sử sự kiện vẫn được giữ. Chỉ làm khi anh muốn bắt đầu một lần đếm mới.'):
            if self.runtime.running:
                self.runtime.send('reset')
            else:
                store = Store(self.folder/'history.db')
                store.reset()
                store.close()
            self.refresh_history()

    def export(self):
        target = filedialog.asksaveasfilename(defaultextension='.csv',initialfile='lich-su-dem-cuon.csv',filetypes=[('CSV','*.csv')])
        if target:
            store = Store(self.folder/'history.db')
            store.export(target)
            store.close()
            self.status.set(f'Đã xuất: {target}')

    def save_frame(self):
        if self.last_frame is None:
            return
        samples = self.folder/'samples'
        samples.mkdir(exist_ok=True)
        target = samples/f'manual-{time.time_ns()}.jpg'
        cv2.imencode('.jpg',self.last_frame,[cv2.IMWRITE_JPEG_QUALITY,95])[1].tofile(target)
        self.status.set(f'Đã lưu ảnh gốc tại {target.name}')

    def refresh_history(self):
        store = Store(self.folder/'history.db')
        self.total.set(str(store.db.execute("SELECT COUNT(*) FROM items WHERE state='counted'").fetchone()[0]))
        rows = list(store.db.execute('SELECT at,kind,item_id,detail FROM events ORDER BY id DESC LIMIT 60'))
        store.close()
        self.history.delete(*self.history.get_children())
        for row in rows:
            self.history.insert('','end',values=row)

    def tick(self):
        latest,result = self.runtime.poll()
        if latest:
            self.last_frame = latest[2]
        if result:
            if 'total' in result:
                encoded = result.pop('image',None)
                if encoded:
                    self.analyzed_frame = cv2.imdecode(np.frombuffer(encoded,np.uint8),cv2.IMREAD_COLOR)
                self.last_result = result
                self.total.set(str(result['total']))
                self.detail.set(f"{len(result['objects'])} cuộn đang theo dõi\n{len(result['pending'])} cần kiểm tra\n{result['ms']:.0f} ms / lần nhận diện")
                self.refresh_pending(result['pending'])
                self.refresh_history()
            elif 'status' in result:
                self.detail.set(result['status'])
            if 'error' in result:
                self.status.set(result['error'])
        if self.runtime.running:
            age = time.monotonic()-latest[1] if latest else 999
            label = 'ĐANG CÓ HÌNH' if age<1.5 else ('VIDEO ĐÃ KẾT THÚC' if self.runtime.ended else 'ĐANG CHỜ HÌNH')
            warning = self.last_result.get('warning','')
            if not self.settings.armed:
                warning = 'Chọn vùng xe hoặc bấm Toàn khung để bắt đầu cộng cuộn.'
            self.status.set(f'{label} · {warning or self.runtime.notice or "Đang nhận diện cuộn"}')
            if self.show_analysis:
                self.status.set('ĐANG XEM KHUNG ĐÃ NHẬN DIỆN · '+self.status.get())
        elif self.runtime.notice:
            self.status.set(self.runtime.notice)
        self.draw()
        self.root.after(80,self.tick)

    def draw(self):
        if self.last_frame is None:
            self.canvas.delete('all')
            self.canvas.create_text(max(100,self.canvas.winfo_width()/2),max(100,self.canvas.winfo_height()/2),
                                    text='Đang chờ hình camera...\nCamera USB: nhập 0 hoặc 1\nCó thể mở video / ảnh để kiểm tra',
                                    fill='#cbd5e1',font=('Segoe UI',14),justify='center',tags='placeholder')
            return
        self.canvas.delete('placeholder')
        frame = (self.analyzed_frame if self.show_analysis and self.analyzed_frame is not None else self.last_frame).copy()
        h,w = frame.shape[:2]
        age = time.monotonic()-self.last_result.get('stamp',0)
        # Slow inference boxes must NOT be painted onto a different live frame.
        fresh = self.show_analysis or age<.4
        if fresh:
            for obj in self.last_result.get('objects',[]):
                color = (70,160,20) if obj['state']=='counted' else ((0,180,255) if obj['state']=='review' else (180,180,180))
                x1,y1,x2,y2 = np.int32(obj['box'])
                cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
                text = f"#{obj['id']} counted" if obj['id'] else f"T{obj['track']} {'REVIEW' if obj['state']=='review' else 'confirming'}"
                cv2.rectangle(frame,(x1,max(0,y1-24)),(min(w,x1+len(text)*8),y1),color,-1)
                cv2.putText(frame,text,(x1+2,max(14,y1-6)),cv2.FONT_HERSHEY_SIMPLEX,.48,(10,20,10),1,cv2.LINE_AA)
        if self.settings.zone:
            a,b,c,d = self.settings.zone
            cv2.rectangle(frame,(int(a*w),int(b*h)),(int(c*w),int(d*h)),(255,190,50),2)
        if self.show_analysis:
            cv2.putText(frame,f'ANALYZED FRAME - {age:.1f}s AGO',(18,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,200,255),2)
        if not self.runtime.running or (self.runtime.latest and time.monotonic()-self.runtime.latest[1]>2):
            cv2.putText(frame,'PAUSED / NO FRESH FRAME',(20,36),cv2.FONT_HERSHEY_SIMPLEX,.8,(50,160,255),2)
        cw,ch = max(1,self.canvas.winfo_width()),max(1,self.canvas.winfo_height())
        ratio = min(cw/w,ch/h)
        dw,dh = max(1,round(w*ratio)),max(1,round(h*ratio))
        left,top = (cw-dw)//2,(ch-dh)//2
        self.display_geometry = (left,top,dw,dh)
        image = Image.fromarray(cv2.cvtColor(cv2.resize(frame,(dw,dh)),cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.delete('frame')
        self.canvas.create_image(left,top,anchor='nw',image=self.photo,tags='frame')
        self.canvas.tag_lower('frame')

    def screenshot(self):
        self.root.update_idletasks()
        x,y = self.root.winfo_rootx(),self.root.winfo_rooty()
        ImageGrab.grab((x,y,x+self.root.winfo_width(),y+self.root.winfo_height())).save(self.args.screenshot)

    def close(self):
        self.runtime.stop()
        self.settings.save(self.config_path)
        if self.args.report:
            store = Store(self.folder/'history.db')
            report = {'version':__version__,'confirmed':sum(v['state']=='counted' for v in store.items().values()),
                      'last_result':self.last_result,'status':self.status.get()}
            store.close()
            Path(self.args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
        self.root.destroy()
