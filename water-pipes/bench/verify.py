# -*- coding: utf-8 -*-
"""생성된 에피소드가 보장 조건을 지키는지 본다.   python3 bench/verify.py

생성기의 판단을 다시 쓰지 않고 engine 으로 처음부터 센다."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import engine as E                                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
eps = json.loads((ROOT / "episodes/episodes.json").read_text())
ALL = frozenset(E.COLORS)
bad = []
chk = Counter(); R = n = nat_n = 0


def natural_band(board, goal):
    """가장 적게 돌리는 배치들을 이어 누른 답이 지키는 띠의 이름. 없으면 None."""
    turns = E.assignments(board).get(frozenset(goal), [])
    if not turns:
        return None
    best = min(sum(t.values()) for t in turns)
    names = set()
    for t in turns:
        if sum(t.values()) != best:
            continue
        q = [i for i in sorted(t) for _ in range(t[i])]
        ok = [E.rule_name(r) for r in (dict(lo=1, hi=1), dict(lo=2, hi=2), dict(lo=3, hi=None))
              if q and not any(E.violations(board, q, r))]
        names.add(ok[0] if ok else None)
    return names.pop() if len(names) == 1 else None


for e in eps:
    if len(e["rounds"]) != 5:
        bad.append(f"{e['id']} 라운드 수")
    for i, r in enumerate(e["rounds"]):
        R += 1
        tag = f"{e['id']} R{r['round']}"

        def ok(name, cond, why):
            if cond:
                chk[name] += 1
            else:
                bad.append(f"{tag} {why}")

        board, goal, rule = r["board"], frozenset(r["goal"]), r["rule"]
        ok("최단이 통함", E.evaluate(board, r["shortest"], goal, rule)["ok"], "최단이 안 통함")
        if not i:
            ok("1R 목표는 모든 꽃", goal == ALL, "1 라운드 목표가 모든 꽃이 아님")
            continue
        n += 1
        p = e["rounds"][i - 1]
        ok("판 변경", board != p["board"], "판이 직전과 같음")
        ok("규칙 변경", rule != p["rule"], "띠가 직전과 같음")
        ok("목표 변경", goal != frozenset(p["goal"]), "목표가 직전과 같음")
        ok("직전 띠로 지금 목표를 풂(P)", E.evaluate(board, r["ruleStick"], goal, p["rule"])["ok"],
           "직전 띠 답이 지금 목표를 못 풂")
        ok("직전 띠 답은 지금 틀림", not E.evaluate(board, r["ruleStick"], goal, rule)["ok"],
           "직전 띠 답이 지금도 맞음")
        ok("직전 목표가 이 판에서 가능", frozenset(p["goal"]) in E.assignments(board), "직전 목표가 이 판에서 불가능")
        nat_n += 1
        ok("직전 목표를 습관대로 → 직전 띠", natural_band(board, p["goal"]) == E.rule_name(p["rule"]),
           "직전 목표의 자연스러운 답이 직전 띠를 안 지킴")

print(f"에피소드 {len(eps)} · 라운드 {R} · 전환 {n}")
for k in ("최단이 통함",):
    print(f"  {k:24} {chk[k]}/{R}" + ("" if chk[k] == R else "   ← 어긋남"))
print(f"  {'1R 목표는 모든 꽃':24} {chk['1R 목표는 모든 꽃']}/{len(eps)}"
      + ("" if chk["1R 목표는 모든 꽃"] == len(eps) else "   ← 어긋남"))
for k in ("판 변경", "규칙 변경", "목표 변경", "직전 띠로 지금 목표를 풂(P)", "직전 띠 답은 지금 틀림",
          "직전 목표가 이 판에서 가능"):
    print(f"  {k:24} {chk[k]}/{n}" + ("" if chk[k] == n else "   ← 어긋남"))
k = "직전 목표를 습관대로 → 직전 띠"
print(f"  {k:24} {chk[k]}/{nat_n}" + ("" if chk[k] == nat_n else "   ← 어긋남"))
print("  문제 없음" if not bad else "  " + "\n  ".join(bad[:20]))
