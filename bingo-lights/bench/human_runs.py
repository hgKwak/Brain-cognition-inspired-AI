# -*- coding: utf-8 -*-
"""사람 결과 파일을 run 폴더로 옮긴다.   python3 bench/human_runs.py 전구_사람_이름.json

`human/bingo-lights.html` 에서 내려받은 결과를 모델 런과 같은 꼴(`runs/<폴더>/index.json` + 문제마다 로그)로 펼친다. 결과의
config.version 이 가리키는 버전 폴더(페이지를 만든 폴더)에 쓰므로, 그 버전의 `bench/score.py runs/<폴더>` 로 모델과
똑같이 채점된다. 폴더 이름과 로그에 참가자 이름이 들어가므로 `runs/human_*` 는 git 에 올리지 않는다(.gitignore).
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

V2 = Path(__file__).resolve().parent.parent.parent              # 저장소 맨 위 — 과제 폴더들이 이 아래에 있다

for path in sys.argv[1:]:
    got = json.loads(Path(path).read_text())
    cfg, sessions = got["config"], got["sessions"]
    root = V2 / cfg.get("version", "bingo-lights")
    who = re.sub(r"[^\w가-힣-]+", "_", got["name"]).strip("_") or "anon"
    stamp = (datetime.fromisoformat(got["finishedAt"].replace("Z", "+00:00"))       # 모델 런처럼 한국 시각
             .astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S"))
    out = root / "runs" / f"human_{who}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.json").write_text(json.dumps(
        dict(model=f"human:{got['name']}", T=cfg["T"], T1=cfg["T"], k=cfg["k"],
             episodes=[s["episode"] for s in sessions],
             settings=dict(provider="human", seed=cfg.get("seed"), sample=cfg.get("sample"))),
        ensure_ascii=False, indent=1))
    for s in sessions:
        s.setdefault("status", "unfinished")          # 중간에 내려받은 마지막 문제
        (out / f"human_{s['episode']}.json").write_text(json.dumps(s, ensure_ascii=False, indent=1))
    print(f"{out}  문제 {len(sessions)} 개")
