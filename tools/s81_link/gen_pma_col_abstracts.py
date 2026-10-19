#!/usr/bin/env python3
"""TW7-S81SERDES 10-19: the S81 SerDes analog PMA of the column parent ot_pdie_serdes_col as TWO hard abstracts side by side
(tools/chip_assembly/macros.py: one clock per macro), modelled per owner rule (hard PHY analog may be behavioural):
  ot_s81_pma_rxm  W half: pads pma_rx + recovered clock pma_rck on W (die edge), q[543:0] on N (to the decoder column's p_d);
                  E face bare (abuts txm: abutted_row, no channel)
  ot_s81_pma_txm  E half: lane d_v / d[543:0] and the forwarded lane clock ck on N (clock_edge N: its W face abuts rxm, the
                  old macros.py always put the clock on W -> unreachable), pads pma_tx / pma_tck on S; W face bare.
                  pma_tck = ck pass-through: untimed pin.
Width default 129.024 (0.048 grid; two halves in a 302.4 column with 22.16-um edge channels); height 2250.216 (plan).
usage: gen_pma_col_abstracts.py [--w 129.024] [--h 2250.216] [--out physical/s81_pma_col]"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chip_assembly"))
import macros as M

def specs(w, h):
    rx = M.MacroSpec("ot_s81_pma_rxm", w, h, [M.Pin("pma_rx", "input", 544, "W", span=(20.0, h - 20.0)),
                                               M.Pin("q", "output", 544, "N", span=(4.0, w - 4.0))],
                     clock="pma_rck", clock_edge="W", clock_span=(h - 12.0, h - 8.0), kind="analog_pma",
                     basis="S81 SerDes PMA RX half (modelled analog, ot_s81_pma_bm LAT 4 behaviour)")
    tx = M.MacroSpec("ot_s81_pma_txm", w, h, [M.Pin("d_v", "input", 1, "N", span=(8.0, 12.0)),
                                               M.Pin("d", "input", 544, "N", span=(14.0, w - 4.0)),
                                               M.Pin("pma_tx", "output", 544, "S", span=(4.0, w - 12.0)),
                                               M.Pin("pma_tck", "output", 1, "S", timed=False, span=(w - 10.0, w - 6.0))],
                     clock="ck", clock_edge="N", clock_span=(4.0, 7.0), kind="analog_pma",
                     basis="S81 SerDes PMA TX half (modelled analog, ot_s81_pma_bm LAT 4 behaviour)")
    return rx, tx

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--w", type=float, default=129.024); ap.add_argument("--h", type=float, default=2250.216)
    ap.add_argument("--out", default="physical/s81_pma_col"); a = ap.parse_args()
    root = Path(__file__).resolve().parents[2]; rec = {}
    for s in specs(a.w, a.h):
        p = M.write_views(s, root / a.out / s.name)
        rec[s.name] = dict(M.describe(s), clock=s.clock, clock_edge=s.clock_edge, files={k: str(v.relative_to(root)) for k, v in p.items()})
    (root / a.out / "abstracts.json").write_text(json.dumps(rec, indent=1) + "\n"); print(json.dumps(rec, indent=1))

if __name__ == "__main__":
    main()
