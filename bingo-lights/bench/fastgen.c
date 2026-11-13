// 빙고 전구 문제 생성기의 C 판 — 파이썬 generate.py 의 one_round · make 와 같은 보장을 30~50 배 빠르게 찾는다.
//   clang -O2 -o fastgen fastgen.c
//   ./fastgen 버튼수 몫분자 몫분모 씨앗 번호 DEEP BUDGET   → 문제 하나를 JSON 으로 stdout 에
// 몫 = 보장 6(새 목표 답 가운데 옛 금지를 피하는 몫이 이것을 넘는다). 분모 0 이면 보장 6 을 걸지 않는다.
// 결과는 파이썬 bench/verify.py 가 engine 으로 처음부터 다시 검사한다. 난수가 달라 파이썬 판과 같은 문제가 나오지는 않는다.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CELLS 9
#define NLINES 8
#define ROUNDS 5
#define CHANGE 4
#define MAXB 8
#define MAXSEQ 2048
#define WORDS (MAXSEQ / 64)
#define TRIES 1500
enum { KEEP, ON, OFF };
static const char *EFFECT[] = {"KEEP", "ON", "OFF"};
static const int LINES[NLINES][3] = {{0, 1, 2}, {3, 4, 5}, {6, 7, 8}, {0, 3, 6}, {1, 4, 7}, {2, 5, 8}, {0, 4, 8}, {2, 4, 6}};

static int B, NSEQ, SNUM, SDEN;
static long DEEP, BUDGET, left_budget;
static int seq_len[MAXSEQ], seq_parent[MAXSEQ], seq_last[MAXSEQ], seq_b[MAXSEQ][4];
static uint8_t LINES_OF[512];
static int LINE_BITS[NLINES];

static uint64_t rng_s;
static uint64_t next64(void) {            // splitmix64
    uint64_t z = (rng_s += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static int rnd(int n) { return (int)(next64() % (uint64_t)n); }
static void shuffle(int *a, int n) {
    for (int i = n - 1; i > 0; i--) { int j = rnd(i + 1), t = a[i]; a[i] = a[j]; a[j] = t; }
}

typedef struct { int8_t e[MAXB][CELLS]; int on[MAXB], off[MAXB]; } Table;
typedef struct { int button, light, frm, to; } Change;
typedef struct {
    Table t; int goal, forbidden, shortest, dflt, rule, habit, has_change; Change ch[CHANGE];
} Round;
typedef struct { uint64_t w[WORDS]; } Set;

static Round rounds[ROUNDS];
static Set solved[ROUNDS];
static int plan_size, plan_kind[ROUNDS];  // kind: 0 뺌, 1 더함

static void masks(Table *t) {
    for (int b = 0; b < B; b++) {
        int on = 0, off = 0;
        for (int c = 0; c < CELLS; c++) { if (t->e[b][c] == ON) on |= 1 << c; else if (t->e[b][c] == OFF) off |= 1 << c; }
        t->on[b] = on; t->off[b] = off;
    }
}
static int distinct(const Table *t) {
    for (int a = 0; a < B; a++) for (int b = a + 1; b < B; b++) if (t->on[a] == t->on[b] && t->off[a] == t->off[b]) return 0;
    return 1;
}
static void random_table(Table *t) {      // 버튼마다 3~4 칸 켜고 0~2 칸 끈다
    memset(t, 0, sizeof *t);
    do {
        memset(t->e, KEEP, sizeof t->e);
        for (int b = 0; b < B; b++) {
            int cells[CELLS], on = 3 + rnd(2), off = rnd(3);
            for (int c = 0; c < CELLS; c++) cells[c] = c;
            shuffle(cells, CELLS);
            for (int k = 0; k < on + off; k++) t->e[b][cells[k]] = k < on ? ON : OFF;
        }
        masks(t);
    } while (!distinct(t));
}
static void perturb(const Table *from, Table *t, Change *ch) { // 정확히 CHANGE 칸. 버튼마다 켜는 칸 둘 이상, 버튼끼리 다르게
    for (;;) {
        *t = *from;
        int idx[MAXB * CELLS], n = B * CELLS;
        for (int i = 0; i < n; i++) idx[i] = i;
        for (int k = 0; k < CHANGE; k++) {
            int j = k + rnd(n - k), x = idx[j]; idx[j] = idx[k]; idx[k] = x;
            int b = x / CELLS, c = x % CELLS, cur = t->e[b][c], to = (cur + 1 + rnd(2)) % 3;
            ch[k] = (Change){b, c, cur, to};
            t->e[b][c] = (int8_t)to;
        }
        masks(t);
        int ok = 1;
        for (int b = 0; b < B && ok; b++) if (__builtin_popcount(t->on[b]) < 2) ok = 0;
        if (ok && distinct(t)) return;
    }
}

static int end_[MAXSEQ], lit_[MAXSEQ];
static uint8_t done_[MAXSEQ];
static void survey(const Table *t) {
    static int acc_end[MAXSEQ], acc_m[MAXSEQ];
    for (int i = 0; i < NSEQ; i++) {
        int b = seq_last[i], p = seq_parent[i];
        int e = p < 0 ? 0 : acc_end[p], m = p < 0 ? 0 : acc_m[p];
        e = (e | t->on[b]) & ~t->off[b]; m |= t->on[b];
        acc_end[i] = e; acc_m[i] = m;
        end_[i] = e; lit_[i] = m; done_[i] = LINES_OF[e];
    }
}
#define LIT(p, c) ((lit_[p] >> (c)) & 1)

static int want_bits(int goal) {
    int w = 0;
    for (int i = 0; i < NLINES; i++) if (goal >> i & 1) w |= LINE_BITS[i];
    return w;
}
static int blocked(const int *nl, int n, int old, int want) {
    int free_ = 0;
    for (int c = 0; c < CELLS; c++) if (!(want >> c & 1) && c != old) free_ |= 1 << c;
    int on_seen = 0, off_seen = 0, on_kept = 0, off_kept = 0;
    for (int i = 0; i < n; i++) {
        int e = end_[nl[i]];
        on_seen |= e; off_seen |= ~e & 511;
        if (!LIT(nl[i], old)) { on_kept |= e; off_kept |= ~e & 511; }
    }
    return ((on_seen & ~on_kept & free_) | (off_seen & ~off_kept & free_)) != 0;
}

// 이 배선에서 (금지 전구, 목표)를 고른다. 보장을 못 맞추면 0.
static int one_round(int d, const Table *t, Round *r, Set *S) {
    const Round *prev = d ? &rounds[d - 1] : NULL;
    int back = d >= 2 ? rounds[d - 2].forbidden : -1;
    int Lp = prev ? prev->forbidden : -1, common = 511;
    if (prev) {
        int cnt = 0;
        for (int b = 0; b < B; b++) cnt += (t->on[b] >> Lp) & 1;
        if (cnt < 2) return 0;
        // 보장 5 의 앞부분 — 직전 정답(3 번 이하)은 옛 금지를 안 켜고, 공통으로 켜는 전구가 있어야 한다
        const Set *s = &solved[d - 1];
        for (int i = 0; i < NSEQ && seq_len[i] <= 3; i++) if (s->w[i >> 6] >> (i & 63) & 1) {
            int m = 0;
            for (int k = 0; k < seq_len[i]; k++) m |= t->on[seq_b[i][k]];
            if (m >> Lp & 1) return 0;
            common &= m;
        }
        if (!common) return 0;
    }
    survey(t);
    if (prev) {                           // 4 옛 목표를 만드는 3 번 이하 답의 절반 이상이 옛 금지를 안 켬
        int n = 0, keep = 0;
        for (int i = 0; i < NSEQ && seq_len[i] <= 3; i++) if (done_[i] == prev->goal) { n++; keep += !LIT(i, Lp); }
        if (!n || keep * 2 < n) return 0;
    }
    int goals[64], ng = 0;
    if (prev) {
        for (int i = 0; i < NLINES; i++) {
            if (plan_kind[d] == 1 && !(prev->goal >> i & 1)) goals[ng++] = prev->goal | 1 << i;
            if (plan_kind[d] == 0 && (prev->goal >> i & 1)) goals[ng++] = prev->goal & ~(1 << i);
        }
    } else if (plan_size == 1) {
        for (int i = 0; i < NLINES; i++) goals[ng++] = 1 << i;
    } else {
        for (int i = 0; i < NLINES; i++) for (int j = i + 1; j < NLINES; j++) goals[ng++] = 1 << i | 1 << j;
    }
    shuffle(goals, ng);
    int lights[CELLS], nl_ = 0;
    for (int c = 0; c < CELLS; c++) if (c != Lp && c != back) lights[nl_++] = c;
    shuffle(lights, nl_);

    static int nl[MAXSEQ];
    for (int g = 0; g < ng; g++) {
        int T = goals[g], n = 0, minlen = 99;
        for (int i = 0; i < NSEQ; i++) if (done_[i] == T) { nl[n++] = i; if (seq_len[i] < minlen) minlen = seq_len[i]; }
        if (!n) continue;
        int want = want_bits(T), bad = 0;
        if (prev) {
            if (want >> Lp & 1) continue;
            for (int i = 0; i < n && !bad; i++) if (seq_len[nl[i]] == minlen && !LIT(nl[i], Lp)) bad = 1;
            if (bad) continue;
            if (SDEN) {                       // 6 새 목표 답 가운데 옛 금지를 피하는 몫이 SNUM / SDEN 을 넘는다
                int ex = 0, kept = 0;
                for (int i = 0; i < n; i++) if (seq_len[nl[i]] <= 3) { ex++; kept += !LIT(nl[i], Lp); }
                if (kept * SDEN <= SNUM * ex) continue;
            }
            if (blocked(nl, n, Lp, want)) continue;
            int hmin = 99;                    // 3 가장 짧은 습관 답과 직전 정답이 끝에 꺼진 목표 전구를 도중에 켜지 않음
            for (int i = 0; i < NSEQ && seq_len[i] <= 3; i++) if (done_[i] == prev->goal && !LIT(i, Lp) && seq_len[i] < hmin) hmin = seq_len[i];
            for (int i = 0; i < NSEQ && seq_len[i] <= 3 && !bad; i++)
                if (done_[i] == prev->goal && !LIT(i, Lp) && seq_len[i] == hmin && (lit_[i] & want & ~end_[i])) bad = 1;
            int rep = prev->shortest;
            if (seq_len[rep] <= 3 && (lit_[rep] & want & ~end_[rep])) bad = 1;
            if (bad) continue;
        }
        for (int l = 0; l < nl_; l++) {
            int L = lights[l];
            if (want >> L & 1) continue;
            bad = 0;
            for (int i = 0; i < n && !bad; i++) if (seq_len[nl[i]] == minlen && (prev ? LIT(nl[i], L) : !LIT(nl[i], L))) bad = 1;
            if (bad) continue;
            if (prev && !(common >> L & 1)) continue;   // 5 직전 정답 전부가 L 을 켠다
            int smin = 99, spick = -1;
            memset(S, 0, sizeof *S);
            for (int i = 0; i < n; i++) if (!LIT(nl[i], L)) {
                int p = nl[i];
                S->w[p >> 6] |= 1ULL << (p & 63);
                if (seq_len[p] < smin) { smin = seq_len[p]; spick = p; }
            }
            if (spick < 0 || smin > 3) continue;
            for (int k = 1; k <= 2 && k <= d && !bad; k++)
                for (int w = 0; w < WORDS; w++) if (S->w[w] & solved[d - k].w[w]) { bad = 1; break; }
            if (bad) continue;
            int dpick = -1;
            for (int i = 0; i < n; i++) if (seq_len[nl[i]] == minlen) { dpick = nl[i]; break; }
            r->t = *t; r->goal = T; r->forbidden = L; r->shortest = spick; r->dflt = dpick; r->rule = r->habit = -1;
            if (!prev) {
                if (smin > minlen + 1) continue;
                return 1;
            }
            for (int i = 0; i < NSEQ && !bad; i++) if (done_[i] && !LIT(i, Lp) && !LIT(i, L)) bad = 1;   // 줄 0
            if (bad) continue;
            int rep = prev->shortest;
            if (LIT(rep, Lp) || !LIT(rep, L)) continue;
            int P = -1, H = -1;
            for (int i = 0; i < n; i++) if (!LIT(nl[i], Lp)) { P = nl[i]; break; }
            for (int i = 0; i < NSEQ; i++) if (done_[i] == prev->goal && !LIT(i, Lp)) { H = i; break; }
            if (P < 0 || H < 0 || seq_len[H] > 3) continue;
            r->rule = P; r->habit = H;
            return 1;
        }
    }
    return 0;
}

static int grow(int d) {
    if (d == ROUNDS) return 1;
    long n = d == 0 ? 1 : d == 1 ? TRIES : DEEP;
    for (long k = 0; k < n; k++) {
        if (left_budget <= 0) return 0;
        left_budget--;
        Table t; Change ch[CHANGE];
        if (d) perturb(&rounds[d - 1].t, &t, ch); else random_table(&t);
        Round r; Set S;
        if (!one_round(d, &t, &r, &S)) continue;
        if (d) { memcpy(r.ch, ch, sizeof ch); r.has_change = 1; } else r.has_change = 0;
        rounds[d] = r; solved[d] = S;
        if (grow(d + 1)) return 1;
    }
    return 0;
}

static void seq_json(int i) {
    putchar('[');
    for (int k = 0; k < seq_len[i]; k++) printf("%s%d", k ? ", " : "", seq_b[i][k]);
    putchar(']');
}
static void print_problem(void) {
    printf("{\"rounds\": [");
    for (int d = 0; d < ROUNDS; d++) {
        const Round *r = &rounds[d];
        printf("%s{\"table\": [", d ? ", " : "");
        for (int b = 0; b < B; b++) {
            printf("%s[", b ? ", " : "");
            for (int c = 0; c < CELLS; c++) printf("%s\"%s\"", c ? ", " : "", EFFECT[(int)r->t.e[b][c]]);
            putchar(']');
        }
        printf("], \"goal\": [");
        int first = 1;
        for (int i = 0; i < NLINES; i++) if (r->goal >> i & 1) { printf("%s%d", first ? "" : ", ", i); first = 0; }
        printf("], \"forbidden\": %d, \"shortest\": ", r->forbidden);
        seq_json(r->shortest);
        printf(", \"default\": ");
        seq_json(r->dflt);
        if (d) {
            printf(", \"ruleStick\": "); seq_json(r->rule);
            printf(", \"habit\": "); seq_json(r->habit);
            printf(", \"change\": [");
            for (int k = 0; k < CHANGE; k++)
                printf("%s{\"button\": %d, \"light\": %d, \"frm\": \"%s\", \"to\": \"%s\"}", k ? ", " : "", r->ch[k].button, r->ch[k].light, EFFECT[r->ch[k].frm], EFFECT[r->ch[k].to]);
            putchar(']');
        }
        printf(", \"round\": %d}", d + 1);
    }
    printf("]}\n");
}

static void make_seqs(void) {             // engine.sequences 와 같은 순서 — 길이순, 같은 길이는 글자순
    NSEQ = 0;
    for (int len = 1; len <= 4; len++) {
        int a[4];
        for (a[0] = 0; a[0] < B; a[0]++) {
            if (len == 1) { seq_len[NSEQ] = 1; seq_b[NSEQ][0] = a[0]; NSEQ++; continue; }
            for (a[1] = 0; a[1] < B; a[1]++) {
                if (a[1] == a[0]) continue;
                if (len == 2) { seq_len[NSEQ] = 2; memcpy(seq_b[NSEQ], a, sizeof(int) * 2); NSEQ++; continue; }
                for (a[2] = 0; a[2] < B; a[2]++) {
                    if (a[2] == a[0] || a[2] == a[1]) continue;
                    if (len == 3) { seq_len[NSEQ] = 3; memcpy(seq_b[NSEQ], a, sizeof(int) * 3); NSEQ++; continue; }
                    for (a[3] = 0; a[3] < B; a[3]++) {
                        if (a[3] == a[0] || a[3] == a[1] || a[3] == a[2]) continue;
                        seq_len[NSEQ] = 4; memcpy(seq_b[NSEQ], a, sizeof(int) * 4); NSEQ++;
                    }
                }
            }
        }
    }
    for (int i = 0; i < NSEQ; i++) {
        seq_last[i] = seq_b[i][seq_len[i] - 1];
        seq_parent[i] = -1;
        if (seq_len[i] > 1)
            for (int j = 0; j < NSEQ; j++)
                if (seq_len[j] == seq_len[i] - 1 && !memcmp(seq_b[j], seq_b[i], sizeof(int) * seq_len[j])) { seq_parent[i] = j; break; }
    }
}

int main(int argc, char **argv) {
    if (argc < 8) { fprintf(stderr, "fastgen 버튼수 몫분자 몫분모 씨앗 번호 DEEP BUDGET\n"); return 2; }
    B = atoi(argv[1]); SNUM = atoi(argv[2]); SDEN = atoi(argv[3]);
    long long seed = atoll(argv[4]); long long index = atoll(argv[5]);
    DEEP = atol(argv[6]); BUDGET = atol(argv[7]);
    rng_s = (uint64_t)(seed * 1000 + index);
    for (int i = 0; i < NLINES; i++) LINE_BITS[i] = 1 << LINES[i][0] | 1 << LINES[i][1] | 1 << LINES[i][2];
    for (int s = 0; s < 512; s++) {
        int m = 0;
        for (int i = 0; i < NLINES; i++) if ((s & LINE_BITS[i]) == LINE_BITS[i]) m |= 1 << i;
        LINES_OF[s] = (uint8_t)m;
    }
    make_seqs();
    int size = rnd(2) ? 1 : 2;             // plan — 줄 수가 한두 줄을 번갈아 오간다
    plan_size = size;
    for (int d = 1; d < ROUNDS; d++) { plan_kind[d] = size == 1; size = plan_kind[d] ? 2 : 1; }
    for (;;) {
        left_budget = BUDGET;
        if (grow(0)) { print_problem(); return 0; }
    }
}
