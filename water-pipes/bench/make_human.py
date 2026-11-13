# -*- coding: utf-8 -*-
"""사람용 페이지를 만든다.   python3 bench/make_human.py [문제수] [씨앗]

W001~W300 에서 문제를 씨앗으로 뽑아 `human/water-pipes.html` 하나에 구워 넣는다. 파일 하나라 참가자에게
그대로 보내면 되고, 끝나면 참가자가 결과 JSON 을 내려받아 돌려준다(`bench/human_runs.py` 로 채점).

모델과 같은 문제 · 같은 예산 · 같은 피드백으로 맞춘다 — 파일럿 `물길/bench/make_human.py` 를 따랐다.
  · 숨은 것(어느 꽃에 물을 줘야 하나 · 연속 클릭 제약)도, 라운드 전환도 알리지 않는다. 둘이 '있다' 는
    것만 모델의 글과 같은 뜻으로 알린다
  · 예산 T · k 도 알리지 않는다(모델도 모른다). 라운드마다 T 번 안에 연속 k 번 맞혀야 넘어가고,
    못 넘어가면 그 문제는 거기서 끝난다 — runner.play 와 같다
  · 판정은 모델이 받는 글과 같은 내용만 — 물이 닿은 꽃의 색, 정답 여부, 틀린 타일 번호(이유는 구분 안 함)
  · 판은 라운드가 바뀌면 말없이 바뀐다. 모델도 다음 질문 앞에 새 판만 받는다
  · 문제(에피소드) 경계는 보여 준다. 모델도 문제마다 대화를 새로 연다
  · 회전 미리보기를 준다. 모델은 글에 적힌 규칙(한 번에 90°, 열린 쪽 표기)으로 회전과 물길을 정확히
    계산할 수 있으니, 사람에게 미리보기를 안 주면 적응이 아니라 머릿속 회전 능력을 재게 된다
메모장은 모델의 추론 자리라 남겨 두되 채점에는 쓰지 않는다.

틀린 타일(engine.wrong_tiles)은 정답 배치를 4^파이프 전수조사해야 해서 브라우저에서 하지 않고 여기서
라운드마다 구워 넣는다 — 지금 목표용(allow)과, 지속적 오류 깃발을 위한 직전 목표용(allowPrev).

문제는 **1 라운드를 푼 모델 수(0~3)로 층을 나눠** 뽑는다. 그냥 뽑으면 다섯 문제 중 셋이 세 모델 모두 1 라운드에서
끝난 문제였다(씨앗 1028) — 사람도 거기서 끝나면 지속적 오류를 잴 라운드가 없다. W001~W300 의 분포(0 · 1 · 2 · 3
모델이 77 · 71 · 63 · 89 문제)대로 몫을 나눈다. 모델 런이 없으면 그냥 뽑는다.

처음(10-28)에는 다섯 문제였다. 열 문제로 늘리면서 그 다섯 문제(W100 · W220 · W240 · W265 · W273)는 6~10번에 그대로
두고 1~5번에 다섯 문제를 더 넣었다. 더 넣는 문제는 열 문제 전체가 위 몫에 맞도록, 남은 문제에서 같은 씨앗으로 이어 뽑는다.
"""
import base64
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import engine as E                                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 1028
T, K = 10, 2                                          # runner 기본값과 같다
FIRST = 5                                             # 처음 낸 페이지의 문제 수 — 그 문제들은 맨 뒤에 둔다


def allow(board, goal):
    """그 목표의 정답 배치들에서 타일마다 허용되는 방향 — engine.wrong_tiles 와 같은 정의."""
    out = {}
    for turns in E.assignments(board).get(frozenset(goal), []):
        for i, r in turns.items():
            out.setdefault(str(i), set()).add(E.rotate(board["tiles"][i]["mask"], r))
    return {k: sorted(v) for k, v in out.items()}


# 물길_통합_300문제 덱이 쓰는 런 — W001~W300 을 세 모델이 한 번씩
RUNS = {"gpt-6.1-sol": ["20261025_192909", "20261025_200420", "20261026_002051", "20261026_112318"],
        "claude-opus-5-5": ["20261025_192915", "20261025_200429", "20261026_002056", "20261026_112323"],
        "claude-sonnet-5-5": ["20261025_192920", "20261025_200435", "20261026_002101", "20261026_112327"]}


def r1_solved():
    """문제마다 1 라운드를 푼 모델 수."""
    got = {}
    for runs in RUNS.values():
        for run in runs:
            for f in (ROOT / "runs" / run).glob("*_W*.json"):
                log = json.loads(f.read_text())
                got[log["episode"]] = got.get(log["episode"], 0) + bool(log["rounds"][0]["solved"])
    return got


def quota(layers, n, total):
    """층 크기에 비례한 몫(최대 나머지 방식)."""
    q = {k: n * len(v) / total for k, v in layers.items()}
    take = {k: int(x) for k, x in q.items()}
    for k in sorted(q, key=lambda k: q[k] - take[k], reverse=True)[:n - sum(take.values())]:
        take[k] += 1
    return take


def sample(everything, n, rng):
    """1 라운드를 푼 모델 수로 층을 나눠, 층 크기에 비례해 뽑는다.

    처음 페이지의 FIRST 문제를 그때와 같은 순서로 다시 뽑은 뒤, n 문제 전체가 몫에 맞도록 남은 문제에서 이어 뽑는다.
    새로 뽑은 문제가 앞, 처음 문제가 뒤."""
    solved = r1_solved()
    if len(solved) < len(everything):
        return sorted(rng.sample(range(len(everything)), n)), {}
    layers = {}
    for i, e in enumerate(everything):
        layers.setdefault(solved[e["id"]], []).append(i)
    first, full = quota(layers, min(FIRST, n), len(everything)), quota(layers, n, len(everything))
    assert all(full[k] >= first[k] for k in layers), (first, full)
    old = [i for k in sorted(layers) for i in rng.sample(layers[k], first[k])]
    new = [i for k in sorted(layers) for i in rng.sample([j for j in layers[k] if j not in old], full[k] - first[k])]
    return sorted(new) + sorted(old), solved


everything = json.loads((ROOT / "episodes/episodes.json").read_text())
picked, solved = sample(everything, N, random.Random(SEED))
eps = []
for e in (everything[i] for i in picked):
    rounds = []
    for j, r in enumerate(e["rounds"]):
        x = dict(round=r["round"], board=r["board"], goal=r["goal"], rule=r["rule"],
                 allow=allow(r["board"], r["goal"]))
        if j:
            x["allowPrev"] = allow(r["board"], e["rounds"][j - 1]["goal"])
        rounds.append(x)
    eps.append(dict(id=e["id"], size=e["rounds"][0]["board"]["size"], rounds=rounds))

CFG = json.dumps(dict(T=T, k=K, seed=SEED, sample=[e["id"] for e in eps]), ensure_ascii=False)
DATA = base64.b64encode(json.dumps(eps).encode()).decode()     # 목표 · 규칙이 소스에 그대로 보이지 않게

HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>물길</title>
<style>
 :root{color-scheme:light}
 *{box-sizing:border-box}
 body{font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif;
      background:#f5f5f7;color:#1a1a1a;margin:0;padding:22px;line-height:1.55}
 .wrap{max-width:1040px;margin:0 auto}
 .cols{display:flex;gap:16px;align-items:flex-start}
 .mid{flex:1 1 0;min-width:0}
 .side{flex:0 0 322px}
 .side .card{position:sticky;top:16px;max-height:calc(100vh - 32px);overflow:auto}
 @media (max-width:820px){.cols{flex-direction:column}.side{flex:none;width:100%}}
 h1{font-size:19px;margin:0 0 14px}
 .card{background:#fff;border:1px solid #e3e3e3;border-radius:12px;padding:20px;margin-bottom:16px}
 .muted{color:#777;font-size:13px}
 .prog{display:flex;gap:5px;margin:0 0 14px}
 .seg{flex:1 1 0;height:8px;background:#e2e2e2;border-radius:4px}
 .seg.on{background:#1a1a1a}

 /* 판 — 발표 자료(물길_통합_300문제.pptx)의 판 그림과 같은 SVG. 모양은 아래 boardSVG 가 그린다 */
 .board{margin:18px auto 4px;width:max-content}
 .board svg{display:block}
 .t{cursor:pointer}
 .t:hover .base{fill:#e8edf2}

 .legend{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin-top:8px}
 .legend span{display:inline-flex;align-items:center;gap:6px}
 .sw{width:18px;height:6px;border-radius:1px;display:inline-block}
 .dot{width:12px;height:12px;border-radius:50%;display:inline-block}

 button{font:inherit;cursor:pointer;font-weight:700;padding:11px 18px;line-height:1.3;
        background:linear-gradient(#ffffff,#eceef0);border:1px solid #bcc0c4;
        border-bottom:4px solid #aeb3b8;border-radius:12px;color:#1a1a1a;
        box-shadow:0 3px 7px rgba(0,0,0,.10);transition:transform .05s,box-shadow .05s}
 button:hover{background:linear-gradient(#ffffff,#e4e7ea)}
 button:active{transform:translateY(3px);border-bottom-width:1px;box-shadow:inset 0 3px 6px rgba(0,0,0,.14)}
 .go{background:linear-gradient(#2c2c2c,#141414);color:#fff;border-color:#141414;
     border-bottom:4px solid #000;padding:12px 26px;letter-spacing:2px}
 .go:hover{background:linear-gradient(#3a3a3a,#1e1e1e)}
 .seqbar{display:flex;gap:10px;align-items:center;justify-content:center;margin:18px 0 2px;flex-wrap:wrap}
 .seq{flex:0 0 auto;width:300px;max-width:100%;min-height:54px;border:2px dashed #c3c3c3;border-radius:11px;
      padding:5px 10px;background:#fafafa;display:flex;align-items:center;justify-content:center}
 .seq.empty{color:#bbb;font-size:13px}
 .tiles{display:flex;gap:5px;flex-wrap:wrap;justify-content:center}
 .tiles b{display:inline-flex;align-items:center;justify-content:center;min-width:24px;height:25px;
          padding:0 5px;border-radius:6px;background:#eef0f2;border:1px solid #d9dde1;
          font-size:13px;font-weight:800;color:#2a2a2a}
 .vd{font-weight:800;font-size:14px;min-height:44px;text-align:center;margin-top:10px}
 .vd .w{display:block;font-weight:600;color:#444}
 .vd.o .v{color:#1f7a3f}
 .vd.x .v{color:#b04040}

 .row{padding:9px 4px;border-bottom:1px solid #f1f1f1}
 .row .top{font-size:12px;font-weight:700}
 .row .top .o{color:#1f7a3f}
 .row .top .x{color:#b04040}
 .row .tiles{justify-content:flex-start;margin-top:4px}
 .row .tiles b{min-width:21px;height:21px;font-size:12px}

 textarea{width:100%;min-height:72px;font:inherit;font-size:13px;padding:10px;
          border:1px solid #ddd;border-radius:8px;resize:vertical}
 input{font:inherit;padding:9px 12px;border:1px solid #ccc;border-radius:8px;width:240px}
 .toast{position:fixed;left:50%;top:60px;transform:translateX(-50%);z-index:50;background:#1a1a1a;
        color:#fff;font-size:17px;font-weight:800;padding:12px 26px;border-radius:999px;
        opacity:0;pointer-events:none;box-shadow:0 6px 20px rgba(0,0,0,.18)}
 .toast.go2{animation:pop 1.4s ease-out}
 @keyframes pop{0%{opacity:0}15%{opacity:1}75%{opacity:1}100%{opacity:0}}
</style></head><body>
<div class="wrap">
 <div id="toast" class="toast"></div>

 <div id="intro" class="card">
  <h1>물길</h1>
  <p>이 퍼즐은 조금 특이합니다. 푸는 방법을 많이 알려 드릴 수 없습니다.</p>
  <p>파이프를 돌려 <b>맞는 꽃</b>에 물이 닿게 하세요. 칸은 파이프, 샘(물방울), 돌, 그리고 빨강 · 노랑 · 파랑
     꽃입니다. 누를 타일의 <b>순서</b>를 통째로 제출합니다.</p>
  <ul class="muted" style="padding-left:20px">
   <li>파이프만 돕니다. 한 번 누르면 시계 방향으로 90°, <b>네 번 누르면 제자리</b>입니다.</li>
   <li>물은 맞닿은 두 칸이 서로 마주 보는 쪽이 모두 열려 있을 때만 흐릅니다.</li>
   <li>타일 번호는 왼쪽 위부터 1, 2, 3 … 입니다. 같은 타일을 여러 번 눌러도 됩니다.</li>
   <li>매 시도는 <b>지금 보이는 판</b>에서 시작합니다. 제출 전까지 판은 누른 순서대로 돌려 본 미리보기입니다.</li>
   <li><b>맞는 꽃에 물을 주는 것만으로는 충분하지 않습니다.</b> 어느 꽃에 물을 줘야 하는지, 어떤 순서가
       받아들여지는지는 알려 드릴 수 없지만, 맞았는지 틀렸는지는 매번 알려 드립니다. 통하는 순서는 늘 있습니다.</li>
   <li>시간 제한은 없습니다. 문제는 모두 __N__개입니다.</li>
  </ul>
  <p style="margin-bottom:6px">이름 또는 식별자</p>
  <input id="who">
  <button class="go" style="margin-left:8px" onclick="start()">시작</button>
 </div>

 <div id="game" style="display:none">
  <div class="prog" id="prog"></div>
  <div class="cols"><div class="mid">
  <div class="card">
   <div class="muted" id="head"></div>
   <div class="board" id="board"></div>
   <div class="legend muted">
    <span><i class="sw" style="background:#18B8BE"></i>물이 흐르는 파이프</span>
    <span><i class="sw" style="background:#93A3B4"></i>마른 파이프</span>
    <span><i class="dot" style="background:#CDEFF1;border:2px solid #18B8BE"></i>물이 닿은 꽃</span>
   </div>
   <div class="vd" id="vd"></div>
   <div class="seqbar">
    <div class="seq empty" id="seq">타일을 눌러 순서를 만드세요</div>
    <button onclick="undo()">⌫</button>
    <button onclick="clr()">지우기</button>
    <button class="go" onclick="submit()">제출</button>
   </div>
  </div>
  <div class="card">
   <div class="muted" style="font-weight:700;margin-bottom:6px">메모 (채점에 쓰이지 않습니다)</div>
   <textarea id="memo" placeholder="알아낸 것을 적어 두셔도 됩니다"></textarea>
  </div>
  </div>
  <div class="side"><div class="card">
   <div class="muted" style="font-weight:700">이 문제의 기록</div>
   <div id="log"></div>
   <button style="margin-top:14px;font-size:12px;padding:6px 10px;border-bottom-width:2px"
           onclick="save()">중간에 그만둘 때: 지금까지 결과 내려받기</button>
  </div></div>
  </div>
 </div>

 <div id="done" class="card" style="display:none">
  <h1>끝났습니다</h1>
  <p>아래 버튼으로 결과 파일을 내려받아 전달해 주세요.</p>
  <button class="go" onclick="save()">결과 내려받기</button>
 </div>
</div>
<script>
const EPS = JSON.parse(atob("__DATA__")), CFG = __CFG__;   // 페이지 소스에서 답이 바로 읽히지 않게
const U=1, Rt=2, D=4, Lt=8;
const DIRS=[[U,4,-1,0],[Rt,8,0,1],[D,1,1,0],[Lt,2,0,-1]];
const COLORS=["red","yellow","blue"], KO={red:"빨강",yellow:"노랑",blue:"파랑"};
let who="", ei=0, ri=0, seq=[], out=[], log=null, t0=0, streak=0, subs=0, busy=false, prevSuccess=null;

const ep=()=>EPS[ei], rd=()=>ep().rounds[ri], bd=()=>rd().board;
const uniq=a=>[...new Set(a)].sort((x,y)=>x-y);
const same=(a,b)=>a.length===b.length && a.every((x,i)=>x===b[i]);

function rot(m){ return ((m<<1)|(m>>3))&15; }

/* bench/engine.apply · watered · reaches 와 같다 */
function applyClicks(board, clicks){
  const m=board.tiles.map(t=>t.mask);
  for(const i of clicks) if(board.tiles[i].kind==="pipe") m[i]=rot(m[i]);
  return m;
}
function watered(board, masks){
  const n=board.size, src=board.tiles.findIndex(t=>t.kind==="source");
  const seen=new Set([src]), q=[src];
  while(q.length){
    const i=q.shift(), r=Math.floor(i/n), c=i%n;
    for(const [bit,opp,dr,dc] of DIRS){
      if(!(masks[i]&bit)) continue;
      const r2=r+dr, c2=c+dc;
      if(r2<0||c2<0||r2>=n||c2>=n) continue;
      const j=r2*n+c2;
      if((masks[j]&opp) && !seen.has(j)){ seen.add(j); q.push(j); }
    }
  }
  return seen;
}
function reaches(board, masks){
  const seen=watered(board, masks);
  return COLORS.filter(c=>board.tiles.some((t,i)=>t.kind==="flower" && t.color===c && seen.has(i)));
}

/* bench/engine.violations 와 같다. 규칙은 같은 타일 연속 클릭 수의 띠 lo..hi (hi 가 null 이면 위 없음) */
function violations(board, clicks, rule){
  const fixed=[], bad=[];
  let last=-1, run=0;
  for(const i of clicks){
    if(board.tiles[i].kind!=="pipe"){ fixed.push(i); continue; }
    if(last!==-1 && i!==last && run<rule.lo) bad.push(last);
    run = (i===last) ? run+1 : 1;
    if(rule.hi!==null && run>rule.hi) bad.push(i);
    last=i;
  }
  if(last!==-1 && run<rule.lo) bad.push(last);
  return [fixed, bad];
}

/* bench/engine.evaluate 와 같다. tiles 는 틀린 곳 전부 — 규칙을 어긴 타일, 돌릴 수 없는데 누른 타일,
   이 순서를 적용했을 때 어떤 정답 배치에도 못 들어가는 파이프 */
function evaluate(board, clicks, goal, rule, allow){
  const [fixed,bad]=violations(board, clicks, rule);
  const masks=applyClicks(board, clicks);
  const wrong=Object.keys(allow).map(Number).filter(i=>!allow[i].includes(masks[i]));
  const off=uniq([...fixed, ...bad, ...wrong]);
  if(fixed.length) return {status:"fixed_tile", tiles:off, ok:false};
  if(bad.length)   return {status:"rule_violation", tiles:off, ok:false};
  const hit=reaches(board, masks), want=COLORS.filter(c=>goal.includes(c));
  if(!same(hit, want)) return {status:"wrong_set", watered:hit, tiles:off, ok:false};
  return {status:"solved", clicks:clicks.length, ok:true};
}

function start(){
  who=document.getElementById("who").value.trim();
  if(!who){ alert("이름 또는 식별자를 적어 주세요"); return; }
  document.getElementById("intro").style.display="none";
  document.getElementById("game").style.display="";
  openEpisode();
}

function openEpisode(){
  const e=ep();
  log={episode:e.id, size:e.size, T:CFG.T, T1:CFG.T, k:CFG.k, rounds:[], calls:[],
       startedAt:new Date().toISOString(), memo:""};
  out.push(log);
  ri=0; prevSuccess=null;
  document.getElementById("memo").value="";
  document.getElementById("prog").innerHTML=EPS.map((_,i)=>`<div class="seg ${i<=ei?"on":""}"></div>`).join("");
  document.getElementById("head").textContent=`문제 ${ei+1} / ${EPS.length}`;
  document.getElementById("log").innerHTML="";
  say(null);
  openRound();
}

/* 새 라운드는 말없이 연다 — 직전 판정 글은 그대로 두고 판만 바뀐다. 모델도 'That is the answer.'
   다음에 새 판을 받을 뿐이다. */
function openRound(){
  log.rounds.push({round:ri+1, submissions:0, solved:false, unparsed:0, streak:0,
                   band:0, rule:0, goal:0, both:0, repeat:0});
  subs=0; streak=0; t0=Date.now(); seq=[]; paint();
}

/* 판 그림 — 발표 자료 빌더의 draw_board · arms · flower · spring · rock 과 같은 비율과 색.
   타일 사이에 틈을 두고, 관은 각 타일 가장자리에서 끝난다. 물이 닿으면 관은 물색, 꽃은 뒤에 물색 원 */
const COL={tile:"#F4F6F8", line:"#D5DCE3", pipe:"#93A3B4", water:"#18B8BE", red:"#C64343", num:"#7B8C9D",
           wet:"#CDEFF1", spring:"#DDF6F7", glint:"#C9F3F5",
           stone:"#A09D96", stoneLine:"#716D66", stoneLight:"#CDCAC3", ground:"#E2DFD9"};
const PETAL={red:"#E0504A", yellow:"#F2C230", blue:"#3A7BD5"}, PISTIL={red:"#F7D560", yellow:"#C8771E", blue:"#F7D560"};
const SIZE=330;                                   // 판 한 변(px)
const nf=x=>+x.toFixed(2);                      // SVG 좌표는 소수 둘째 자리까지
const shade=(hex,f)=>"#"+[1,3,5].map(i=>Math.floor(parseInt(hex.slice(i,i+2),16)*f).toString(16).padStart(2,"0")).join("");

function armsSVG(x0, y0, t, mask, h, col){
  const cx=x0+t/2, cy=y0+t/2;
  return [[U,cx-h,y0,cx+h,cy+h],[Rt,cx-h,cy-h,x0+t,cy+h],[D,cx-h,cy-h,cx+h,y0+t],[Lt,x0,cy-h,cx+h,cy+h]]
    .filter(([bit])=>mask&bit)
    .map(([,ax,ay,bx,by])=>`<rect x="${nf(ax)}" y="${nf(ay)}" width="${nf(bx-ax)}" height="${nf(by-ay)}" fill="${col}"/>`).join("");
}
function flowerSVG(cx, cy, t, color, wet){         // 꽃잎 다섯 장과 꽃술
  let s = wet ? `<circle cx="${nf(cx)}" cy="${nf(cy)}" r="${nf(.34*t)}" fill="${COL.wet}" stroke="${COL.water}" stroke-width="${nf(.03*t)}"/>` : "";
  const base=PETAL[color], pw=.17*t, pl=.25*t, dc=.12*t;
  for(let k=0;k<5;k++){
    const a=(-90+72*k)*Math.PI/180, px=nf(cx+dc*Math.cos(a)), py=nf(cy+dc*Math.sin(a));
    s+=`<ellipse cx="${px}" cy="${py}" rx="${nf(pw/2)}" ry="${nf(pl/2)}" fill="${base}" stroke="${shade(base,.72)}"`
      +` stroke-width="0.7" transform="rotate(${72*k} ${px} ${py})"/>`;
  }
  return s+`<circle cx="${nf(cx)}" cy="${nf(cy)}" r="${nf(.065*t)}" fill="${PISTIL[color]}"/>`;
}
function springSVG(cx, cy, t){                     // 옅은 물색 샘 안의 물방울
  const rb=.31*t, r=.12*t, cd=cy+.08*t, c=1/1.9, hw=r*Math.sqrt(1-c*c), top=cd-1.9*r, foot=cd-r*c;
  const gx=nf(cx-.39*r), gy=nf(cd-.15*r);
  return `<circle cx="${nf(cx)}" cy="${nf(cy)}" r="${nf(rb)}" fill="${COL.spring}" stroke="${COL.water}" stroke-width="${nf(.026*t)}"/>`
    + `<polygon points="${nf(cx)},${nf(top)} ${nf(cx+hw)},${nf(foot)} ${nf(cx-hw)},${nf(foot)}" fill="${COL.water}"/>`
    + `<circle cx="${nf(cx)}" cy="${nf(cd)}" r="${nf(r)}" fill="${COL.water}"/>`
    + `<ellipse cx="${gx}" cy="${gy}" rx="${nf(.16*r)}" ry="${nf(.3*r)}" fill="${COL.glint}" transform="rotate(20 ${gx} ${gy})"/>`;
}
function rockSVG(cx, cy, t){                       // 비튼 팔각형 바위와 밝은 면, 바닥 그림자
  const w=.54*t, h=.4*t, x=cx-w/2, y=cy-h/2-.02*t, k=.29289*Math.min(w,h);
  const pts=[[x+k,y],[x+w-k,y],[x+w,y+k],[x+w,y+h-k],[x+w-k,y+h],[x+k,y+h],[x,y+h-k],[x,y+k]]
    .map(([a,b])=>`${nf(a)},${nf(b)}`).join(" ");
  const lx=nf(cx-.095*t), ly=nf(cy-.1125*t);
  return `<ellipse cx="${nf(cx)}" cy="${nf(cy+.17*t)}" rx="${nf(.29*t)}" ry="${nf(.06*t)}" fill="${COL.ground}"/>`
    + `<polygon points="${pts}" fill="${COL.stone}" stroke="${COL.stoneLine}" stroke-width="1" transform="rotate(8 ${nf(cx)} ${nf(cy-.02*t)})"/>`
    + `<ellipse cx="${lx}" cy="${ly}" rx="${nf(.095*t)}" ry="${nf(.0375*t)}" fill="${COL.stoneLight}" transform="rotate(-15 ${lx} ${ly})"/>`;
}
function boardSVG(b, masks, seen, bad){
  const n=b.size, gap=SIZE*.035, t=(SIZE-gap*(n-1))/n, h=t*.085;
  let s=`<svg width="${SIZE}" height="${SIZE}" viewBox="0 0 ${SIZE} ${SIZE}" role="img" aria-label="판">`;
  b.tiles.forEach((tl,i)=>{
    const x0=(i%n)*(t+gap), y0=Math.floor(i/n)*(t+gap), cx=x0+t/2, cy=y0+t/2, wet=seen.has(i);
    s+=`<g class="t" onclick="tap(${i})"><rect class="base" x="${nf(x0)}" y="${nf(y0)}" width="${nf(t)}" height="${nf(t)}"`
      +` rx="${nf(.1*t)}" fill="${COL.tile}" stroke="${COL.line}" stroke-width="1"/>`;
    if(tl.kind==="stone") s+=rockSVG(cx, cy, t);
    else {
      s+=armsSVG(x0, y0, t, masks[i], h, (tl.kind==="source"||wet) ? COL.water : COL.pipe);
      if(tl.kind==="source") s+=springSVG(cx, cy, t);
      if(tl.kind==="flower") s+=flowerSVG(cx, cy, t, tl.color, wet);
    }
    if((bad||[]).includes(i))                      // 틀린 타일 — 빨간 테두리(발표 자료와 같음)
      s+=`<rect x="${nf(x0+1.5)}" y="${nf(y0+1.5)}" width="${nf(t-3)}" height="${nf(t-3)}" rx="${nf(.1*t)}" fill="none" stroke="${COL.red}" stroke-width="3"/>`;
    s+=`<text x="${nf(x0+.07*t)}" y="${nf(y0+.05*t)}" dominant-baseline="hanging" font-size="${nf(.16*t)}" fill="${COL.num}">${i+1}</text></g>`;
  });
  return s+"</svg>";
}

/* 판을 그린다. 미리보기라 지금 만든 순서까지 돌려서 보여 준다 */
function paint(bad){
  const b=bd(), masks=applyClicks(b, seq), seen=watered(b, masks);
  document.getElementById("board").innerHTML=boardSVG(b, masks, seen, bad);
  const el=document.getElementById("seq");
  el.className="seq"+(seq.length?"":" empty");
  el.innerHTML=seq.length ? `<span class="tiles">${seq.map(i=>`<b>${i+1}</b>`).join("")}</span>`
                          : "타일을 눌러 순서를 만드세요";
}

function tap(i){ if(busy) return; seq.push(i); paint(); }
function undo(){ if(busy) return; seq.pop(); paint(); }
function clr(){ if(busy) return; seq=[]; paint(); }

/* 모델이 받는 글과 같은 내용 — 물이 닿은 꽃, 정답 여부, 틀린 타일 */
const wateredText=c=>"물이 닿은 꽃: "+(c.length ? c.map(x=>KO[x]).join(" · ") : "없음");
const verdictText=res=>res.ok ? "정답입니다"
  : (res.tiles.length ? `틀린 타일 ${res.tiles.map(i=>i+1).join(" ")} — 정답이 아닙니다` : "정답이 아닙니다");
function say(res, reached){
  const vd=document.getElementById("vd");
  if(!res){ vd.className="vd"; vd.innerHTML=""; return; }
  vd.className="vd "+(res.ok?"o":"x");
  vd.innerHTML=`<span class="w">${wateredText(reached)}</span><span class="v">${verdictText(res)}</span>`;
}

function submit(){
  if(busy || !seq.length) return;
  const e=ep(), r=rd(), b=r.board, clicks=seq.slice();
  const res=evaluate(b, clicks, r.goal, r.rule, r.allow);
  const reached=reaches(b, applyClicks(b, clicks));
  const rec=log.rounds[ri];
  rec.submissions++; subs++;
  const call={round:ri+1, submission:rec.submissions, clicks, status:res.status, correct:res.ok, reached,
              tiles:res.ok ? [] : res.tiles,          // 틀린 타일 — 모델 로그의 피드백 글에 해당
              api:{provider:"human", participant:who, secs:(Date.now()-t0)/1000}};
  if(!res.ok && ri){               // runner.play 의 지속적 오류 깃발과 같다 — 판은 지금 것
    const p=e.rounds[ri-1], [f,v]=violations(b, clicks, p.rule);
    const hits={band:!f.length && !v.length,
                rule:evaluate(b, clicks, r.goal, p.rule, r.allow).ok,
                goal:evaluate(b, clicks, p.goal, r.rule, r.allowPrev).ok,
                both:evaluate(b, clicks, p.goal, p.rule, r.allowPrev).ok,
                repeat:prevSuccess!==null && same(clicks, prevSuccess)};
    for(const [k,hit] of Object.entries(hits)) if(hit){ rec[k]++; call[k]=true; }
  }
  log.calls.push(call);
  t0=Date.now();
  say(res, reached);
  paint(res.ok ? null : res.tiles);

  const row=document.createElement("div");
  row.className="row";
  row.innerHTML=`<div class="top"><span class="${res.ok?"o":"x"}">${verdictText(res)}</span></div>`
    + `<div class="muted">${wateredText(reached)}</div>`
    + `<div class="tiles">${clicks.map(i=>`<b>${i+1}</b>`).join("")}</div>`;
  const lg=document.getElementById("log");
  lg.appendChild(row); row.scrollIntoView({block:"nearest"});

  streak = res.ok ? streak+1 : 0;
  busy=true;
  if(res.ok && streak>=CFG.k){
    rec.solved=true; rec.streak=streak; rec.solution=clicks; prevSuccess=clicks;
    // 라운드가 끝난 것을 알리지 않는다. 모델도 통보받지 않고 다음 질문에 새 판만 받는다.
    setTimeout(()=>{ busy=false; nextRound(); }, 900);
  } else if(subs>=CFG.T){
    rec.budgetExhausted=true;
    log.status = ri===0 ? "round1_unsolved" : `stopped_round${ri+1}`;
    setTimeout(()=>{ busy=false; nextEpisode(); }, 1200);
  } else {
    setTimeout(()=>{ busy=false; seq=[]; paint(res.ok ? null : res.tiles); }, 700);
  }
}

function nextRound(){
  ri++;
  if(ri>=ep().rounds.length){ log.status="completed"; nextEpisode(); return; }
  openRound();
  // 기록은 그대로 둔다 — 모델의 대화 기록에 해당하고, 지우면 라운드가 바뀐 신호가 된다.
}

function nextEpisode(){
  log.memo=document.getElementById("memo").value;
  ei++;
  if(ei>=EPS.length){
    document.getElementById("game").style.display="none";
    document.getElementById("done").style.display="";
    return;
  }
  toast(`문제 ${ei+1} 시작`);       // 모델도 문제마다 대화를 새로 연다
  openEpisode();
}

function toast(t){
  const el=document.getElementById("toast");
  el.textContent=t; el.className="toast"; void el.offsetWidth; el.className="toast go2";
}

function save(){
  if(log && ei<EPS.length) log.memo=document.getElementById("memo").value;
  const blob=new Blob([JSON.stringify({name:who, finishedAt:new Date().toISOString(), config:CFG, sessions:out},
                                      null, 1)], {type:"application/json"});
  const a=document.createElement("a");
  a.href=URL.createObjectURL(blob);
  a.download=`물길_사람_${who}.json`;
  a.click();
}
</script></body></html>
"""

(ROOT / "human").mkdir(exist_ok=True)
page = ROOT / "human" / f"{ROOT.name}.html"           # human/water-pipes.html
page.write_text(HTML.replace("__DATA__", DATA).replace("__CFG__", CFG).replace("__N__", str(len(eps))))
print(page)
print(f"  문제 {len(eps)} 개 (씨앗 {SEED}): " + " ".join(e["id"] + (f"({solved[e['id']]})" if solved else "") for e in eps)
      + f" · T={T} k={K}" + ("   괄호 = 1 라운드를 푼 모델 수" if solved else ""))
print(f"  열기: open {page}")
