# -*- coding: utf-8 -*-
"""러너 로직을 모델 호출 없이 확인한다.   python3 bench/selftest.py"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))
import engine as E                                    # noqa: E402
import generate as G                                  # noqa: E402
import prompt as P                                    # noqa: E402
import runner as R                                    # noqa: E402

eps = json.loads((ROOT / "episodes/episodes.json").read_text())
ep = eps[0]


def habit(board, goal):
    """가장 적게 돌리는 배치를 타일마다 필요한 횟수만큼 이어 누른 답."""
    turns = E.assignments(board).get(frozenset(goal), [])
    best = min(turns, key=lambda t: (sum(t.values()), sorted(t.items())))
    return [i for i in sorted(best) for _ in range(best[i])]


class Script:
    """plan[i] 가 i+1 라운드에서 낼 '전략'.
    now    지금 목표·지금 띠의 정답
    old    직전 띠로 지금 목표를 푼 답 (band · rule)
    habit  직전 목표를 습관대로(이어 누르기) 푼 답 — 전환을 모르는 첫 제출 (band · both)
    repeat 직전 라운드 정답을 그대로"""

    def __init__(self, plan):
        self.plan, self.round, self.at, self.i, self.last = plan, 1, 1, 0, None

    def pick(self, n, how):
        spec = ep["rounds"][n - 1]
        prev = ep["rounds"][n - 2] if n > 1 else None
        if how == "old" and prev:
            return spec["ruleStick"]
        if how == "habit" and prev:
            return habit(spec["board"], prev["goal"])
        if how == "repeat" and prev:
            return prev["shortest"]
        return spec["shortest"]

    def ask(self, system, messages, state):
        if self.round != self.at:
            self.at, self.i = self.round, 0
        how = self.plan[self.round - 1]
        if isinstance(how, tuple):
            old, times, new = how
            how = old if self.i < times else new
        self.i += 1
        q = self.pick(self.round, how)
        return f"<answer>{' '.join(str(i + 1) for i in q)}</answer>", dict(stop_reason="end_turn")

    def close(self):
        pass


smoke = G.study(G.random_board(random.Random(3)))
print("판 연구 함수  %s" % ("통과" if smoke is None or len(smoke) == 2 else "실패"))
first = P.opening(ep["rounds"][0]["board"])
print("프롬프트 검사  %s\n" % ("통과" if "[Fr] [Fy] [Fb]" in first and "the right flowers" in first else "실패"))
print(first, "\n")
print(f"에피소드 {ep['id']}")
for r in ep["rounds"]:
    print(f"  R{r['round']}  목표 {','.join(r['goal']):18} 띠 {E.rule_name(r['rule']):4}"
          f"  최단 {' '.join(str(i + 1) for i in r['shortest'])}")
print()
CASES = {
    "라운드마다 그 라운드 정답": ["now"] * 5,
    "직전 띠로 지금 목표 2번 → 정답": ["now"] + [("old", 2, "now")] * 4,
    "직전 목표를 습관대로 2번 → 정답": ["now"] + [("habit", 2, "now")] * 4,
    "직전 정답 그대로 2번 → 정답": ["now"] + [("repeat", 2, "now")] * 4,
}
stale = 0
for name, plan in CASES.items():
    log = R.play(Script(plan), ep, T=10, k=2, say=lambda line: None)
    for c in log["calls"]:                              # 묻는 판 = 채점하는 판
        stale += E.text(ep["rounds"][c["round"] - 1]["board"]) not in c["prompt"]
    print(f"  {name}")
    print(f"    상태 {log['status']}  제출 {[r['submissions'] for r in log['rounds']]}")
    print("    " + "  ".join(f"{R.TAGNAME[k]} {[r[k] for r in log['rounds']]}" for k in R.KINDS))
print(f"\n판 검사 — 묻는 판과 채점하는 판이 다른 질문 {stale}개 " + ("(통과)" if not stale else "(실패)"))
