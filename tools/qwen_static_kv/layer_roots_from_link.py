#!/usr/bin/env python3
"""Q-KVSYS PVJOIN 2026-10-16: compile the all36 layer-programme roots from the link compiler's program calendar.

    layer_roots_from_link.py CALDIR OUTDIR [--T 8192] [--digest 0x..] [--epoch N]

The layer programme (rtl/qwen_sys/static_kv_20261014/qkd_static_kv_layer_programme.sv; ROM-image variant
qkd_static_kv_layer_programme_rom.sv) emits nine fixed roots per stage.  This compiler places them on the KV link's own
calendar (tools/qwen_split/d2d_link_calendar.py --profile program, CALDIR/calendar.json):

  frame   programme external start = the KV link calendar sequencer's TOKEN cal_start (qkd_d2d_cal_seq_pin cal_start with
          layer 0); internal start = +1 edge = the static D2D end's run edge 0 (the end captures cal_start one edge at its
          pin).  Programme age a == KV run edge a.  Stage 1 = L0, which sits inside the token run at program.layers[0].start
          (its roots carry that base); stage s >= 2 = layer s-1 = the link calendar's layer run s-1, so
          stage_end[1] = START[1], stage_end[s] = START[s] - START[s-1] (s = 2..35), stage_end[36] = layers[35].cycles.
  attention_run     = the CMD record's event edge at the attention programme - RX_CMD (qkd_native_attention_static_ctl:
                      run is age 0, CMD at age RX_CMD >= 2); CMD event edge = KV rx_out of the kind-1 record + D2D_OUT
                      (pin-registered end output) ;
  attention_issue   = attention_run - ISSUE_TO_RUN (programme guard + descriptor load: >= 4) ;
  start_qk          = attention_run + RX_CMD + Q_TO_START (service samples Q beat 0 two edges after the request) ;
  kgo / ctrl_go     = start_qk - KV calendar qk_start_after_prefetch (tools/qwen_static_schedule/kv_calendar.py
                      screen_36_capacity at T, resized front 10 / ring 64, refresh as implemented) ;
  vgo               = kgo + PV_START (attn_calendar w16 G3S2 at T: the V pass's own prefetch lead = the K lead) ;
  writer_start      = first KVN word event (KV rx_out of kind 5 + D2D_OUT) - WRITER_T0 (qkd_kv_native_programme t0 >= 4) ;
  link_start        = 3 (the earliest legal root: the link calendar is already started by the sequencer; informational) ;
  expected_quiet    = last KV->compute STATUS send of the layer + 1 (nothing of this layer leaves the KV die after it) ;
Constants D2D_OUT, RX_CMD, Q_TO_START, ISSUE_TO_RUN, WRITER_T0 are named below with their source.  Die relay / pin ages
between the masters are NOT measured: the image is COMPONENT_TEST (not production installable), exactly as
tools/qwen_static_kv/layer_programme.py labels images without MEASURED path receipts; the die composition must re-derive
the ages (as qkd_d2d_cal_seq's START_ADJ) before qualification.

Outputs OUTDIR/layer_roots.json (rows in the layer_programme.py profile shape + every event) and
OUTDIR/layer_programme_image.svh (LP_ROOTS[36*9*32], LP_DIGEST, LP_EPOCH) for the ROM variant.  Exit 1 on any rule
violation (assemble_rows of layer_programme.py is reused for the root legality checks).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

D2D_OUT = 1        # qkd_d2d_static PR wrapper: every output leaves one pin flop after the core (d2d_pinreg_gen.py)
RX_CMD = 2         # qkd_native_attention_static_ctl: compiled_rx_cmd >= 2 (minimum: CMD two edges after run)
Q_TO_START = 2     # qkd_native_attention_static_ctl header: service samples Q beat 0 two edges after the request
ISSUE_TO_RUN = 4   # qkd_static_kv_layer_programme: attention_run >= attention_issue + 4 (guard + descriptor load)
WRITER_T0 = 4      # qkd_kv_native_programme boot check: t0 >= 4 (first compiled word slot after its start)
LINK_START = 3     # earliest legal root
FIELDS = ('ctrl_go', 'kgo', 'vgo', 'attention_issue', 'attention_run', 'writer_start', 'link_start', 'expected_quiet',
          'stage_end')


def kv_lead(T):
    from qwen_static_schedule import kv_calendar as K
    base = dict(K.SOURCED, ring_cdc_core_edges=3, layer_period_core=6798, write_ready_core=0)
    q = dict(base, front_nblk=10, ring_depth=64, refresh=K.refresh_from_table())
    r = K.screen_36_capacity(T, q)
    if not r['capacity_feasible']:
        raise SystemExit(f'KV calendar capacity infeasible at T={T}')
    return r['layer']['qk_start_after_prefetch_core'], K._pv_start(T)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('caldir')
    ap.add_argument('out')
    ap.add_argument('--T', type=int, default=8192)
    ap.add_argument('--digest', type=lambda s: int(s, 0), default=0x123456789abcdef0)
    ap.add_argument('--epoch', type=int, default=3)
    a = ap.parse_args()
    cal = json.loads((Path(a.caldir) / 'calendar.json').read_text())
    prog = cal['program']
    lay = prog['layers']
    starts = [l['start'] for l in lay]                       # starts[0] = L0 inside the token run
    msgs = cal['messages']

    cmd = [m for m in msgs if m.get('seg', 0) == 0 and m['src'] == 'C' and m['rx_port'] == 0 and m['kind'] == 1]
    kvn = [m for m in msgs if m.get('seg', 0) == 0 and m['src'] == 'C' and m['rx_port'] == 3 and m['kind'] == 5]
    st = [m for m in msgs if m.get('seg', 0) == 0 and m['src'] == 'K' and m['tx_port'] == 0 and m['kind'] == 4]
    # L0 inside the token run must have the same layer-relative offsets (layer_msgs(1, l0_start, ...))
    cmd1 = [m for m in msgs if m.get('seg', 0) == 1 and m['src'] == 'C' and m['rx_port'] == 0 and m['kind'] == 1]
    if len(cmd) != 1 or len(cmd1) != 1 or len(st) != 1 or len(kvn) != 4 or cmd1[0]['rx_out'] - starts[0] != cmd[0]['rx_out']:
        raise SystemExit('link calendar: expected one CMD / STATUS and 4 KVN per layer run, L0 at the same layer offsets')
    lead, pvs = kv_lead(a.T)
    cmd_ev = cmd[0]['rx_out'] + D2D_OUT
    run = cmd_ev - RX_CMD
    issue = run - ISSUE_TO_RUN
    start_qk = run + RX_CMD + Q_TO_START
    kgo = start_qk - lead
    vgo = kgo + pvs
    writer = min(m['rx_out'] for m in kvn) + D2D_OUT - WRITER_T0
    quiet = st[0]['cyc'] + 1
    rel = dict(ctrl_go=kgo, kgo=kgo, vgo=vgo, attention_issue=issue, attention_run=run, writer_start=writer,
               link_start=LINK_START, expected_quiet=quiet)
    ends = [starts[1]] + [lay[s]['start'] - lay[s - 1]['start'] for s in range(2, 36)] + [lay[35]['cycles']]
    if lay[1]['start'] != prog['cal_starts'][1]['cycle']:
        raise SystemExit('link calendar layer starts differ from its cal_starts')
    rows = []
    for s in range(1, 37):
        base = starts[0] if s == 1 else 0
        roots = {k: (v + base if k != 'link_start' else v) for k, v in rel.items()}
        roots['stage_end'] = ends[s - 1]
        rows.append(dict(stage=s, roots=roots))
    from layer_programme import assemble_rows
    img = assemble_rows(rows, a.digest, a.epoch)              # the RTL's boot legality rules, in the compiler
    od = Path(a.out)
    od.mkdir(parents=True, exist_ok=True)
    words = img['words']
    vec = ''.join(f'{w:08x}' for w in reversed(words[:324]))
    (od / 'layer_programme_image.svh').write_text(
        '// GENERATED by tools/qwen_static_kv/layer_roots_from_link.py from the link compiler program calendar: do not edit\n'
        f'// T={a.T} kv_lead={lead} pv_start={pvs} COMPONENT_TEST (die path ages not measured)\n'
        f"localparam [36*9*32-1:0] LP_ROOTS = {36*9*32}'h{vec};\n"
        f"localparam [63:0] LP_DIGEST = 64'h{a.digest:016x};\n"
        f"localparam [15:0] LP_EPOCH = 16'd{a.epoch};\n")
    (od / 'boot.hex').write_text(''.join(f'{w:016x}\n' for w in words))
    rec = dict(schema='opentallas.qwen_kv_static.layer_roots_from_link.v1', status='COMPONENT_TEST_NOT_PRODUCTION_INSTALLABLE',
               T=a.T, kv_qk_start_after_prefetch=lead, pv_start=pvs, layer_relative=rel, start_qk=start_qk,
               constants=dict(D2D_OUT=D2D_OUT, RX_CMD=RX_CMD, Q_TO_START=Q_TO_START, ISSUE_TO_RUN=ISSUE_TO_RUN,
                              WRITER_T0=WRITER_T0, LINK_START=LINK_START),
               stage_end=ends, l0_base=starts[0], token_core_cycles=img['token_core_cycles'],
               link_token_cycles_through_L35=prog['token_cycles_through_L35'], rows=rows, events=img['events'],
               gaps=['die relay / pin ages between DCAL, the layer programme and its consumers are not measured',
                     'kgo / vgo use the T=8192 KV prefetch lead for every context (fixed image)'])
    if img['token_core_cycles'] != prog['token_cycles_through_L35']:
        raise SystemExit(f"frames {img['token_core_cycles']} != link token cycles {prog['token_cycles_through_L35']}")
    (od / 'layer_roots.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f"LAYER_ROOTS PASS T={a.T} rel={rel} l0_base={starts[0]} token_cycles={img['token_core_cycles']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
