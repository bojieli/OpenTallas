#!/usr/bin/env python3
"""HBM-ATTGAP (10-19): the DS attention WINDOW on the d4g SMs without per-token descriptor or programme changes.

Gap (VEH-ATT 10-19): the window ring (128 KV8 rows, ATT B.m = 128, param[8] ring) is read oldest first from slot
first = (POS1 - n) mod m (tools/hgi_sim/machine.py att_rows), so the head moves one row every token.  An SM run reads
a contiguous canonical line stream from a 64-line block start (ot_hbm_sm_kv_desc_static: one line run; the svg feed:
64-line blocks, ceil(rows*136/128)*4 sectors from the block's first sector).  A KV8 row is 528 B = 3 15/17 lines, so the
run that starts at head h starts 120*h mod 136 bytes into a line: a moving head is NOT a moving base.
  * per-token descriptor rewrite: cannot express the mid-line start (and the issuer table is write-locked while it
    runs; in a plain layer the window SMs leave wq_b ~97 cycles before attend.qk);
  * base-register-relative descriptors (issuer offset): same mid-line start -> would also need a start-skip in the SM
    KV realigner (ot_hbm_sm_kv_line, SM tile) and a sector-offset feed: two tile changes, both critical paths of
    closure.
CHOSEN (no RTL): WINDOW STAGING IN GOLDEN ORDER.  Each window SM keeps its sub-runs (positions [32j, 32j + 32) of the
window, j = 0..3 on sm_SW0 / sm_SW1 with the HBM-ATTGAP 32-row sub-runs) as STATIC canonical line streams (2 blocks a
sub-run, fixed bases) -> the ATT descriptors and programmes never change.  After a layer's attend.pv the DMA refreshes
that layer's staging for the next token: position i+1 -> i (127 rows, a row-granular copy through the VM; the row
crossing a sub-run / SM boundary moves between streams), and the next token's DMA.KVWB_DS window_row_append writes the
newest row at the FIXED last-row offset of sub-run 3 (critical path unchanged: one row write, as today).  The refresh
has a whole token of slack (it must land after this token's attend.pv and before the next token's append of the same
layer): it costs DMA / HBM-PC busy time, not token latency.

    att_window_staging.py check --kv DIR [--layer 2] [--tokens 300] --out J
checks, over `tokens` consecutive tokens with a moving head, that the staging maintained by (refresh, append) equals,
sub-run by sub-run, the canonical line stream of the rows machine.att_rows reads in golden order (bit for bit), and
reports the per-token DMA bytes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import att_images as AI  # noqa: E402

M, N, SUB = 128, 128, 32          # ring slots, window rows, rows a sub-run
ROW_B = 528


def canon(rowcode):
    codes, sc, _ = rowcode
    return AI.B.canon_row(codes, sc, 0)


def cmd_check(a):
    rec, src = AI.load_ds(Path(a.kv), a.layer)
    pool = rec["rows8"]                      # valid KV8 rows of the fixture (encodings decode bit-exact)
    # ring state: slot -> row id (pool index); the fixture's ring at capture (first = 0) holds pool rows 0..127
    ring = list(range(M))
    pos = M                                   # POS1 at capture: first = (pos - n) mod m = 0
    # staging: 4 sub-run byte streams of SUB rows each = rows of positions [32j, 32j+32) in golden order
    golden = lambda: [ring[(pos - N + i) % M] for i in range(N)]  # noqa: E731
    stage = [[golden()[SUB * j + i] for i in range(SUB)] for j in range(N // SUB)]
    moved, checks = 0, 0
    for t in range(a.tokens):
        # --- this token: the layer reads the staging; check it against the golden ring read, line stream exact
        g = golden()
        for j in range(N // SUB):
            want = AI.B.stream_lines(b"".join(canon(pool[r]) for r in g[SUB * j:SUB * (j + 1)]))
            got = AI.B.stream_lines(b"".join(canon(pool[r]) for r in stage[j]))
            if want != got:
                raise SystemExit(f"token {t} sub-run {j}: staging != golden ring read")
            checks += 1
        # --- after attend.pv: refresh for the next token (position i+1 -> i), then the next token's append
        flat = [r for s in stage for r in s]
        flat = flat[1:] + [None]
        moved += (N - 1) * ROW_B
        new = (37 * t + 11) % len(pool)       # the next token's new KV row (any valid KV8 row)
        pos += 1
        ring[(pos - 1) % M] = new             # machine: KVWB_DS writes slot POS mod m before the read of POS1 = pos
        flat[-1] = new
        stage = [flat[SUB * j:SUB * (j + 1)] for j in range(N // SUB)]
    lines_sub = len(AI.B.stream_lines(b"".join(canon(pool[r]) for r in stage[0])))
    doc = dict(schema="opentallas.hbm_att_window_staging.v1", lane="HBM-ATTGAP", source=src, tokens=a.tokens,
               subrun_rows=SUB, subruns=N // SUB, lines_per_subrun=lines_sub, blocks_per_subrun=-(-lines_sub // 64),
               checks=checks, verdict="PASS",
               refresh_bytes_per_layer_token=(N - 1) * ROW_B, append_bytes_per_layer_token=ROW_B,
               descriptor_rewrites_per_token=0, programme_rewrites_per_token=0,
               rule="staging sub-run j = canonical line stream of positions [32j, 32j+32) in golden (oldest-first) "
                    "order; refresh = position i+1 -> i through the VM (row granular, 132 VM words a row), append = the "
                    "newest row at sub-run 3 row 31 (fixed line offset 31*528 B)",
               not_chosen=dict(
                   descriptor_rewrite="a head h run starts 120*h mod 136 B into a line: not expressible by a line-run "
                                      "descriptor / 64-line block feed; issuer table write-locked while running",
                   base_register_relative="same mid-line start: needs a KV realigner start-skip (ot_hbm_sm_kv_line) + "
                                          "sector-offset feed besides the issuer offset (SM tiles)"))
    Path(a.out).write_text(json.dumps(doc, indent=1, default=int) + "\n")
    print("PASS HBM_ATT_WINDOW_STAGING " + json.dumps({k: v for k, v in doc.items() if k not in ("source", "not_chosen")}))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--kv", required=True)
    p.add_argument("--layer", type=int, default=2)
    p.add_argument("--tokens", type=int, default=300)
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return cmd_check(a)


if __name__ == "__main__":
    sys.exit(main())
