# -*- coding: utf-8 -*-
"""3×3 빙고 전구 5라운드 에피소드 — 목표는 어느 줄, 규칙은 금지 전구.   python3 bench/generate.py [개수] [시드] [병렬 수]

`전구-빙고-어느줄3` 과 판 · 판정 · 글이 같고 전환 라운드 보장 다섯을 더했다(사용자: "만들어", 2026-10-28). 배선은
매 라운드 **네 칸** 바뀐다(어느줄3 은 두 칸).
어느줄3 S001~S100 에서 Claude 는 37.9 · 37.8% 였는데, 옛 규칙을 전혀 붙들지 않는 가상 모델(첫 제출은 직전 정답,
그 뒤엔 새 목표의 가장 짧은 답)도 32% 를 받는다 — 전환을 모르는 첫 제출은 누가 내도 지속적 오류라서다. 습관 몫은
5~6%p 뿐이었다. 그 런에서 아래 넷을 이미 만족한 라운드는 Opus 44.8 · Sonnet 43.5 · GPT 52.0%(35 · 37 · 26 라운드),
하나도 만족하지 않는 라운드는 36.8 · 35.7 · 41.7% 였다. 열 갈래 넘게 나눠 본 뒤 고른 조합이라 실제 효과는 더 작을
수 있다 — 파일럿으로 확인한다.

  1  목표 변화는 뺌 · 더함만 (한 줄 공유를 뺌)    공유 라운드가 가장 낮았다(Opus 36.7 · Sonnet 36.4%)
  2  규칙 없이 가장 짧은 T 답은 모두 L 을 안 켠다  옛 규칙을 버린 모델은 바로 정답이 된다. 자연스러운 답이 새 금지
                                                   전구까지 켜면 옛 · 새 금지를 다 켠 오답(지속적 오류 아님)이 늘었다
                                                   (그런 라운드 Opus 35.5 · Sonnet 32.4%)
  3  첫 제출(가장 짧은 습관 답과 직전 정답)은    더해진 줄의 전구가 첫 제출 도중 켜졌다 꺼지면 금지 전구와 똑같이
     끝에 꺼진 T 전구를 누르는 도중 켜지 않는다    짚혀, Claude 가 그 전구를 피하고 옛 목표를 다시 만들었다("the flags
                                                   are probably about history rather than lines")
  4  새 배선에서 T' 를 만드는 3 번 이하 답의      물길의 '옛 목표의 자연스러운 답이 옛 띠를 따름' 과 같은 장치. 옛
     절반 이상이 L' 을 안 켠다                     목표를 다시 노리면 L' 은 피하고(줄 0 보장 때문에) L 을 켜 지속적
                                                   오류가 된다 — 옛 목표를 붙드는 것도 지속적 오류로 잡힌다
  5  직전 라운드의 정답(3 번 이하) 어느 것을     전환 첫 제출의 83~88% 는 직전 라운드 마지막 정답을 그대로 낸 것이다.
     되풀이해도 L' 은 안 켜고 L 을 켠다            두 칸 변화에서는 그 답이 새 배선에서도 L' 을 피했다(98~99%). 배선을
                                                   네 칸 바꾸므로 이것을 보장으로 옮겼다
2 때문에 습관 없는 가상 모델은 모든 전환에서 지속적 오류 하나 + 정답 둘(33%)이다. 바닥은 그대로 두고 습관 몫만
키운다. 문제 번호는 Q001~(어느줄3 은 S).

배선을 두 칸만 바꾸던 것은 `전구-시작버튼` · `전구-빙고` 의 버튼 규칙 때문이었다 — 배선을 새로 그리면 버튼이
옛 버튼과 이어지지 않아 버튼 규칙이 넘어가지 않았다. 금지 '전구' 는 자리가 고정이라 그 이유가 없다(사용자 지적).
두 칸으로는 4 를 건 문제가 나오지 않았다 — 배선 섭동 대비 통과율 R2 0.011% · R3 0.005% · R4 0.0006% · R5 0%
(2 만 4 천 번 중 0), 몫 하한 1/3 에서도 R4 에서 끊김. 8 코어 80 초 시험에서 세 칸은 0 문제, 네 칸은 3 문제(문제당 CPU
약 210 초), 매번 새로 그리면 5 때문에 0 문제였다. Q001~Q030 은 8 코어 42 분(문제당 CPU 약 490 초, 오래 걸린 문제가
뒤를 끌었다), `bench/verify.py` 전부 통과. 습관 없는 가상 모델 33.3%(120 전환 모두 PCC), 우연(버튼 1 · 2 · 3 개)
28 · 24 · 10% 로 어느줄3 과 같고, 새 배선에서 옛 목표 답이 옛 금지를 피하는 몫은 평균 0.67(어느줄3 0.37).

주의 — 어느줄3 런에서 4 를 만족한 라운드에 늘어난 지속적 오류의 절반은 '옛 목표를 다시 만듦' 이고 절반은 '새 금지
전구를 지나는 줄'(새 금지 전구를 켜야 할 전구로 잘못 읽고 노린 줄로 가는 길이 마침 옛 금지를 피한 것)이었다. 뒤의
것은 습관이라 보기 어렵다 — 파일럿에서 지속적 오류를 이 둘로 나눠 본다.

아래는 어느줄3 의 머리말이다. 어느줄3 은 `전구-빙고-어느줄2` 와 판 · 판정 · 글 · 보장이 같고, **목표가 바뀌는 방식** 하나만 정했다 — 하나 뺌(두 줄 →
한 줄) · 하나 더함(한 줄 → 두 줄) · 한 줄만 공유(두 줄 중 한 줄을 바꿈)를 1/3 씩. 겹치는 줄이 없는 변화는 없다.
어느줄 · 어느줄2 첫 런에서 바뀌는 방식별 지속적 오류율이 겹침 없음 35%(79 전환) · 뺌 37%(63) · 더함 41%(50) ·
한 줄 공유 47%(11) 였다. 셋을 고르게 섞으면 약 42% 를 기대한다(한 줄 공유가 더함 수준이면 40%).
문제마다 목표 줄 수와 바뀌는 방식을 먼저 정한다(plan). 한 줄에서는 '더함' 뿐이고 두 줄에서는 '뺌' · '한 줄
공유' 를 반씩 고르며, 1 라운드를 한 줄 1/3 · 두 줄 2/3 로 뽑으면 세 방식이 1/3 씩 나온다. 계획은 문제 번호마다
한 번 뽑고 다시 찾을 때도 바꾸지 않는다 — 바꾸면 찾기 쉬운 계획만 남아 '뺌' 으로 쏠린다.

아래는 어느줄2 의 머리말이다. 어느줄2 는 `전구-빙고-어느줄` 과 판 · 판정 · 글이 같고, 생성 보장 하나(아래 '옛
금지를 지켜도 끝 판 고치기가 막히지 않는다')만 더했다. 어느줄 첫 파일럿에서 줄은 맞고 새 금지 전구만 짚힌 오답 17 개 중 11 개가 한 전환(L001 R2)
에서 나왔다. 그 판은 1-2-3 줄을 끊으려 2 번을 끄려면 옛 금지 전구 8 번을 켜는 A 를 눌러야 했고, 세 모델
모두 거기서 옛 규칙을 버렸다 — Sonnet: "Getting 2 off requires A, so this brief lighting can't be avoided,
and my earlier idea that 8 must never be lit does not seem to apply here." 그 뒤 실패는 지속적 오류로
잡히지 않는다. 어느줄 첫 런 19 문제(전환 65 개)에서 이 성질이 있는 전환은 지속적 오류율 46%(20 개), 고치기가
하나라도 막힌 전환은 30~33%(막힘 1 개 30% · 2 개 32% · 3 개 이상 33%)였다. 물길에는 이 보장이 없다 — 띠 '2'
는 180° 씩만 돌아 90° · 270° 가 필요한 타일을 못 고치고, 물길이 거는 것은 '직전 띠로도 지금 목표를 푸는
답이 있다'(여기의 P)까지다. 어느줄 문제에서는 전환의 21% 만 이 성질을 가져 네 전환이 모두 가지려면 되짚어
찾아야 한다(make).

  조건  배선표 (버튼 5 개, 덮어쓰기)   1 라운드는 새로 뽑고, 그 뒤 매 라운드 **두 칸**씩 바뀜, 보임
  규칙  금지 전구 하나                 매 라운드 변경, 숨김 — 직전과도 두 라운드 전과도 다르게
  목표  완성할 줄 한두 개              매 라운드 변경, 숨김 — 끝에 정확히 그 줄만 완성
매 시도는 전구가 전부 꺼진 상태에서 시작한다. 정답 = 금지 전구를 켜는 버튼을 쓰지 않고 완성된 줄이
정확히 목표. 버튼 모양(3~4 칸 켜고 0~2 칸 끔)과 배선을 두 칸씩만 바꾸는 이유는 `전구-빙고` 와 같다.
목표 줄 수와 바뀌는 방식은 위의 계획(plan)을 따른다.

보장 — 라운드 1  (L 금지 전구, T 목표)
  L 을 켜지 않고 T 를 만드는 답이 있다 (3 번 이하, 규칙 없는 최단보다 많아야 한 번 더)
  규칙 없이 가장 짧은 T 답은 모두 L 을 켠다      기본대로 풀면 1 라운드에 금지를 한 번 겪는다
보장 — 라운드 i>=2  (L' 직전 금지, T' 직전 목표)
  배선이 정확히 두 칸 바뀐다. L != L' , L != 두 라운드 전 금지, T != T'
  L 도 L' 도 T 의 줄 위에 없다                  → L' 이 목표 줄에 있으면 '꺼진 목표 전구' 로 짚혀 전환이
                                                   바로 드러난다
  S  L 을 안 켜고 T (3 번 이하)                  있을 것
  P  L' 을 안 켜고 T                             있을 것 — 규칙만 옛것인 답
  H  L' 을 안 켜고 T' (3 번 이하)                있을 것 — 전환을 모르는 첫 제출
  L' 도 L 도 안 켜서는 줄을 하나도 못 만든다     → 직전 금지를 지키며 줄을 만들면 반드시 지금 금지를
                                                   켠다. P · H 는 모두 지속적 오류가 된다
  직전 라운드 정답을 그대로 내면 L' 은 안 켜고 L 을 켠다 → 되풀이한 첫 제출이 지속적 오류
  규칙 없이 가장 짧은 T 답은 모두 L' 을 켠다     → 직전 금지를 피하는 것은 배운 습관이라야 나온다
  L' 을 켜는 버튼이 둘 이상                     → 우연 기준을 낮춘다. 하나뿐이면 무작위 버튼 둘이
                                                   L' 을 피하고 L 을 켤 확률이 53%, 둘이면 26%
  옛 금지를 지켜도 끝 판 고치기가 막히지 않는다  정확히 T 인 끝 판에서 목표 줄 밖 전구 c 를 켜 둘(꺼 둘)
                                                   수 있으면, L' 을 안 켜고도 그럴 수 있다. 직전 금지를
                                                   지키는 모델이 결과를 고치다 옛 규칙과 부딪치지 않는다
  직전 라운드 · 두 라운드 전 정답은 지금 틀린다
`전구-빙고-금지전구` 에 있던 '규칙 없이 가장 짧은 답은 모두 L 도 켠다' 는 전환 라운드에서 뺐다. 정확히
그 줄만 만드는 답은 배선마다 몇 개뿐이라, 줄 0 보장과 함께 걸면 만족하는 배선이 없었다(0/240). 빼면
규칙을 모르는 가장 짧은 답이 지금 정답일 수 있다 — 직전 금지를 피하는 습관이 없을 때만 나오는 답이다.
"""
import json
import random
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import engine as E                                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BUTTONS, ROUNDS, CHANGE = 5, 5, 4                     # 배선은 매 라운드 네 칸(어느줄3 은 두 칸)
SEQS = E.sequences(BUTTONS, 4)
GOALS = {1: [(i,) for i in range(len(E.LINES))],
         2: list(combinations(range(len(E.LINES)), 2))}
CHANGES = ("뺌", "더함")                                # 1 한 줄 공유는 뺐다
NATURAL = True                                         # 2 규칙 없이 가장 짧은 T 답은 L 을 안 켠다
LOOKALIKE = True                                       # 3 첫 제출이 끝에 꺼진 T 전구를 도중에 켜지 않는다
COUPLE = 1 / 2                                         # 4 옛 목표 답 가운데 L' 을 안 켜는 몫의 하한
REPEAT_ALL = True                                      # 5 직전 라운드 정답(3 번 이하) 전부가 L' 을 안 켜고 L 을 켠다


def change(T, Tp):
    """직전 목표 Tp 에서 지금 목표 T 로 바뀐 방식. 세 방식이 아니면 None."""
    a, b = set(T), set(Tp)
    if a == b:
        return None
    if a < b:
        return "뺌" if len(b) - len(a) == 1 else None
    if a > b:
        return "더함" if len(a) - len(b) == 1 else None
    return "한 줄 공유" if len(a & b) == 1 else None


def plan(rng):
    """(라운드별 목표 줄 수, 전환별 바뀌는 방식). 한 줄 → 더함, 두 줄 → 뺌 — 줄 수가 한두 줄을 번갈아 오간다.
    1 라운드를 한 줄 · 두 줄 반반으로 뽑아, 문제마다 뺌 · 더함이 둘씩 나온다."""
    size = 1 if rng.random() < 1 / 2 else 2
    sizes, kinds = [size], []
    for _ in range(ROUNDS - 1):
        kind = "더함" if size == 1 else "뺌"
        size = 1 if kind == "뺌" else 2
        sizes.append(size)
        kinds.append(kind)
    return sizes, kinds


def pick(seqs):
    """가장 짧고, 같으면 글자 순으로 앞선 것."""
    return list(min(seqs, key=lambda p: (len(p), p)))


def shortest(seqs):
    m = min(len(p) for p in seqs)
    return [p for p in seqs if len(p) == m]


def distinct(table):
    return len({tuple(r) for r in table}) == len(table)


def random_table(rng):
    """버튼마다 3~4 칸 켜고 0~2 칸 끈다."""
    while True:
        t = []
        for _ in range(BUTTONS):
            row = [E.KEEP] * E.CELLS
            on, off = rng.randint(3, 4), rng.randint(0, 2)
            for k, c in enumerate(rng.sample(range(E.CELLS), on + off)):
                row[c] = E.ON if k < on else E.OFF
            t.append(row)
        if distinct(t):
            return t


def perturb(rng, table):
    """정확히 CHANGE 칸을 다른 효과로 바꾼다. 버튼마다 켜는 칸이 둘 이상 남고 버튼끼리 같아지지 않게."""
    cells = [(b, c) for b in range(BUTTONS) for c in range(E.CELLS)]
    while True:
        t = [row[:] for row in table]
        change = []
        for b, c in rng.sample(cells, CHANGE):
            to = rng.choice([e for e in E.EFFECTS if e != t[b][c]])
            change.append(dict(button=b, light=c, frm=t[b][c], to=to))
            t[b][c] = to
        if all(sum(e == E.ON for e in row) >= 2 for row in t) and distinct(t):
            return t, change


LINE_BITS = [sum(1 << c for c in l) for l in E.LINES]
LINES_OF = [tuple(i for i, lb in enumerate(LINE_BITS) if (s & lb) == lb) for s in range(1 << E.CELLS)]


def survey(table):
    """순서마다 (완성된 줄 묶음, 켜 본 전구 비트, 끝 판 비트). 켜 본 전구는 어떤 버튼을 썼는지로만 정해진다.
    engine.run · lines 와 같은 계산을 비트로, 앞 순서의 결과를 이어 받아 한다 — 되짚어 찾느라 배선 검사가
    수십만 번이라 느렸다. SEQS 는 짧은 순서부터라 앞 순서가 늘 먼저 계산돼 있다."""
    on = [sum(1 << c for c, e in enumerate(row) if e == E.ON) for row in table]
    off = [sum(1 << c for c, e in enumerate(row) if e == E.OFF) for row in table]
    acc, out = {(): (0, 0)}, {}
    for p in SEQS:
        end, m = acc[p[:-1]]
        b = p[-1]
        end, m = (end | on[b]) & ~off[b], m | on[b]
        acc[p] = (end, m)
        out[p] = (LINES_OF[end], m, end)
    return out


def blocked(info, exact, old, want):
    """옛 금지 전구 old 를 지키면 못 하는 끝 판 고치기 — (전구, 값) 집합. 정확히 목표인 답들의 끝 판에서
    목표 줄 밖 전구가 가질 수 있는 값 가운데, old 를 안 켜는 답으로는 못 만드는 것. old 자신은 뺀다 —
    끝에 old 가 켜진 판은 old 를 켜야만 나오고, 옛 규칙을 지키는 모델은 그 판을 원하지 않는다."""
    free = sum(1 << c for c in range(E.CELLS) if c not in want and c != old)
    on_seen = off_seen = on_kept = off_kept = 0
    for p in exact:
        _, m, end = info[p]
        on_seen |= end; off_seen |= ~end
        if not m >> old & 1:
            on_kept |= end; off_kept |= ~end
    bad_on, bad_off = on_seen & ~on_kept & free, off_seen & ~off_kept & free
    return ({(c, 1) for c in range(E.CELLS) if bad_on >> c & 1}
            | {(c, 0) for c in range(E.CELLS) if bad_off >> c & 1})


def one_round(rng, table, rounds, solved, size=None, kind=None):
    """이 배선에서 (금지 전구, 목표)를 고른다. 보장을 못 맞추면 None.
    size 는 1 라운드 목표 줄 수, kind 는 전환의 바뀌는 방식 — 주지 않으면 뺌 · 더함 중 아무것이나."""
    prev = rounds[-1] if rounds else None
    back = rounds[-2]["forbidden"] if len(rounds) >= 2 else None
    if prev is not None and len(E.lighting(table, prev["forbidden"])) < 2:
        return None                                        # 직전 금지 전구를 켜는 버튼은 둘 이상
    info = survey(table)
    by = defaultdict(list)
    for p, (done, _, _) in info.items():
        by[done].append(p)
    lit = lambda p, c: info[p][1] >> c & 1                  # noqa: E731
    if prev is not None:                                   # 4 옛 목표를 만드는 답의 절반 이상이 옛 금지를 안 켬
        old = [p for p in by.get(tuple(prev["goal"]), []) if len(p) <= 3]
        if not old or sum(not lit(p, prev["forbidden"]) for p in old) < COUPLE * len(old):
            return None
    sizes = [size] if size else [1, 2]
    rng.shuffle(sizes)
    goals = []
    for k in sizes:
        g = [T for T in GOALS[k] if prev is None or change(T, prev["goal"]) in ((kind,) if kind else CHANGES)]
        rng.shuffle(g)
        goals += g
    lights = [c for c in range(E.CELLS) if prev is None or c not in (prev["forbidden"], back)]
    rng.shuffle(lights)
    for T in goals:
        nline = by.get(T)
        if not nline:
            continue
        want = E.need(T)
        dflt = shortest(nline)
        if prev is not None:
            Lp = prev["forbidden"]
            if Lp in want or not all(lit(p, Lp) for p in dflt) or blocked(info, nline, Lp, want):
                continue
            wbits = sum(1 << c for c in want)              # 3 첫 제출이 끝에 꺼진 목표 전구를 도중에 켜지 않음
            H = [p for p in by.get(tuple(prev["goal"]), []) if len(p) <= 3 and not lit(p, Lp)]
            first = shortest(H) if H else []               # 습관 답 가운데 가장 짧은 것과 직전 정답
            if len(prev["shortest"]) <= 3:
                first.append(tuple(prev["shortest"]))
            if LOOKALIKE and any(info[p][1] & wbits & ~info[p][2] for p in first):
                continue
        for L in lights:
            if L in want or (prev is None and not all(lit(p, L) for p in dflt)):
                continue
            if NATURAL and prev is not None and any(lit(p, L) for p in dflt):
                continue                                   # 2 규칙 없이 가장 짧은 답은 새 금지를 안 켬
            S = {p for p in nline if not lit(p, L)}
            if not S or min(map(len, S)) > 3 or any(S & s for s in solved[-2:]):
                continue
            r = dict(table=table, goal=list(T), forbidden=L, shortest=pick(S), default=pick(dflt))
            if prev is None:
                if min(map(len, S)) > len(dflt[0]) + 1:
                    continue
                return r, S
            if any(info[p][0] for p in SEQS if not lit(p, Lp) and not lit(p, L)):
                continue                                   # 둘 다 피해서 줄을 만들 수 있음
            rep = tuple(prev["shortest"])
            if lit(rep, Lp) or not lit(rep, L):
                continue                                   # 직전 정답을 그대로 내면 지속적 오류
            if REPEAT_ALL and any(lit(p, Lp) or not lit(p, L) for p in solved[-1] if len(p) <= 3):
                continue                                   # 직전 라운드의 어느 정답을 되풀이해도 지속적 오류
            P = [p for p in nline if not lit(p, Lp)]
            H = [p for p in by.get(tuple(prev["goal"]), []) if not lit(p, Lp)]
            if not P or not H or min(map(len, H)) > 3:
                continue
            r.update(ruleStick=pick(P), habit=pick(H))
            return r, S
    return None


def make(rng, tries=1500, budget=20000, how=None):
    """다섯 라운드를 되짚어 가며 찾는다. 막힘 없음 보장을 넣고 한 라운드씩 앞으로만 가면 에피소드가 나오지
    않았다(라운드당 400 번 666 회 · 2000 번 93 회 모두 0) — 통과하는 배선이 드물고(섭동의 0.13%), 통과한
    배선이 다음 라운드에도 통과 배선을 낳을 확률이 12% 안팎이다. 다음 라운드가 막히면 이 라운드의 다른
    배선으로 돌아가 다시 찾는다(8 코어 30 초에 4 개). 1 라운드는 배선 하나만 보고, 안 되면 None.
    되짚기는 가지가 많으면 끝없이 길어져(첫 생성이 14 분에 30 개를 못 채움) 배선 검사 횟수를 budget 으로
    끊는다. 시간이 아니라 횟수로 끊어야 같은 씨앗에서 같은 문제가 나온다."""
    left = [budget]

    def grow(rounds, solved):
        if len(rounds) == ROUNDS:
            return rounds
        for _ in range(tries if rounds else 1):
            if left[0] <= 0:
                return None
            left[0] -= 1
            if rounds:
                table, change = perturb(rng, rounds[-1]["table"])
            else:
                table, change = random_table(rng), None
            if how:
                sizes, kinds = how
                got = one_round(rng, table, rounds, solved, size=None if rounds else sizes[0],
                                kind=kinds[len(rounds) - 1] if rounds else None)
            else:
                got = one_round(rng, table, rounds, solved)
            if not got:
                continue
            r, S = got
            if change:
                r["change"] = change
            r["round"] = len(rounds) + 1
            out = grow(rounds + [r], solved + [S])
            if out:
                return out
        return None
    return grow([], [])


def one(args):
    """에피소드 하나. 번호마다 씨앗이 정해져 있어, 개수를 늘려 다시 만들어도 앞 번호의 문제는 그대로다.
    1 라운드 배선 백 개 중 하나꼴로만 다섯 라운드가 이어져(되짚어 찾아도) 될 때까지 다시 뽑는다."""
    i, seed = args
    rng = random.Random(seed * 1000 + i)
    how = plan(rng)
    while True:
        r = make(rng, how=how)
        if r:
            return r


def numbered(args):
    return args[0], one(args)


def main(count=300, seed=20261028, jobs=8):
    """문제가 끝날 때마다 진행을 찍고, 앞 번호부터 빈틈없이 끝난 데까지 episodes.json 에 써 둔다 — 어느줄3
    300 문제는 pool.map 이라 한 시간 넘게 아무것도 보이지 않았다. 써 둔 앞부분으로 파일럿을 먼저 돌릴 수 있다."""
    import time
    from multiprocessing import Pool
    (ROOT / "episodes").mkdir(exist_ok=True)
    t0, done = time.time(), {}
    have = ROOT / "episodes/episodes.json"
    if have.exists():                                  # 이미 만든 번호는 그대로 둔다 — 번호마다 씨앗이 정해져 있다
        for e in json.loads(have.read_text()):
            done[int(e["id"][1:]) - 1] = e["rounds"]
    todo = [(i, seed) for i in range(count) if i not in done]
    print(f"이미 있는 {len(done)} 개는 그대로 두고 {len(todo)} 개를 만든다", flush=True)

    def save():
        k = 0
        while k in done:
            k += 1
        eps = [dict(id=f"Q{i + 1:03d}", buttons=BUTTONS, rounds=done[i]) for i in range(k)]
        (ROOT / "episodes/episodes.json").write_text(json.dumps(eps, ensure_ascii=False, indent=1))
        return eps

    eps = save()
    with Pool(jobs) as pool:
        for i, r in pool.imap_unordered(numbered, todo):
            done[i] = r
            eps = save()
            print(f"  Q{i + 1:03d} 끝 — {len(done)}/{count}, 앞에서부터 {len(eps)} 개 저장, {time.time() - t0:.0f} 초",
                  flush=True)
    rs = [r for e in eps for r in e["rounds"]]
    sw = [r for e in eps for r in e["rounds"][1:]]
    print(f"에피소드 {len(eps)}/{count}")
    print(f"  정답 길이 {dict(sorted(Counter(len(r['shortest']) for r in rs).items()))}"
          f"   규칙 없는 최단 길이 {dict(sorted(Counter(len(r['default']) for r in rs).items()))}")
    print(f"  목표 줄 수 {dict(sorted(Counter(len(r['goal']) for r in rs).items()))}"
          f"   금지 전구 {dict(sorted(Counter(r['forbidden'] + 1 for r in rs).items()))}")
    print(f"  습관 답 길이 {dict(sorted(Counter(len(r['habit']) for r in sw).items()))}")
    print(f"  바뀌는 방식 {dict(Counter(change(r['goal'], e['rounds'][i - 1]['goal']) for e in eps for i, r in enumerate(e['rounds']) if i))}")
    lit = Counter(len(E.lighting(r["table"], e["rounds"][i - 1]["forbidden"]))
                  for e in eps for i, r in enumerate(e["rounds"]) if i)
    print(f"  직전 금지 전구를 켜는 버튼 수(전환 라운드) {dict(sorted(lit.items()))}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if a else 300, int(a[1]) if len(a) > 1 else 20261028, int(a[2]) if len(a) > 2 else 8)
