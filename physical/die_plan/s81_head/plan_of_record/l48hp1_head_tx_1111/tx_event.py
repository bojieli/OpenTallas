#!/usr/bin/env python3
"""HEAD-94 11-11: TX_STAGE=1 plan event (hd_host_w a3, COORD 'TX_STAGE approved').
 ot_s81hd_host_w_core TX_STAGE=1 adds ONE register stage on every host276 h_rx_o frame: the plan declares it as fixed_cycles +1 on the
 host_rx lane (host_w.h_rx_o -> host_nstrip -> sp5..sp0 -> ctl.h_rx_i), same convention as head_host_split_delta INGRESS_FIXED /
 EGRESS_FIXED; the latency table and the generated lat package (LAT_HD_HOST_RX 58 -> 59) are regenerated with gen.write_latency.
 usage: tx_event.py REPO BASE_PLAN.json[.gz] OUT_DIR   (OUT_DIR/source_plan.json, OUT_DIR/lat/*)"""
import gzip, json, sys, copy
from pathlib import Path
R = Path(sys.argv[1]).resolve(); src = Path(sys.argv[2]); out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(R / "tools/die_plan"))
import gen as G
raw = json.loads(gzip.open(src).read() if src.suffix == ".gz" else src.read_bytes())
# consistency of the base: regenerate the table, it must equal the plan's own latency block
tab0, _, _ = G.write_latency(copy.deepcopy(raw), out / "lat_base")
old = raw["latency"]["lanes"]
bad = [k for k, v in tab0.items() if k in old and any(v.get(f) != old[k].get(f) for f in ("cycles", "fixed", "natural"))]
print("base latency table vs plan latency block: %d lanes compared, %d differ %s" % (len(tab0), len(bad), bad[:5]))
ln = [l for l in raw["lanes"] if l["id"] == "host_rx"]
assert len(ln) == 1
ln[0]["fixed_cycles"] = int(ln[0].get("fixed_cycles", 0)) + 1
tab, pkg, js = G.write_latency(copy.deepcopy(raw), out / "lat")
for f in ("cycles", "fixed", "natural"):
    raw["latency"]["lanes"]["host_rx"][f] = tab["host_rx"][f]
print("lane cycle changes: host_rx", old["host_rx"]["cycles"] if False else tab["host_rx"]["cycles"] - 1, "->", tab["host_rx"]["cycles"])
(out / "source_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
print("TX event plan written; pkg", pkg)
