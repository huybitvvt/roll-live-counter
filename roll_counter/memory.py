"""Durable physical identities and conservative counting, above tracker IDs."""
import csv
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import numpy as np


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS items (
          id INTEGER PRIMARY KEY, state TEXT NOT NULL, feature TEXT NOT NULL,
          box TEXT NOT NULL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, at TEXT NOT NULL, kind TEXT NOT NULL,
          item_id INTEGER, detail TEXT NOT NULL);
        ''')
        self.db.commit()

    def items(self):
        return {row[0]: {'id':row[0], 'state':row[1], 'feature':np.array(json.loads(row[2]), np.float32),
                        'box':json.loads(row[3]), 'first_seen':row[4], 'last_seen':row[5]}
                for row in self.db.execute('SELECT * FROM items')}

    def save(self, item):
        self.db.execute('INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?)',
                        (item['id'],item['state'],json.dumps(np.asarray(item['feature']).tolist()),
                         json.dumps(np.asarray(item['box']).tolist()),item['first_seen'],item['last_seen']))

    def event(self, kind, item_id=None, detail=''):
        self.db.execute('INSERT INTO events(at,kind,item_id,detail) VALUES (?,?,?,?)',
                        (datetime.now().astimezone().isoformat(timespec='seconds'),kind,item_id,detail))

    def export(self, path):
        with open(path, 'w', encoding='utf-8-sig', newline='') as out:
            writer = csv.writer(out)
            writer.writerow(['id','thoi_gian','su_kien','ma_cuon','chi_tiet'])
            writer.writerows(self.db.execute('SELECT * FROM events ORDER BY id'))

    def reset(self):
        self.db.execute('DELETE FROM items')
        self.event('RESET', detail='Người vận hành đặt lại bộ đếm')
        self.db.commit()

    def close(self):
        self.db.commit()
        self.db.close()


class Memory:
    def __init__(self, store, confirm_frames=3, confirm_seconds=.5, capacity=5000):
        self.store = store
        self.records = store.items()
        self.bindings = {}
        self.provisional = {}
        self.candidates = {}
        historical = store.db.execute('SELECT COALESCE(MAX(item_id),0) FROM events').fetchone()[0]
        self.next_id = max(max(self.records,default=0),historical)+1
        self.confirm_frames, self.confirm_seconds, self.capacity = confirm_frames, confirm_seconds, capacity
        self.zone = []
        self.enabled = True
        self.warning = ''
        self.previous_time = None
        self.visible_ids = set()

    @property
    def total(self):
        return sum(r['state']=='counted' for r in self.records.values())

    def reconnect(self):
        # A new camera/worker epoch MUST NOT reuse numerical tracker IDs.
        self.bindings.clear()
        self.provisional.clear()
        self.candidates.clear()
        self.visible_ids.clear()

    def inside(self, box, shape):
        if not self.zone:
            return True
        h,w = shape[:2]
        cx,cy = (box[0]+box[2])/(2*w), (box[1]+box[3])/(2*h)
        a,b,c,d = self.zone
        return a <= cx <= c and b <= cy <= d

    def update(self, detections, now, shape, continuity_known=False):
        if not continuity_known and self.previous_time is not None and now-self.previous_time > 3.:
            self.reconnect()
        self.previous_time = now
        # Collect ALL visible identities first, before matching new detections.
        visible = {self.bindings[d['track']] for d in detections if d['track'] in self.bindings}
        seen_tracks = {d['track'] for d in detections}
        self.provisional = {k:v for k,v in self.provisional.items() if k in seen_tracks}
        self.candidates = {}
        stamps = datetime.now().astimezone().isoformat(timespec='seconds')
        output = []
        for detection in detections:
            key = detection['track']
            box, feat = detection['box'], detection['feature']
            if key in self.bindings:
                record = self.records[self.bindings[key]]
                record.update(box=box, last_seen=stamps)
                # Keep original appearance; background contamination must not
                # overwrite a counted object's identity model on every frame.
                self.store.save(record)
                state = record['state']
                object_id = record['id']
            else:
                pending = self.provisional.setdefault(key, {'hits':0, 'start':now})
                pending['hits'] += 1
                state, object_id = 'confirming', None
                if self.enabled and pending['hits'] >= self.confirm_frames and now-pending['start'] >= self.confirm_seconds and self.inside(box, shape):
                    possible = []
                    for rid, record in self.records.items():
                        if rid in visible:
                            continue
                        sim = float(np.dot(feat, record['feature']))
                        if sim >= .80:
                            possible.append((sim, rid))
                    possible.sort(reverse=True)
                    if possible:
                        # Never merge by color/shape alone: identical rolls
                        # require a review when temporal continuity is lost.
                        state = 'review'
                        self.candidates[key] = {'track':key,'box':np.asarray(box).tolist(),
                                                'feature':feat,'ids':[rid for _,rid in possible[:8]]}
                    elif len(self.records) >= self.capacity:
                        state = 'review'
                        self.warning = 'Bộ nhớ đạt 5.000 cuộn. Xuất lịch sử và đặt lại khi phù hợp.'
                    else:
                        object_id = self._create(box, feat, stamps)
                        self.bindings[key] = object_id
                        visible.add(object_id)
                        state = 'counted'
            output.append({'track':key,'id':object_id,'state':state,'box':np.asarray(box).tolist(),
                           'score':detection.get('score',1.)})
        self.store.db.commit()
        self.visible_ids = visible
        return output

    def _create(self, box, feat, stamp):
        rid = self.next_id
        self.next_id += 1
        record = {'id':rid,'state':'counted','box':np.asarray(box).tolist(),'feature':feat,
                  'first_seen':stamp,'last_seen':stamp}
        self.records[rid] = record
        self.store.save(record)
        self.store.event('COUNT', rid, 'Cuộn mới được xác nhận')
        return rid

    def resolve(self, track, existing_id=None, ignore=False):
        candidate = self.candidates.get(track)
        if candidate is None:
            return False
        if existing_id is not None:
            if existing_id not in candidate['ids'] or existing_id in self.visible_ids:
                return False
            rid = existing_id
            self.store.event('MERGE', rid, f'Người vận hành ghép track {track}')
        elif ignore:
            rid = self.next_id
            self.next_id += 1
            stamp = datetime.now().astimezone().isoformat(timespec='seconds')
            self.records[rid] = {'id':rid,'state':'ignored','box':candidate['box'],
                                 'feature':candidate['feature'],'first_seen':stamp,'last_seen':stamp}
            self.store.save(self.records[rid])
            self.store.event('IGNORE', rid, 'Người vận hành bỏ qua nhận diện')
        else:
            if len(self.records) >= self.capacity:
                return False
            stamp = datetime.now().astimezone().isoformat(timespec='seconds')
            rid = self._create(candidate['box'], candidate['feature'], stamp)
            self.store.event('REVIEW_NEW', rid, f'Người vận hành xác nhận track {track}')
        # One physical ID may have only one current tracker binding.
        self.bindings = {k:v for k,v in self.bindings.items() if v != rid}
        self.bindings[track] = rid
        self.candidates.pop(track, None)
        self.store.db.commit()
        return True
