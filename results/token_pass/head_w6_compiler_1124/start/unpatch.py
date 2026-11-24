#!/usr/bin/env python3
"""HEAD-R18 11-24: invert head_start_local_reset.patch + relay_over.py on a START provider (canonical emit form:
one global rst_raw_n), then prove the inversion by re-applying the provider's own reset rows (round trip byte-equal).
usage: unpatch.py PROVIDER_DIR TOOLS_ROOT OUT_DIR"""
import copy, gzip, json, re, sys
from pathlib import Path
I, M, O = map(Path, sys.argv[1:4])
sys.path[:0] = [str(M / "tools/s81_head")]
import head_start_local_reset as LR
rd = lambda n: (gzip.open(I / (n + ".gz")).read().decode() if (I / (n + ".gz")).exists() else (I / n).read_text())
doc = json.loads(rd("start_stages.json")); sv = rd("start_stages.sv")
# step A: undo relay_over.py (one ot_dp_rrelay per over-reach stage, binding rrly_<id>)
base = copy.deepcopy(doc); s1 = sv; relayed = []
for s in base["stages"]:
    r = s.pop("reset_relay", None)
    if r is None:
        continue
    w = r["net"]; inst = r["instance"]
    line = re.compile(r"    wire " + re.escape(w) + r";\n    ot_dp_rrelay " + re.escape(inst) + r" \(\.clk\(" + re.escape(s["clock_port"])
                      + r"\), \.d\(" + re.escape(s["reset_port"]) + r"\), \.q\(" + re.escape(w) + r"\)\);[^\n]*\n")
    s1, n = line.subn("", s1); assert n == 1, (s["id"], "relay lines", n)
    pat = r"(\.clk\(" + re.escape(s["clock_port"]) + r"\), \.rst_raw_n\()" + re.escape(w) + r"(\))"
    s1, n = re.subn(pat, lambda m: m[1] + s["reset_port"] + m[2], s1); assert n == 1, (s["id"], "relay binding", n)
    relayed.append(s["id"])
assert len(relayed) == doc.get("reset_relays", 0), (len(relayed), doc.get("reset_relays"))
base.pop("reset_relays", None); base["root_settle_guard"].pop("raw_relative_span_with_relays", None)
c = copy.deepcopy(base); s2 = s1
doc_full, sv_full = doc, sv
doc, sv = base, s1
for s in c["stages"]:
    name = s["reset_port"]
    pat = r"(\.clk\(" + re.escape(s["clock_port"]) + r"\), \.rst_raw_n\()" + re.escape(name) + r"(\))"
    s2, n = re.subn(pat, lambda m: m[1] + "rst_raw_n" + m[2], s2)
    assert n == 1, (s["id"], n)
    for k in ("reset_port", "reset_source", "reset_hop_um"):
        s.pop(k, None)
ports = sorted(doc["reset_ports"])
block = "".join(f"    input  wire {p},\n" for p in ports)
assert s2.count(block) == 1
s2 = s2.replace(block, "    input  wire rst_raw_n,\n")
prev = doc["root_settle"] - doc["root_settle_guard"]["added_boot_cycles"]
for k in ("reset_form", "reset_ports", "reset_qualification", "root_settle_guard"):
    c.pop(k, None)
c["root_settle"] = prev
# round trip: the provider's own rows as exports
rows = [dict(stage=s["id"], stage_region=s["region"], source=s["reset_source"], hop_um=s["reset_hop_um"]) for s in doc["stages"]]
root = next(s for s in doc["stages"] if s["root"])
rel = max(s["reset_source"]["raw_release"] - root["reset_source"]["raw_release"] for s in doc["stages"])
ex = dict(stages=rows, summary=dict(over_hop=[], max_relative_raw_release=rel))
d3, s3 = LR.patch(c, s2, ex, doc["root_settle"])
assert s3 == sv, "SV round trip differs"
assert json.dumps(d3, sort_keys=True) == json.dumps(doc, sort_keys=True), "JSON round trip differs"
print(json.dumps(dict(relays_undone=len(relayed), relay_stages=relayed)))
O.mkdir(parents=True, exist_ok=False)
(O / "start_stages.json").write_text(json.dumps(c, indent=1)); (O / "start_stages.sv").write_text(s2)
for n in ("ctree.v", "ctree.tcl"):
    (O / n).write_bytes((I / n).read_bytes())
print(json.dumps(dict(UNPATCH="OK_ROUNDTRIP_PATCH", stages=len(c["stages"]), prev_settle=prev, provider_settle=doc["root_settle"], span=rel)))
