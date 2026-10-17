#!/usr/bin/env python3
"""Golden for qkd_kvn_ctx_cal (rtl/qwen_sys/d2d_static_20261015/qkd_kvn_ctx_cal.sv), Q-KVSYS PVJOIN 2026-10-16.

    kvn_ctx_golden.py CALDIR OUTDIR [--ntok N] [--ch CH]

CALDIR = tools/qwen_split/d2d_link_calendar.py --profile program output (the run_d2d_program.sh arguments; its
d2d_cal_seq_image.py include must equal the committed rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh, checked here).

From the link compiler's program calendar it takes (a) every KV-die RX port-3 KVN arrival (kind 5) per run segment
(segment 1 = token run, L0; segment 0 = the layer run replayed by layers 1..35) and (b) the compiled run starts START[l].
It writes
  kvn_ctx_gold.svh   KVN_L0_OUT[4] / KVN_LN_OUT[4] (receiver-run edges of the KVN word at the end's rx_out), START[36],
                     token period, first-token offset, the leaf's and the end's fixed latencies;
  host.memh          per token: {gen2, cohort_tag59} (HOST stimulus: epoch 0x0123, token 4242 + 1009 n, position 77 + 5 n);
  expect.memh        per token x layer: {gen2, identity59} = {epoch, layer + 1, token, position, 0} -- the compute die's
                     qfd_native59_command_context begin_tag for that layer (the value every KVN word of the layer carries);
  window.json        the stability window check: the leaf's expectation for run r is valid from cal_start(r) + LEAF_STAGE
                     + PR edges until cal_start(r + 1) + LEAF_STAGE + PR; every KVN word of run r must lie inside, and the HOST
                     cohort must change at least LEAF_TAG + PR edges before the token's first KVN word.
Exit 1 when the committed image differs or a window check fails.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEAF_STAGE = 3      # cal_start pin -> stage_q -> output flop
LEAF_TAG = 2        # cohort pin -> output flop
PR = 1              # qkd_d2d_static pin-register wrapper: kvn_compiled_* captured one edge at its pin
END_START = 1       # the end captures cal_start one edge at its pin (PR): end run edge 0 = DCAL cal_start + 1
EPOCH = 0x0123


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('caldir')
    ap.add_argument('out')
    ap.add_argument('--ntok', type=int, default=2)
    ap.add_argument('--ch', type=int, default=12, help='HOST cohort change, edges after the token cal_start')
    a = ap.parse_args()
    cd, od = Path(a.caldir), Path(a.out)
    od.mkdir(parents=True, exist_ok=True)
    img = od / 'd2d_cal_image_compiled.svh'
    subprocess.run([sys.executable, str(ROOT / 'tools/qwen_split/d2d_cal_seq_image.py'), str(cd), str(img)], check=True)
    if img.read_text() != (ROOT / 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh').read_text():
        print('KVN_CTX_GOLDEN FAIL committed sequencer image differs from the compiler')
        return 1
    cal = json.loads((cd / 'calendar.json').read_text())
    prog = cal['program']
    kvn = [m for m in cal['messages'] if m['src'] == 'C' and m['rx_port'] == 3 and m['kind'] == 5]
    seg = {s: sorted(m['rx_out'] for m in kvn if m.get('seg', 0) == s) for s in (0, 1)}
    arr = {s: sorted(m['arrive'] for m in kvn if m.get('seg', 0) == s) for s in (0, 1)}
    if len(seg[0]) != 4 or len(seg[1]) != 4:
        print(f'KVN_CTX_GOLDEN FAIL expected 4 KVN words per run, got {seg}')
        return 1
    starts = [0] + [l['start'] for l in prog['layers'][1:]]
    period = prog['token_period']
    adm = prog['admission']
    # stability windows, in DCAL edges relative to the token cal_start
    run_start = starts + [period]                       # the next token's run starts at the period
    bad, margins = [], []
    for r in range(36):
        lo = run_start[r] + LEAF_STAGE + PR             # first edge the end sees stage r + 1
        hi = run_start[r + 1] + LEAF_STAGE + PR         # first edge it sees the next run's stage
        s = 1 if r == 0 else 0
        first = run_start[r] + END_START + arr[s][0]
        last = run_start[r] + END_START + seg[s][-1]
        margins.append(dict(run=r, before=first - lo, after=hi - 1 - last))
        if first < lo or last >= hi:
            bad.append(r)
    l0_first = END_START + arr[1][0]
    host_margin = l0_first - (a.ch + LEAF_TAG + PR)
    # HOST CONTEXT record: the token run's kind-12 S->C record is captured by the end at token-run edge wr (it carries
    # the new token's context, so the HOST cohort is already the new token's by then: the KVN expectation needs less)
    ctx = [m for m in cal['messages'] if m['src'] == 'K' and m['kind'] == 12 and m.get('seg', 0) == 1]
    win = dict(leaf_stage_edges=LEAF_STAGE, leaf_tag_edges=LEAF_TAG, end_pin_edges=PR, end_start_edges=END_START,
               kvn_rx_out=dict(token_run=seg[1], layer_run=seg[0]), kvn_arrive=dict(token_run=arr[1], layer_run=arr[0]),
               starts=starts, token_period=period, first_token_ofs=adm['first_token_ofs'],
               min_margin_before=min(x['before'] for x in margins), min_margin_after=min(x['after'] for x in margins),
               host_cohort_change_edge=a.ch, host_margin_to_L0_kvn=host_margin,
               host_context_record_wr=[m['wr'] for m in ctx], bad_runs=bad,
               verdict='PASS' if not bad and host_margin >= 0 else 'FAIL')
    (od / 'window.json').write_text(json.dumps(win, indent=1) + '\n')

    def vec(vals, w):
        return f"{len(vals) * w}'h" + ''.join(f'{x:0{w // 4}x}' for x in reversed(vals))
    lines = [f'localparam [4*16-1:0] KVN_L0_OUT = {vec(seg[1], 16)};',
             f'localparam [4*16-1:0] KVN_LN_OUT = {vec(seg[0], 16)};',
             f'localparam [36*20-1:0] GOLD_START = {vec(starts, 20)};',
             f'localparam integer GOLD_PERIOD = {period};',
             f'localparam integer GOLD_FIRST = {adm["first_token_ofs"]};',
             f'localparam integer END_START = {END_START};',
             f'localparam integer GOLD_NTOK = {a.ntok};',
             f'localparam integer GOLD_CH = {a.ch};']
    (od / 'kvn_ctx_gold.svh').write_text('\n'.join(lines) + '\n')
    host, exp = [], []
    for n in range(a.ntok):
        token, pos, gen = 4242 + 1009 * n, 77 + 5 * n, n % 4
        tag = (EPOCH << 43) | (token << 19) | (pos << 6)
        host.append((gen << 59) | tag)
        for layer in range(36):
            exp.append((gen << 59) | (EPOCH << 43) | ((layer + 1) << 37) | (token << 19) | (pos << 6))
    (od / 'host.memh').write_text(''.join(f'{x:016x}\n' for x in host))
    (od / 'expect.memh').write_text(''.join(f'{x:016x}\n' for x in exp))
    print(f"KVN_CTX_GOLDEN {win['verdict']} runs=36 kvn_rx_out L0={seg[1]} Ln={seg[0]} margin_before>={win['min_margin_before']} "
          f"margin_after>={win['min_margin_after']} host_margin={host_margin} bad={bad}")
    return 0 if win['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
