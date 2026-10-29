#!/usr/bin/env python3
"""DIE-KV-19 (2026-10-28) pv_pair (b2): KV as-built netlist with the per-lane-group red_issue / red_capture copy pins.

Exactly the netlist the shared column RTL produces with ot_qwen_tp8_pv_col LC=1 (rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv):
every bank tile ot_qwen_tp8_pv_slice_t #(.RESET_PIN(1)) X (.bc(N[h:l]), ...) becomes
ot_qwen_tp8_pv_slice_lc_t #(.G(4), .RESET_PIN(1)) X (.bc(N[h:l]), .bcx({N[l+18] x3, N[l+17] x3}), ...), i.e. the copy pins
take the SAME nets as bc[18] (red_capture) / bc[17] (red_issue) at the bank boundary (0 cycles; slice RTL proof
results/die_kv_14_1028/pv_pair/lec_result.txt; column bench results/die_kv_19_1028).  Nothing else changes (checked:
every other line is byte-identical, 512 tiles rewritten).

  kv_pv_lc_netlist.py            write die_bound_native_mission_lc.v.gz from die_bound_native_mission.v.gz
  kv_pv_lc_netlist.py --check    fail if the committed output is stale
"""
import gzip
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "die_bound_native_mission.v.gz"
OUT = HERE / "die_bound_native_mission_lc.v.gz"
RX = re.compile(r"^(\s*)ot_qwen_tp8_pv_slice_t #\(\.RESET_PIN\(1\)\) (\S+) \(\.bc\((\S+)\[(\d+):(\d+)\]\), (.*)$")
N_TILES = 512


def derive(text):
    out, n = [], 0
    for line in text.split("\n"):
        if "ot_qwen_tp8_pv_slice_t" not in line:
            out.append(line)
            continue
        m = RX.match(line)
        assert m, line[:200]
        ind, inst, net, hi, lo, rest = m.groups()
        hi, lo = int(hi), int(lo)
        assert hi - lo == 22, (inst, hi, lo)
        cap, iss = f"{net}[{lo + 18}]", f"{net}[{lo + 17}]"
        bcx = ", ".join([cap] * 3 + [iss] * 3)
        out.append(f"{ind}ot_qwen_tp8_pv_slice_lc_t #(.G(4), .RESET_PIN(1)) {inst} (.bc({net}[{hi}:{lo}]), "
                   f".bcx({{{bcx}}}), {rest}")
        n += 1
    assert n == N_TILES, n
    return "\n".join(out)


if __name__ == "__main__":
    txt = derive(gzip.decompress(SRC.read_bytes()).decode())
    if "--check" in sys.argv:
        ok = OUT.is_file() and gzip.decompress(OUT.read_bytes()).decode() == txt
        sys.exit(0 if ok else f"STALE {OUT}")
    OUT.write_bytes(gzip.compress(txt.encode(), mtime=0))
    print("wrote", OUT, N_TILES, "tiles")
