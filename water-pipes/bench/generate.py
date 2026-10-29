# -*- coding: utf-8 -*-
"""물길 5라운드 에피소드 — 조건 · 규칙 · 목표가 매 라운드 모두 바뀐다.
   python3 bench/generate.py [개수] [시드] [병렬 수]

  조건  판 전체(파이프 · 돌 · 꽃 배치)        매 라운드 새 판
  목표  물이 닿아야 할 꽃 색 조합              1 라운드는 모든 꽃, 그 뒤 매 라운드 변경, 숨김
  규칙  같은 타일 연속 클릭 수 (1 · 2 · 3+)    매 라운드 변경, 숨김

v1 물길(규칙만 변경)에 판 변경을 더하면 지표가 52/63/46 → 22/39/28% 로 떨어졌다. 줄어든
지속적 오류의 대부분이 '두 띠를 다 어긴 오답' 으로 옮겨 갔다 — 새 판에서 모델은 타일마다
필요한 만큼 이어 누르는데, 지금 문항에서 그런 답이 직전 띠를 지키는 전환은 19% 뿐이었다
(67% 는 두 띠를 다 어김). v1 은 판이 같아서 전에 통한 순서가 그대로 직전 띠를 지켰다.

보장 (라운드 i>=2.  pb = 직전 띠, b = 지금 띠, pg = 직전 목표, g = 지금 목표)
  · 판이 직전과 다르다. b != pb, g != pg
  · g 를 b 로 풀 수 있다 (S)
  · g 를 pb 로 풀 수 있다 (P) — 직전 띠로 지금 목표를 푸는 답이 있다
  · pg 가 이 판에서 가능하다
  · **이 판에서 pg 를 자연스럽게 푼 답이 pb 를 지킨다** — 모든 전환에 건다
      '자연스럽게' = 가장 적게 돌리는 배치를 타일마다 필요한 횟수만큼 이어 누르기.
      가장 적게 돌리는 배치가 여럿이면 전부 그래야 한다. 전환을 모르는 첫 제출
      (직전 목표를 습관대로)이 지속적 오류가 되게 하는 장치다.

띠를 1 · 2-3 · 4+ 에서 1 · 2 · 3+ 로 바꿨다. 자연스러운 답은 타일당 1~3 번이라 4+ 를 지킬 수
없어 직전 띠가 4+ 인 전환(3 분의 1)에는 장치를 걸 수 없었고, 그 라운드는 지표가 평균 7% 였다
(장치가 걸린 라운드는 42%, 첫 런 runs/20261025_1847*, 그때 문항 episodes_띠1-23-4.json).
1 · 2 · 3+ 는 셋 다 자연스러운 답이 지킬 수 있다. 대신 '2' 는 한 번에 180° 씩만 돌므로
90° · 270° 가 필요한 타일은 못 맞춘다 — 그 띠로 풀리는 (판, 목표) 만 고른다(무작위의 28%).
  띠가 서로소라 직전 띠를 지킨 답은 지금 반드시 틀린다.
  (g 를 자연스럽게 푼 답이 pb 를 지키는지는 natNew 에 남긴다 — 생성 조건은 아니다.)
"""
import itertools
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import engine as E                                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SIZE, ROUNDS, FLOWERS = 3, 5, 3
BANDS = [dict(lo=1, hi=1), dict(lo=2, hi=2), dict(lo=3, hi=None)]
ALL = frozenset(E.COLORS)
SHAPES = None


def shapes():
    global SHAPES
    if SHAPES is None:
        SHAPES = [E.U | E.D, E.R | E.L, E.U | E.R, E.U | E.L, E.D | E.R, E.D | E.L,
                  E.U | E.R | E.D, E.U | E.R | E.L, E.U | E.D | E.L, E.R | E.D | E.L]
    return SHAPES


def random_board(rng):
    n = SIZE
    kinds = [E.PIPE] * (n * n)
    k = 1 + FLOWERS + (1 if rng.random() < 0.35 else 0)
    spots = rng.sample(range(n * n), k)
    kinds[spots[0]] = E.SOURCE
    colors = list(E.COLORS)
    rng.shuffle(colors)
    flower_color = {}
    for i in range(FLOWERS):
        kinds[spots[1 + i]] = E.FLOWER
        flower_color[spots[1 + i]] = colors[i]
    if k > 1 + FLOWERS:
        kinds[spots[-1]] = E.STONE
    tiles = []
    for i, kind in enumerate(kinds):
        if kind == E.PIPE:
            t = dict(kind=kind, mask=rng.choice(shapes()))
        elif kind == E.STONE:
            t = dict(kind=kind, mask=0)
        else:
            t = dict(kind=kind, mask=rng.choice([E.U, E.R, E.D, E.L]))
            if kind == E.FLOWER:
                t["color"] = flower_color[i]
        tiles.append(t)
    return dict(size=n, tiles=tiles)


def natural(turn_lists):
    """가장 적게 돌리는 배치들의 자연스러운 답이 지키는 띠의 번호. 하나로 정해지지 않으면 None."""
    best = min(sum(t.values()) for t in turn_lists)
    out = set()
    for t in turn_lists:
        if sum(t.values()) != best:
            continue
        rs = [r for r in t.values() if r]
        hit = [k for k, b in enumerate(BANDS)
               if rs and all(b["lo"] <= r and (b["hi"] is None or r <= b["hi"]) for r in rs)]
        out.add(hit[0] if hit else None)
    return out.pop() if len(out) == 1 else None


def study(board):
    """한 판에서 쓸 수 있는 (목표, 띠) 와 목표마다 자연스러운 답의 띠."""
    if not E.maybe_solvable(board):
        return None
    table, nat = {}, {}
    for goal, turns in E.assignments(board).items():
        if not goal:
            continue
        for b, rule in enumerate(BANDS):
            for t in turns[:60]:
                seq = E.sequence_for(board, t, rule)
                if seq and E.evaluate(board, seq, goal, rule)["ok"]:
                    table.setdefault(goal, {})[b] = seq
                    break
        if goal in table:
            nat[goal] = natural(turns)
    if ALL not in table or len(table) < 4:
        return None
    return table, nat


def collect(args):
    """판 묶음 하나를 모은다. 묶음마다 씨앗이 정해져 있어 재현된다."""
    want, seed = args
    rng = random.Random(seed)
    out, tries = [], 0
    while len(out) < want and tries < want * 3000:
        tries += 1
        board = random_board(rng)
        got = study(board)
        if got:
            table, nat = got
            out.append(dict(board=board,
                            table={",".join(sorted(g)): v for g, v in table.items()},
                            nat={",".join(sorted(g)): v for g, v in nat.items()}))
    return out


def key(goal):
    return ",".join(sorted(goal))


def one_round(rng, prev, pool, tries=400):
    for _ in range(tries):
        bi = rng.randrange(len(pool))
        P = pool[bi]
        table, nat = P["table"], P["nat"]
        if prev is None:
            bands = sorted(int(b) for b in table[key(ALL)])
            b = rng.choice(bands)
            return dict(board=P["board"], goal=sorted(ALL), band=b, rule=BANDS[b],
                        shortest=table[key(ALL)][b],
                        r1Natural=nat.get(key(ALL)), _bi=bi)
        if bi == prev["_bi"]:
            continue
        pb, pg = prev["band"], key(prev["goal"])
        if pg not in table:
            continue
        if nat.get(pg) != pb:
            continue                                   # 직전 목표를 습관대로 풀면 직전 띠를 지켜야 한다
        b = rng.choice([x for x in range(3) if x != pb])
        cands = [g for g, v in table.items() if g != pg and b in v and pb in v]
        if not cands:
            continue
        g = rng.choice(sorted(cands))
        return dict(board=P["board"], goal=g.split(","), band=b, rule=BANDS[b],
                    shortest=table[g][b], ruleStick=table[g][pb],
                    natNew=nat.get(g) == pb, _bi=bi)
    return None


def make(idx, rng, pool):
    rounds, prev = [], None
    for n in range(1, ROUNDS + 1):
        r = one_round(rng, prev, pool)
        if r is None:
            return None
        r["round"] = n
        rounds.append(r)
        prev = r
    for r in rounds:
        r.pop("_bi", None)
    return dict(id=f"W{idx + 1:03d}", size=SIZE, rounds=rounds)


def main(count=300, seed=20261025, jobs=8, boards=480):
    from multiprocessing import Pool
    with Pool(jobs) as pp:
        parts = pp.map(collect, [(boards // jobs, seed * 100 + j) for j in range(jobs)])
    pool = [b for part in parts for b in part]
    for P in pool:                                     # json 이 아니니 띠 키는 정수로
        P["table"] = {g: {int(b): s for b, s in v.items()} for g, v in P["table"].items()}
    print(f"쓸 수 있는 판 {len(pool)} 개", flush=True)
    rng = random.Random(seed)
    eps, tries = [], 0
    while len(eps) < count and tries < count * 50:
        tries += 1
        e = make(len(eps), rng, pool)
        if e:
            eps.append(e)
    (ROOT / "episodes").mkdir(exist_ok=True)
    (ROOT / "episodes/episodes.json").write_text(json.dumps(eps, ensure_ascii=False, indent=1))
    rs = [r for e in eps for r in e["rounds"]]
    print(f"에피소드 {len(eps)}/{count}  시도 {tries}")
    print(f"  띠 {dict(sorted(Counter(E.rule_name(r['rule']) for r in rs).items()))}")
    print(f"  목표 꽃 수 {dict(sorted(Counter(len(r['goal']) for r in rs).items()))}")
    print(f"  새 목표를 습관대로 풀어도 직전 띠 {sum(r.get('natNew', False) for r in rs)}"
          f"/{sum(1 for r in rs if r['round'] > 1)}")
    print(f"  1 라운드를 자연스럽게 풀면 그 띠를 지킴 "
          f"{sum(1 for e in eps if e['rounds'][0]['r1Natural'] == e['rounds'][0]['band'])}/{len(eps)}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if a else 300, int(a[1]) if len(a) > 1 else 20261025,
         int(a[2]) if len(a) > 2 else 8)
