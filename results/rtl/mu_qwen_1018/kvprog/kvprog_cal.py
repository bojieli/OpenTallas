#!/usr/bin/env python3
"""MU-KV-PROG 10-19: the 4-user stage calendar of tb_kvprog_mu (static; lprg_mu GAP table + the bench's owner order).

Stage rows = the KV die's production layer-relative roots (results/arch/qwen_kv_static_programme_1017/die/report.json
layer_relative_roots: ctrl_go 227, kgo 227, vgo 1273, attention_issue 606, attention_run 610, writer_start 642,
link_start 3, expected_quiet 2396, stage_end 6836) for all 36 stages; writer slots 4..7, stop 12 (report.json writer).
Placement law (static; the KV die serves one user's stage at a time, results/rtl/mu_qwen_1018/kvprog/README.md section 3):
  * user 0 = latency user, gaps 0, its stage s begins at (s-1) * 6836 from its accepted start;
  * fillers 1..3 (round robin, one stage each in turn): a stage begins at the earliest edge >= the end of the user's
    previous stage (or >= k * 1800 for stage 1) whose KV-die attention window [B+606, B+2400) is disjoint from every placed
    window and whose root edges {B+r} (and its end edge B+6836) hit no edge already used by another user (lprg_mu
    collision rule).  Stage begin of user u = its accepted start edge A_u = u (consecutive start pulses) + GAP[u][0].
  * 'bad' = the same with user 1's first stage forced to begin 1000 edges after user 0's (attention windows overlap):
    the RTL must fault (the attention controller rejects a load while busy).
Writes kvprog_cal_good.hex / kvprog_cal_bad.hex (32-bit words, layout below) and prints a summary.
  [0..143]   GAP[u][s-1] (u-major)            [144..287] owner order (u << 8 | s), sorted by stage begin
  [288..290] ownership roots, single user      [291..293] ownership roots, MU (max over users)
  [294]      last stage end edge (all users)   [295]      user 0's last stage end edge
"""
import sys
from pathlib import Path

P = 6836
ROOTS = [0, 3, 227, 606, 610, 642, 1273, 2396]       # stage begin + every root edge (link 3, ctrl/k 227, ...)
ATT = (606, 2400)                                   # attention programme busy window (issue .. run + 1784 + margin)
QUIET = 2396
NU, NS = 4, 36


def place(force1=None):
    used = {}                                        # edge -> user
    wins = []
    B = {u: [] for u in range(NU)}

    def ok(u, b):
        a0, a1 = b + ATT[0], b + ATT[1]
        if any(not (a1 <= w0 or w1 <= a0) for (w0, w1, v) in wins if v != u):
            return False
        return all(used.get(b + r, u) == u for r in ROOTS + [P])

    def add(u, b):
        for r in ROOTS + [P]:
            used[b + r] = u
        wins.append((b + ATT[0], b + ATT[1], u))
        B[u].append(b)
    for s in range(NS):
        add(0, s * P)
    nxt = {k: k * 1800 for k in range(1, NU)}
    if force1 is not None:
        add(1, force1)
        nxt[1] = force1 + P
    while any(len(B[k]) < NS for k in range(1, NU)):
        for k in range(1, NU):                       # round robin: users 1, 2, 3 interleave stage by stage
            if len(B[k]) == NS:
                continue
            b = nxt[k]
            while not ok(k, b):
                b += 1
            add(k, b)
            nxt[k] = b + P
    return B


def image(B):
    gaps = []
    for u in range(NU):
        g = [B[u][0] - u] + [B[u][s + 1] - (B[u][s] + P) for s in range(NS - 1)]
        assert all(x >= 0 for x in g), (u, g[:4])
        gaps += g
    order = sorted((B[u][s], u, s + 1) for u in range(NU) for s in range(NS))
    order = [(u << 8) | s for _, u, s in order]
    dur = [B[u][-1] - B[u][0] for u in range(NU)]
    single = [3, (NS - 1) * P + QUIET + 8, NS * P]
    mu = [3, max(dur) + QUIET + 8, max(dur) + P]
    last = max(B[u][-1] + P for u in range(NU))
    return gaps + order + single + mu + [last, B[0][-1] + P], dur


def main(outdir):
    for name, f1 in (('good', None), ('bad', 1000)):
        B = place(f1)
        words, dur = image(B)
        Path(outdir, f'kvprog_cal_{name}.hex').write_text(''.join(f'{w:08x}\n' for w in words))
        print(name, 'first begins', [B[u][0] for u in range(NU)], 'durations', dur, 'last end', words[294],
              'max gap', max(words[:144]))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent)
