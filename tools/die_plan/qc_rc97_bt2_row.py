#!/usr/bin/env python3
"""QC-RC97-BT2 11-24: row RC97-BT2 (rc97 registered btab read on the st_a_v2 slices), for C1n.

rc97 = the btab macro read -> logic -> long reach class (FABLE-RC-QC 11-24 01:35: standing default form = REGISTERED read,
+1 cycle).  Row, per st_a_v2 type (the 6 slices E1 E3 E5 W1 W3 W5; st_a_v1 slices are not in this row):
  * verilog_defines += OT_BTAB_S4R  -> qfd_dv_s5_btab_s4 uses qfd_dv_s5_btab_safe_r: every SRAM rd_out bit captured in a
    flop at the macro, then the unchanged AND-OR + q capture; same SRAM instances (u_core.g_btb[k].u_m), +1 edge on bt_q;
  * region hard cores u_r0..u_r3 (param_wrap base qfd_dv_s8_station_tail1_nb0, BT_LAT 1) -> master <m>_bt2 with
    param_wrap BT_LAT 2 (every other param, outline, pins file, origin unchanged; same 494 pins), lef/lib -> the
    QC-RC97-BT2 view dir (NEEDS-BUILD until its private child kit signs off);
  * the paired st_b_v2 regions u_r4..u_r7 get BT_LAT 2 from the bind hook qc_fabric_transport (one BT_LAT per slice,
    fail closed without OT_BTAB_S4R): no plan field, but their type RTL changes (re-kit).
Latency: no lane, station or boundary stage changes (LATCHECK tables unchanged); +1 edge inside the slice on the bt
round trip, so each st region result r_v/r_d leaves 1 edge later: stn_transport result(s) +1 and busy(s) +1 on the six
slices (compiler schedule, DV_STN_TRANSPORT).

usage: rc97_bt2_row.py BASE_PLAN OUT_PLAN [--views-dir REL] [--delta OUT_DELTA.json]
"""
import argparse
import copy
import hashlib
import json

BASE = "qfd_dv_s8_station_tail1_nb0"
NOTE = ("QC-RC97-BT2 11-24 rc97: BT_LAT 2 master (registered btab read OT_BTAB_S4R on this type; "
        "+1 edge on the bt round trip), NEEDS-BUILD until its private child kit signs off")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--views-dir", default="physical/die_plan/qwen_compute/qcviews_rc97bt2")
    ap.add_argument("--delta")
    a = ap.parse_args()
    raw = open(a.base, "rb").read()
    p = json.loads(raw)
    q = copy.deepcopy(p)
    delta = {"row": "RC97-BT2", "base_sha256": hashlib.sha256(raw).hexdigest(), "types": {}, "masters": {}}
    for tn, t in sorted(q["partition_types"].items()):
        if "_st_a_v2" not in tn:
            continue
        rows = [h for h in t.get("hard_cores", []) if (h.get("param_wrap") or {}).get("base") == BASE]
        assert len(rows) == 4, (tn, len(rows))
        ch = []
        for h in rows:
            pr = h["param_wrap"]["params"]
            assert pr["BT_LAT"] == 1, (tn, h["inst"], pr)
            m0 = h["module"]
            assert h["physical_master"] == m0 and not m0.endswith("_bt2"), (tn, h["inst"], m0)
            m = m0 + "_bt2"
            pr["BT_LAT"] = 2
            h["module"] = h["physical_master"] = m
            h["lef"] = f"{a.views_dir}/{m}/{m}.lef"
            h["lib"] = f"{a.views_dir}/{m}/{m}_tt.lib"
            h["note"] = (h.get("note", "") + " | " + NOTE).lstrip(" |")
            delta["masters"].setdefault(m, {"from": m0, "params": dict(sorted(pr.items())), "pins_file": h["pins_file"],
                                            "outline_um": h["outline_um"], "rows": []})["rows"].append(f"{tn}.{h['inst']}")
            ch.append(f"{h['inst']}: {m0} -> {m} (BT_LAT 1 -> 2)")
        d = list(t.get("verilog_defines") or [])
        assert "OT_BTAB_S4R" not in d, tn
        t["verilog_defines"] = d + ["OT_BTAB_S4R"]
        ch.append("verilog_defines += OT_BTAB_S4R")
        delta["types"][tn] = ch
    slices = {}
    for pp in q["partitions"]:
        if pp["type"] in delta["types"]:
            slices[pp["name"].split("_")[1]] = pp["type"]
    st_b = {pp["name"].split("_")[1]: pp["type"] for pp in q["partitions"] if pp["name"].endswith("_st_b")}
    delta["slices"] = {s: {"st_a": slices[s], "st_b": st_b.get(s)} for s in sorted(slices)}
    delta["latency"] = {"lanes_changed": 0, "in_slice_edges": {s: 1 for s in sorted(slices)},
                        "compiler": "stn_transport result(s) +1, busy(s) +1 on these slices (qc_fabric_transport bt_lat)"}
    out = json.dumps(q, indent=1, sort_keys=False) + "\n"
    open(a.out, "w").write(out)
    delta["out_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    if a.delta:
        open(a.delta, "w").write(json.dumps(delta, indent=1) + "\n")
    print(json.dumps({"types": len(delta["types"]), "masters": {k: len(v["rows"]) for k, v in delta["masters"].items()},
                      "slices": delta["slices"], "base": delta["base_sha256"][:12], "out": delta["out_sha256"][:12]}))


if __name__ == "__main__":
    main()
