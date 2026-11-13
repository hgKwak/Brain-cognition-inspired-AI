# -*- coding: utf-8 -*-
"""run 폴더의 로그에서 지표를 다시 계산한다.   python3 bench/score.py [runs/...]

러너 안의 집계를 믿지 않고 calls 를 되짚는다.

지속적 오류율 — 세 층 평균 (2026-10-21 확정)
    라운드_i = a_i / n_i            a_i 지속적 오류 수, n_i 그 라운드의 제출 수
    문제_e   = (Σ 라운드_i) / 라운드 수
    전체     = (Σ 문제_e) / 문제 수
라운드마다 들어간 문제 수가 달라, 라운드별 표를 어떻게 가중해도 전체 값이 나오지
않는다. 라운드별은 내역으로만 쓴다.

집계 대상은 라운드 2 부터 **처음 못 푼 라운드까지**(그 라운드 포함). 러너가 거기서
에피소드를 끝내므로 그 뒤 라운드는 애초에 없다.

a_i 를 무엇으로 셀지는 네 가지를 다 뽑는다 — rule / goal / both / repeat.
기본은 **rule**(지금 목표를 직전 규칙으로 달성)이다.
"""
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import engine as E                                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EPS = {e["id"]: e for e in json.loads((ROOT / "episodes/episodes.json").read_text())}
KINDS = ("band", "rule", "goal", "both", "repeat")


def score(log, kind="rule", cap=None):
    """라운드별 기록. kind 로 지속적 오류의 정의를 고른다."""
    ep = EPS[log["episode"]]
    calls = {}
    for c in log["calls"]:
        calls.setdefault(c["round"], []).append(c)
    out = []
    for i, r in enumerate(log["rounds"]):
        cs = calls.get(r["round"], [])
        if i and cap:
            cs = cs[:cap]
        # 분모는 **채점된 제출**(읽을 수 있었던 것)만 센다. 읽을 수 없는 응답에서는
        # 분자가 나올 수 없으므로 분모에 넣으면 지표가 그만큼 낮게 나온다.
        scored = [c for c in cs if c.get("clicks") is not None]
        a = wrong = 0
        for c in scored:
            if c.get("correct"):
                continue
            wrong += 1
            if i and c.get(kind):
                a += 1
        out.append(dict(round=r["round"], submissions=len(scored) or r["submissions"],
                        solved=r["solved"], unparsed=r["unparsed"], wrong=wrong,
                        perseverative=a,
                        rate=(a / len(scored) if scored else 0.0),
                        counted=bool(i)))
    return out


def per_episode(rec):
    """문제 하나의 지속적 오류율. 집계 라운드의 단순평균."""
    v = [x["rate"] for x in rec if x["counted"]]
    return statistics.mean(v) if v else None


def main(folder):
    folder = Path(folder)
    index = json.loads((folder / "index.json").read_text())
    logs = [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))
            if p.name != "index.json"]
    n = len(index["episodes"])
    print(f"{index['model']}  T={index['T']} T1={index.get('T1')} k={index['k']}"
          f"  에피소드 {len(logs)}/{n}" + ("  (진행 중)" if len(logs) < n else ""))
    if not logs:
        return
    print(f"  상태 {dict(Counter(l['status'] for l in logs))}")
    r1 = [l["rounds"][0] for l in logs]
    print(f"\n  라운드 1  해결 {sum(x['solved'] for x in r1)}/{len(r1)}"
          f"  제출 중앙값 {statistics.median([x['submissions'] for x in r1])}")
    stop = Counter(max((x["round"] for x in l["rounds"] if x["round"] > 1), default=0)
                   for l in logs)
    print(f"  집계가 끊긴 라운드 " + "  ".join(f"R{m}={stop.get(m, 0)}" for m in range(0, 6))
          + f"   다섯 라운드 완주 {sum(all(x['solved'] for x in l['rounds']) for l in logs)}"
            f"/{len(logs)}")
    print()
    # 지표는 하나다 — 직전 라운드라면 정답이었을 제출 ÷ 그 라운드 제출 수.
    # 나머지 깃발은 로그(calls)에 남아 있으니 필요할 때 따로 뽑는다.
    for kind in ("band", "rule"):   # band = 지표(규칙으로만), rule = v1 물길 정의
        rows = [score(l, kind) for l in logs]
        eps = [v for v in (per_episode(r) for r in rows) if v is not None]
        if not eps:
            continue
        byr = {m: [x["rate"] for r in rows for x in r
                   if x["round"] == m and x["counted"]] for m in (2, 3, 4, 5)}
        print(f"  {kind:<7} {statistics.mean(eps):6.1%}  (문제 {len(eps)}개)   "
              + "  ".join(f"R{m}=" + (f"{statistics.mean(v):.0%}({len(v)})" if v else "—")
                          for m, v in byr.items()))
    bad = sum(x["unparsed"] for l in logs for x in l["rounds"])
    sub = sum(x["submissions"] for l in logs for x in l["rounds"])
    print(f"\n  읽을 수 없는 응답 {bad}/{sub} ({bad / sub:.1%})")


if __name__ == "__main__":
    for f in sys.argv[1:] or sorted(Path("runs").glob("*")):
        main(f); print()
