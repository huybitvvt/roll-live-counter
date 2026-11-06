from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import sys


def resource(name):
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1])) / name


def data_dir():
    path = Path(os.environ.get('ROLL_COUNTER_DATA', Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'RollLiveCounter'))
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Settings:
    source: str = '0'
    confidence: float = 0.15
    scan_fps: float = 4.0
    zone: list = field(default_factory=list)
    collect: bool = False
    armed: bool = False

    @classmethod
    def load(cls, path):
        try:
            obj = json.loads(Path(path).read_text('utf-8-sig'))
            result = cls(**{k: v for k, v in obj.items() if k in cls.__dataclass_fields__})
            result.confidence = min(.9, max(.10, float(result.confidence)))
            result.scan_fps = min(10., max(.5, float(result.scan_fps)))
            if not isinstance(result.source, str):
                result.source = '0'
            if len(result.zone) != 4 or not all(isinstance(x, (int, float)) and 0 <= x <= 1 for x in result.zone):
                result.zone = []
            return result
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, path):
        path = Path(path)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), 'utf-8')
        temp.replace(path)
