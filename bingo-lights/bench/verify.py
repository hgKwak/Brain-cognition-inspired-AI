# -*- coding: utf-8 -*-
"""생성된 에피소드가 보장 조건을 지키는지 본다.   python3 bench/verify.py

생성기의 판단을 다시 쓰지 않고 engine 으로 처음부터 센다."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import engine as E                                    # noqa: E402
from generate import CHANGE, COUPLE, change           # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
eps = json.loads((ROOT / "episodes/episodes.json").read_text())
SEQS = E.sequences(5, 4)
bad, chk, kinds = [], Counter(), Counter()
R = n = n2 = 0


def exact(t, goal):
    return [p for p in SEQS if E.lines(E.run(t, p)) == list(goal)]


def blocked(t, goal, old):
    """옛 금지를 지키면 못 하는 끝 판 고치기 — generate.blocked 를 engine 으로 다시 센다."""
    want = E.need(goal)
    seen, kept = set(), set()
    for p in exact(t, goal):
        end = E.run(t, p)
        pairs = {(c, end[c]) for c in range(9) if c not in want and c != old}
        seen |= pairs
        if not E.touches(t, p, old):
            kept |= pairs
    return seen - kept


def shortest(ps):
    m = min(len(p) for p in ps)
    return [p for p in ps if len(p) == m]


for e in eps:
    if len(e["rounds"]) != 5:
        bad.append(f"{e['id']} 라운드 수")
    sols = []
    for i, r in enumerate(e["rounds"]):
        R += 1
        tag = f"{e['id']} R{r['round']}"

        def ok(name, cond, why):
            if cond:
                chk[name] += 1
            else:
                bad.append(f"{tag} {why}")

        t, g, L = r["table"], r["goal"], r["forbidden"]
        now = exact(t, g)
        S = {p for p in now if not E.touches(t, p, L)}
        sols.append(S)
        dflt = shortest(now)
        ok("정답이 통함", E.evaluate(t, g, L, r["shortest"])["ok"], "정답이 안 통함")
        ok("정답 3번 이하", len(r["shortest"]) <= 3, "정답이 4번 이상")
        ok("목표는 한두 줄", len(g) in (1, 2), "목표 줄이 한두 개가 아님")
        ok("금지 전구는 목표 줄 밖", L not in E.need(g), "금지 전구가 목표 줄 위에 있음")
        if not i:
            ok("기본 최단은 모두 금지 전구를 켬", all(E.touches(t, p, L) for p in dflt),
               "규칙 없이 가장 짧은 답 중 금지 전구를 안 켜는 것이 있음")
            continue
        n += 1
        p = e["rounds"][i - 1]
        Lp = p["forbidden"]
        diff = sum(a != b for ra, rb in zip(t, p["table"]) for a, b in zip(ra, rb))
        ok("조건 변경(배선 네 칸)", diff == CHANGE, f"배선이 {diff} 칸 바뀜")
        ok("규칙 변경", L != Lp, "금지 전구가 직전과 같음")
        if i >= 2:
            n2 += 1
            ok("두 라운드 전 금지와도 다름", L != e["rounds"][i - 2]["forbidden"], "두 라운드 전 금지 전구로 돌아감")
            ok("두 라운드 전 정답은 지금 틀림", not (S & sols[i - 2]), "두 라운드 전 정답이 지금도 맞음")
        ok("목표 변경", g != p["goal"], "목표가 직전과 같음")
        kinds[change(g, p["goal"])] += 1
        ok("바뀌는 방식이 뺌 · 더함 중 하나", change(g, p["goal"]) in ("뺌", "더함"), "목표가 뺌 · 더함이 아닌 방식으로 바뀜")
        ok("직전 금지는 목표 줄 밖", Lp not in E.need(g), "직전 금지 전구가 지금 목표 줄 위에 있음")
        ok("직전 정답은 지금 틀림", not (S & sols[i - 1]), "직전 라운드 정답이 지금도 맞음")
        ok("둘 다 피하면 줄 0", not any(E.lines(E.run(t, q)) for q in SEQS
                                    if not E.touches(t, q, Lp) and not E.touches(t, q, L)),
           "직전 · 지금 금지를 둘 다 피하고도 줄을 만들 수 있음")
        rs = r["ruleStick"]
        ok("직전 금지만 지켜 지금 목표 → 틀림", E.lines(E.run(t, rs)) == g and not E.touches(t, rs, Lp)
           and E.touches(t, rs, L), "규칙만 옛것인 답이 없거나 지금 금지를 안 켬")
        hb = r["habit"]
        ok("직전 목표를 직전 금지만 지켜 → 지속적 오류", E.lines(E.run(t, hb)) == p["goal"]
           and not E.touches(t, hb, Lp) and E.touches(t, hb, L) and len(hb) <= 3, "습관대로 푼 답이 없음")
        rep = p["shortest"]
        ok("직전 정답 그대로 → 지속적 오류", not E.touches(t, rep, Lp) and E.touches(t, rep, L),
           "직전 정답을 그대로 내도 지속적 오류가 아님")
        ok("기본 최단은 모두 직전 금지 전구를 켬", all(E.touches(t, q, Lp) for q in dflt),
           "규칙 없이 가장 짧은 답 중 직전 금지 전구를 안 켜는 것이 있음")
        ok("직전 금지를 켜는 버튼 둘 이상", len(E.lighting(t, Lp)) >= 2, "직전 금지 전구를 켜는 버튼이 하나뿐")
        ok("옛 금지를 지켜도 끝 판 고치기 가능", not blocked(t, g, Lp), "옛 금지를 지키면 못 하는 끝 판 고치기가 있음")
        # 어느줄4 에서 더한 보장 (generate.py 머리말 2 · 3 · 4 · 5)
        ok("기본 최단은 모두 지금 금지 전구를 안 켬", not any(E.touches(t, q, L) for q in dflt),
           "규칙 없이 가장 짧은 답 중 지금 금지 전구를 켜는 것이 있음")
        old = [q for q in exact(t, p["goal"]) if len(q) <= 3]
        ok("옛 목표 답 절반 이상이 옛 금지를 피함", bool(old) and sum(not E.touches(t, q, Lp) for q in old) >= COUPLE * len(old),
           "새 배선에서 옛 목표를 만드는 3 번 이하 답 가운데 옛 금지 전구를 피하는 것이 절반 미만")
        habit = [q for q in old if not E.touches(t, q, Lp)]          # 습관 답 가운데 가장 짧은 것과 직전 정답
        first = (shortest(habit) if habit else []) + ([tuple(rep)] if len(rep) <= 3 else [])
        prevS = [q for q in exact(p["table"], p["goal"]) if len(q) <= 3 and not E.touches(p["table"], q, Lp)]
        ok("직전 정답 무엇을 되풀이해도 지속적 오류", all(not E.touches(t, q, Lp) and E.touches(t, q, L) for q in prevS),
           "직전 라운드 정답 가운데 되풀이하면 지속적 오류가 아닌 것이 있음")
        ok("첫 제출이 꺼진 목표 전구를 켰다 끄지 않음",
           not any(E.touches(t, q, c) and not E.run(t, q)[c] for q in first for c in E.need(g)),
           "첫 제출 후보가 끝에 꺼진 목표 전구를 누르는 도중 켬")

print(f"에피소드 {len(eps)} · 라운드 {R} · 전환 {n}")
for k in ("정답이 통함", "정답 3번 이하", "목표는 한두 줄", "금지 전구는 목표 줄 밖"):
    print(f"  {k:30} {chk[k]}/{R}" + ("" if chk[k] == R else "   ← 어긋남"))
k = "기본 최단은 모두 금지 전구를 켬"
print(f"  {k + ' (1 라운드)':30} {chk[k]}/{len(eps)}" + ("" if chk[k] == len(eps) else "   ← 어긋남"))
for k in ("조건 변경(배선 네 칸)", "규칙 변경", "목표 변경", "직전 금지는 목표 줄 밖", "직전 정답은 지금 틀림",
          "둘 다 피하면 줄 0", "직전 금지만 지켜 지금 목표 → 틀림", "직전 목표를 직전 금지만 지켜 → 지속적 오류",
          "직전 정답 그대로 → 지속적 오류", "기본 최단은 모두 직전 금지 전구를 켬", "직전 금지를 켜는 버튼 둘 이상",
          "옛 금지를 지켜도 끝 판 고치기 가능", "바뀌는 방식이 뺌 · 더함 중 하나",
          "기본 최단은 모두 지금 금지 전구를 안 켬", "옛 목표 답 절반 이상이 옛 금지를 피함",
          "첫 제출이 꺼진 목표 전구를 켰다 끄지 않음", "직전 정답 무엇을 되풀이해도 지속적 오류"):
    print(f"  {k:30} {chk[k]}/{n}" + ("" if chk[k] == n else "   ← 어긋남"))
for k in ("두 라운드 전 금지와도 다름", "두 라운드 전 정답은 지금 틀림"):
    print(f"  {k:30} {chk[k]}/{n2}" + ("" if chk[k] == n2 else "   ← 어긋남"))
print(f"  바뀌는 방식 {dict(kinds)}")
print("  문제 없음" if not bad else "  " + "\n  ".join(bad[:20]))
