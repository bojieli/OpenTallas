#!/usr/bin/env python3
"""What-if: the Qwen P8191 token (timing.py S2) with the SU / SFU record cost replaced by a D1-peer service model:
span + stage (sectors / rate) + compute (priced) + drain (sectors / rate), sequential or overlapped."""
import json, sys
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[1]; ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
from hgi_sim import timing as T, qwen_compiler as QC
from hgi_unitrate.su_census import span_secs

def d1_cost(span, rs, rd, overlap):
    def cf(r, dyn, L):
        c, g, how = T.cost(r, dyn, L)
        if r.unit not in ("SU", "SFU"): return c, g, how
        half = r.unit == "SU" and r.sut and r.sut.get("b_half")
        st = dr = 0
        for k, d in r.desc.items():
            if d.space != "VM": continue
            s, _ = span_secs(d, dyn, L, half and k in ("B", "D"))
            if k in ("O", "R"): dr += s
            else: st += s
        if overlap: return span + max(st / rs, c) + min(dr / rd, 64) + 8, g, how
        return span + st / rs + c + dr / rd, g, how
    return cf

cfg = json.loads((ROOT / "compiler/models/qwen3-8b/config.json").read_text())
q = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), cfg["num_hidden_layers"])
base = T.schedule(q, 8191, "S2")["total_cycles"]
print(f"priced {base:.0f} cyc {1.2e9/base:.1f} tok/s")
for nm, a in [("current D1 4-out (0.45 sec/cyc, span 200)", (200, 0.45, 0.45, False)),
              ("wide 32 sec/cyc sequential, span 10", (10, 32, 32, False)),
              ("wide 32 sec/cyc stage||compute, drain tail", (10, 32, 32, True)),
              ("wide 16 sec/cyc sequential", (10, 16, 16, False))]:
    s = T.schedule(q, 8191, "S2", cost_fn=d1_cost(*a))["total_cycles"]
    print(f"{nm:45s} {s:.0f} cyc {1.2e9/s:.1f} tok/s ({s/base:.3f}x)")
