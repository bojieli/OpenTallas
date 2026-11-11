#!/usr/bin/env python3
"""HEAD-93 11-11: stage the prepared plan of the 12:00 HEAD event (what KW-FIX feeds head_wave_kit_rtl.py export).
l48hp1 is already prepared in content (count sites + private exports are in the raw plan: head_wave_kit_rtl.py prepare
refuses "count sites already placed"); the prepared snapshot differs from the raw plan only by (a) clock.sink_bins_file
pointing at the snapshot's assets/sink_bins_N.json copies and (b) the l48hp1_straps sites for hd_ctl / hd_serdes.
This script applies (a)+(b) to the composed plan and PROVES the procedure by reproducing the prepared l48hp1 plan
sha cf0fba5f053d from the raw l48hp1 plan first.
usage: prepare_cut.py ROOT COMPOSE_OUT PREP_HP1_DIR OUT
"""
import gzip, hashlib, json, shutil, sys
from pathlib import Path
R, CO, HP1, OUT = (Path(a).resolve() for a in sys.argv[1:5])
POR = R / "physical/die_plan/s81_head/plan_of_record"
sha = lambda b: hashlib.sha256(b).hexdigest()
hp1 = json.loads((HP1 / "source_plan.json").read_text())
sink = {t: v["clock"]["sink_bins_file"] for t, v in hp1["partition_types"].items() if "sink_bins_file" in v.get("clock", {})}
d = json.loads((POR / "l48hp1_straps/delta.json").read_text())


def prepare(raw_plan):
    p = json.loads(json.dumps(raw_plan))
    for t, f in sink.items():
        p["partition_types"][t]["clock"]["sink_bins_file"] = f
    for t, straps in d["count_straps"].items():
        by = {s["name"]: s for s in p["partition_types"][t]["count_straps"]}
        for name, v in straps.items():
            by[name].update(layer=v["layer"], sites_um=v["sites_um"])
    return p


raw0 = json.loads(gzip.open(POR / "l48hp1/source_plan.json.gz").read())
p0 = prepare(raw0)
# l48hp1_straps delta result = prepared l48hp1 + strap sites + hd_host_e raw pins; compare modulo the pins (straps base cf0fba5f)
h0 = json.loads(json.dumps(p0)); 
for nm, xy in d["landing_pins_xy_um"]["hd_host_e"].items():
    for x in h0["partition_types"]["hd_host_e"]["clock"]["landing_contract"]["pins"]:
        if x["name"] == nm: x["xy_um"] = xy
got = sha((json.dumps(h0, indent=1) + "\n").encode())
print("procedure check: raw l48hp1 -> prepared + straps + raw pins sha", got[:12], "expected", d["result_sha256"][:12], "OK" if got == d["result_sha256"] else "DIFFERS")
assert got == d["result_sha256"], "prepare procedure does not reproduce the l48hp1_straps event plan"
cut = json.loads((CO / "source_plan.json").read_text())
p = prepare(cut)
for t in ("hd_ctl", "hd_serdes"):
    hc = p["partition_types"][t].get("hard_cores", [])
    for name, v in d["count_straps"][t].items():
        for x, y in v["sites_um"]:
            for h in hc:
                w, hh = h["outline_um"] if h.get("orient", "R0") in ("R0", "MX", "MY", "R180") else h["outline_um"][::-1]
                if h["origin_um"][0] <= x <= h["origin_um"][0] + w and h["origin_um"][1] <= y <= h["origin_um"][1] + hh:
                    print("WARN strap site inside core", t, name, [x, y], h["inst"])
if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(HP1, OUT, ignore=shutil.ignore_patterns("source_plan.json"))
shutil.copy(POR / "l48hp1_h2/ot_s81hd_he_epc_pins.json", OUT / "core_pins/ot_s81hd_he_epc_pins.json")
OLD = "/srv/opentallas-scratch2/claude/kw42/prep_hp1/prep"
for v in p["partition_types"].values():           # self-contained snapshot: sink-bin pointers into this dir's assets copy
    c = v.get("clock", {})
    if c.get("sink_bins_file", "").startswith(OLD):
        c["sink_bins_file"] = str(OUT) + c["sink_bins_file"][len(OLD):]
text = json.dumps(p, indent=1) + "\n"
(OUT / "source_plan.json").write_text(text)
w = json.loads((OUT / "wave_prepare.json").read_text())
for k, v in w["native_sink_censuses"].items():
    v["path"] = str(OUT) + v["path"][len(OLD):]
w["prepared_plan_sha256"] = sha(text.encode())
w["l48hp1_head_cut1111"] = dict(event="HEAD 12:00 cut (HEAD-93): lepB+S03, ctl C1, start_q, H2, hp1 sites, hd_serdes 50 ps, per-port +10",
                                base_plan_sha256="7322511ff22a4741426044711ca11b2b52fe8afcb18f0abfed4d1080aa54a5e6",
                                raw_plan_sha256=sha((CO / "source_plan.json").read_bytes()), by="HEAD-93")
(OUT / "wave_prepare.json").write_text(json.dumps(w, indent=1) + "\n")
print("PREPARED cut plan sha256", sha(text.encode()))
