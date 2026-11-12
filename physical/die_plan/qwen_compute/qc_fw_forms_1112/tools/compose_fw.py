#!/usr/bin/env python3
"""QC-FW-FORMS 11-12: compose the three fw forms onto the QC plan of record s25 (plan_qc99_s25, e4820bd9d97c).

  compose_fw.py BASE_S25 SLW_DERIVED HEAD_SLW V1_STRUCT V1_DERIVED SLE_DERIVED OUT REPORT

slw_fw_v3  = STRUCT-FWV3 re-derived on s25 (qc_struct_core on the s25 attempt_3 kit/geom) + fwderive C/S/F/P/R/H2 on the
             a20 struct-form pilot (SLW_DERIVED = that plan's slw type); hold_hb4 N=4 on the 7 in-buses the a20 pilot
             was measured with (HEAD_SLW = cand21c_hf lineage); clock.tap_pair_affinity.chains = true (u_pd4 delay
             chains join the pair graph, item 2); s25 keys landing_output_qreg [x_ctl_i] kept.
slw_fw_v1__clf51c11d8__clc7ddab13 = STRUCT-FWV3 on s25 (V1_STRUCT type) + fwderive C/H1/H2 measured on the s25-form
             attempt_3 placement / 4_cts (V1_DERIVED: clock keys except landing_contract, hold_hb4 per in-bus).
sle_fw_v3  = fwderive on the a21 pilot over the identical s25 type (SLE_DERIVED type; the base type is byte-equal).
Lane fixed_cycles are NOT set here (lanes2.py per type after this step)."""
import copy, hashlib, json, sys
base_f, slw_f, head_slw_f, v1s_f, v1d_f, sle_f, out_f, rep_f = sys.argv[1:9]
rb = open(base_f, "rb").read(); raw = json.loads(rb)
assert json.dumps(raw, indent=1).encode() == rb, "base style"
PT = raw["partition_types"]
ld = lambda f: json.load(open(f))["partition_types"]
SLW, V1, SLE = "slw_fw_v3", "slw_fw_v1__clf51c11d8__clc7ddab13", "sle_fw_v3"
rep = {}
# --- slw
d = copy.deepcopy(ld(slw_f)[SLW]); hs = ld(head_slw_f)[SLW]
assert d["clock"].get("landing_output_qreg") == PT[SLW]["clock"].get("landing_output_qreg") == ["x_ctl_i"]
hb = {b["name"]: b["hold_hb4"] for b in hs["buses"] if b.get("hold_hb4")}
for b in d["buses"]:
    if b["name"] in hb:
        assert "hold_hb4" not in b; b["hold_hb4"] = hb[b["name"]]
d["clock"]["tap_pair_affinity"]["chains"] = True
d["note"] = (d.get("note") or "") + " | QC-FW-FORMS 11-12: hold_hb4 4 on " + ",".join(sorted(hb)) + \
    " (a20 measured basis), tap_pair_affinity.chains"
rep[SLW] = dict(hold_hb4=hb, stations=len(d.get("internal_stations", [])), relay_sites=len(d.get("relay_sites", {})))
PT[SLW] = d
# --- v1
s = copy.deepcopy(ld(v1s_f)[V1]); m = ld(v1d_f)[V1]; b0 = PT[V1]
ck = {k: v for k, v in m["clock"].items() if k != "landing_contract" and b0["clock"].get(k) != v}
s["clock"].update(copy.deepcopy(ck))
hb1 = {b["name"]: b["hold_hb4"] for b in m["buses"] if b.get("hold_hb4")}
for b in s["buses"]:
    if b["name"] in hb1:
        assert "hold_hb4" not in b; b["hold_hb4"] = hb1[b["name"]]
fts = {f.get("name"): f.get("hold_hb4") for f in m.get("ft_slots", []) if f.get("hold_hb4")}
assert not fts, fts
s["note"] = (s.get("note") or "") + " | QC-FW-FORMS 11-12: STRUCT-FWV3 (qc_struct_core on s25 attempt_3) + fwderive C/H1/H2 " \
    "(attempt_3 4_cts): clock " + ",".join(sorted(ck)) + "; hold_hb4 " + json.dumps(hb1, sort_keys=True)
rep[V1] = dict(clock_keys=sorted(ck), hold_hb4=hb1, stations=len(s.get("internal_stations", [])), relay_sites=len(s.get("relay_sites", {})))
PT[V1] = s
# --- sle
e = copy.deepcopy(ld(sle_f)[SLE])
src_base = ld(sle_f)  # derived from head_anc, whose sle == s25 sle (checked by caller)
# ft_slots have no hold_hb4 key in the main schema (HOLDFORM-1 pads in-boundary bus flops only): the H1 ft row is dropped
# and reported (port-start hold, io_hold_parent at sign-off)
ftd = {f["name"]: f.pop("hold_hb4") for f in e.get("ft_slots", []) if "hold_hb4" in f}
rep[SLE] = dict(stations=len(e.get("internal_stations", [])), hold_hb4={b["name"]: b["hold_hb4"] for b in e["buses"] if b.get("hold_hb4")},
                ft_hold_hb4_dropped=ftd)
PT[SLE] = e
out = json.dumps(raw, indent=1)
open(out_f, "w").write(out)
rep["sha256"] = hashlib.sha256(out.encode()).hexdigest(); rep["base_sha256"] = hashlib.sha256(rb).hexdigest()
json.dump(rep, open(rep_f, "w"), indent=1, sort_keys=True)
print(json.dumps(rep)[:2000])
