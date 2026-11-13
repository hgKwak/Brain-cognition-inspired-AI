# -*- coding: utf-8 -*-
"""러너 로직을 모델 호출 없이 확인한다.   python3 bench/selftest.py

대본은 라운드별로 준다. 라운드 번호는 러너가 라운드를 시작할 때 driver.round 에
넣어 준다 — 출력에서 거꾸로 읽으면 묻는 시점보다 한 박자 늦는다.
"""
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

ep = json.loads((ROOT / "episodes/episodes.json").read_text())[0]


class Script:
    """plan[i] 가 i+1 라운드에서 낼 '전략'.
    now      지금 금지 전구를 안 켜고 지금 목표 (정답)
    rule     직전 금지만 지켜 지금 목표 — 규칙만 옛것 (forbid · rule)
    habit    직전 금지만 지켜 직전 목표 — 전환을 모르고 직전처럼 (forbid · both)
    default  규칙 없이 가장 짧은 답 — 금지 전구를 신경 쓰지 않은 답
    repeat   직전 라운드 정답을 그대로 (forbid)"""

    def __init__(self, plan):
        self.plan, self.round, self.at, self.i = plan, 1, 1, 0

    def pick(self, n, how):
        spec = ep["rounds"][n - 1]
        prev = ep["rounds"][n - 2] if n > 1 else None
        if prev is None or how == "now":
            return spec["shortest"]
        return dict(rule=spec["ruleStick"], habit=spec["habit"], default=spec["default"],
                    repeat=prev["shortest"])[how]

    def ask(self, system, messages, state):
        if self.round != self.at:
            self.at, self.i = self.round, 0
        how = self.plan[self.round - 1]
        if isinstance(how, tuple):                     # (옛전략, 몇 번, 새전략)
            old, times, new = how
            how = old if self.i < times else new
        self.i += 1
        pick = self.pick(self.round, how)
        return f"<answer>{' '.join(E.label(i) for i in pick)}</answer>", dict(stop_reason="end_turn")

    def close(self):
        pass


# 판정 단위 검사 — 손으로 만든 배선 (A 1-2-3, B 4-5-6, C 1-4-7, D 1-5-9, E 5 끄기)
K, ON, OFF = E.KEEP, E.ON, E.OFF
row = lambda on=(), off=(): [ON if c in on else OFF if c in off else K for c in range(9)]   # noqa: E731
T0 = [row(on=(0, 1, 2)), row(on=(3, 4, 5)), row(on=(0, 3, 6)), row(on=(0, 4, 8)), row(off=(4,))]
units = [   # (이름, 판정, 정답?, 짚는 전구, status)   전구와 줄은 0 부터 센 번호
    ("목표 1-2-3 · 금지 9 안 켬", E.evaluate(T0, [0], 8, [0]), True, [], "solved"),
    ("1-5-9 도 완성 · 금지 5 켬 → 5 9", E.evaluate(T0, [0], 4, [0, 3]), False, [4, 8], "both"),
    ("줄은 맞고 금지 5 를 켰다 끔 → 5", E.evaluate(T0, [0], 4, [0, 3, 4]), False, [4], "rule"),
    ("4-5-6 만 완성 → 1~6", E.evaluate(T0, [0], 8, [1]), False, [0, 1, 2, 3, 4, 5], "goal"),
    ("두 줄 목표 1-2-3 + 1-4-7", E.evaluate(T0, [0, 3], 4, [0, 2]), True, [], "solved"),
    ("빈 답 → 목표 줄 전구", E.evaluate(T0, [0], 8, []), False, [0, 1, 2], "empty"),
]
fails = [name for name, res, ok, fl, st in units
         if res["ok"] != ok or res["flagged"] != fl or res["status"] != st]
SAYS = [(E.evaluate(T0, [0], 4, [0, 3]), "Bingo lines: 1-2-3 and 1-5-9. Wrong at lights 5 9. Not the answer."),
        (E.evaluate(T0, [0], 4, [0, 3, 4]), "Bingo lines: 1-2-3. Wrong at light 5. Not the answer."),
        (E.evaluate(T0, [0], 8, [0]), "Bingo lines: 1-2-3. That is the answer."),
        (E.evaluate(T0, [0], 8, []), "Bingo lines: none. Wrong at lights 1 2 3. Not the answer.")]
fails += [f"문구: {want}" for res, want in SAYS if P.say(res) != want]
ROWS = [((E.evaluate(T0, [0], 4, [0, 3]), "rows"), "Bingo lines: 1-2-3 and 1-5-9. Wrong on lines 4-5-6 and 7-8-9. Not the answer."),
        ((E.evaluate(T0, [0], 4, [0, 3, 4]), "rows"), "Bingo lines: 1-2-3. Wrong on line 4-5-6. Not the answer."),
        ((E.evaluate(T0, [0], 4, [0, 3]), "inrows"), "Bingo lines: 1-2-3 and 1-5-9. The wrong lights are in the middle and bottom rows. Not the answer."),
        ((E.evaluate(T0, [0], 4, [0, 3, 4]), "inrows"), "Bingo lines: 1-2-3. The wrong lights are in the middle row. Not the answer.")]
fails += [f"문구({mode}): {want}" for (res, mode), want in ROWS if P.say(res, mode) != want]
print("판정 단위 검사  %s" % ("통과" if not fails else "실패: " + ", ".join(fails)))
for res, _ in SAYS:
    print("  " + P.say(res))

def second(rng):
    """1 라운드 하나와 그 다음 라운드 하나. 다음 라운드를 낳는 1 라운드 배선이 열에 하나꼴이라 여럿 본다
    (다섯 라운드를 다 만들면 문제당 20 초쯤 걸린다)."""
    for _ in range(40):
        r1 = next(x for x in (G.one_round(rng, G.random_table(rng), [], []) for _ in range(200)) if x)
        r1[0]["round"] = 1
        for _ in range(300):
            if G.one_round(rng, G.perturb(rng, r1[0]["table"])[0], [r1[0]], [r1[1]]):
                return True
    return False


print("생성기 연기 검사  %s" % ("통과" if second(random.Random(1)) else "실패"))
first = P.opening(ep["rounds"][0]["table"])
print("프롬프트 검사  %s" % ("통과" if "Lighting the right lines is not enough" in first
                          and "Here is what the buttons do:" in first and "<answer>A" not in first else "실패"))
print(f"\n{first}\n")
print(f"에피소드 {ep['id']}")
for r in ep["rounds"]:
    print(f"  R{r['round']}  목표 {' + '.join(E.NAMES[i] for i in r['goal'])}  금지 {r['forbidden'] + 1}번"
          f"   정답 {' '.join(E.label(i) for i in r['shortest'])}"
          f"   규칙 없는 최단 {' '.join(E.label(i) for i in r['default'])}"
          + (f"   습관 {' '.join(E.label(i) for i in r['habit'])}" if "habit" in r else ""))
print()
CASES = {
    "라운드마다 그 라운드 정답": ["now"] * 5,
    "지금 목표를 직전 금지만 지켜 2번 → 정답": ["now"] + [("rule", 2, "now")] * 4,
    "직전 목표를 직전 금지만 지켜 2번 → 정답": ["now"] + [("habit", 2, "now")] * 4,
    "규칙 없이 가장 짧은 답 2번 → 정답": ["now"] + [("default", 2, "now")] * 4,
    "직전 정답 그대로 2번 → 정답": ["now"] + [("repeat", 2, "now")] * 4,
}
stale = 0
for name, plan in CASES.items():
    log = R.play(Script(plan), ep, T=10, k=2, say=lambda line: None)
    for c in log["calls"]:                              # 묻는 배선 = 채점하는 배선
        stale += P.wiring(ep["rounds"][c["round"] - 1]["table"]) not in c["prompt"]
    print(f"  {name}")
    print(f"    상태 {log['status']}  제출 {[r['submissions'] for r in log['rounds']]}")
    print("    " + "  ".join(f"{R.TAGNAME[k]} {[r[k] for r in log['rounds']]}" for k in R.KINDS))
print(f"\n조건 검사 — 묻는 배선과 채점하는 배선이 다른 질문 {stale}개 " + ("(통과)" if not stale else "(실패)"))
