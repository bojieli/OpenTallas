#!/usr/bin/env python3
"""QC-RC97V1 11-25: row RC97-V1 (+ BTLAT3 form) for the 6 st_a_v1 types of C1o (E0 E2 E4 W0 W2 W4), key-patch on the base plan.

The v1 regions are base qfd_dv_s8_station_tail1 (not _nb0), BT_LAT default 1.  Per st_a_v1 type:
  * verilog_defines += OT_BTAB_S4R, OT_BTAB_RQ (registered btab read + request-leg register at the SRAM stack; BT_LAT 3);
  * region hard cores u_r0..u_r3 <m> -> <m>_bt3, param_wrap BT_LAT 3 (all other params, outline, pins (560), origin kept),
    lef/lib -> --views-dir (NEEDS-BUILD until the private child kit signs off + LEC);
  * relay_sites: the u_sel.m[j] second-stage select seats the S4R btab adds (same grid as STA-BTSEAT) and the request flops
    rq_* at the midpoint of the u_r0 bt_word pins and the far bank (both hops <= 405 um, asserted), as STA-BTLAT3 does for v2.
The paired st_b regions take BT_LAT 3 from the bind hook (slice-wide, fail closed).  0 lane/station/boundary changes.
usage: qc_rc97v1_row.py BASE_PLAN OUT_PLAN OUT_ROW.json --pins-dir DIR [--views-dir REL]"""
import argparse, copy, hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qc_sta_btlat3_row as B

BASE = "qfd_dv_s8_station_tail1"
NOTE = ("QC-RC97V1 11-25: BT_LAT 3 master (OT_BTAB_S4R + OT_BTAB_RQ on this type; +2 edges on the bt round trip), "
        "NEEDS-BUILD until its private child kit signs off")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base"); ap.add_argument("out"); ap.add_argument("row")
    ap.add_argument("--pins-dir", required=True)
    ap.add_argument("--views-dir", default="physical/die_plan/qwen_compute/qcviews_btlat3")
    a = ap.parse_args()
    raw = open(a.base, "rb").read().decode()
    q = json.loads(raw)
    p0 = copy.deepcopy(q)
    row = {"row": "RC97-V1", "base_plan_sha": hashlib.sha256(raw.encode()).hexdigest()[:12], "types": {}, "masters": {}, "set": []}
    for tn, t in sorted(q["partition_types"].items()):
        if "_st_a_v1" not in tn:
            continue
        rs = t.setdefault("relay_sites", {})
        d = list(t.get("verilog_defines") or [])
        assert "OT_BTAB_S4R" not in d and "OT_BTAB_RQ" not in d, (tn, d)
        regs = [h for h in t["hard_cores"] if (h.get("param_wrap") or {}).get("base") == BASE]
        assert len(regs) == 4, (tn, len(regs))
        ch = row["types"].setdefault(tn, [])
        for h in regs:
            pr = h["param_wrap"]["params"]
            m0 = h["module"]
            assert "BT_LAT" not in pr and h["physical_master"] == m0 and not m0.endswith("_bt3"), (tn, h["inst"], m0, pr)
            m = m0 + "_bt3"
            pr["BT_LAT"] = 3
            h["module"] = h["physical_master"] = m
            h["lef"] = f"{a.views_dir}/{m}/{m}.lef"
            h["lib"] = f"{a.views_dir}/{m}/{m}_tt.lib"
            h["note"] = (h.get("note", "") + " | " + NOTE).lstrip(" |")
            row["masters"].setdefault(m, {"from": m0, "params": dict(sorted(pr.items())), "pins_file": h["pins_file"],
                                          "outline_um": h["outline_um"], "rows": []})["rows"].append(f"{tn}.{h['inst']}")
            ch.append(f"{h['inst']}: {m0} -> {m} (BT_LAT default 1 -> 3)")
        t["verilog_defines"] = d + ["OT_BTAB_S4R", "OT_BTAB_RQ"]
        ch.append("verilog_defines += OT_BTAB_S4R, OT_BTAB_RQ")
        # S4R adds the second-stage select copies u_sel.m[j]; the q seats already exist (STA-BTSEAT)
        t_s4r = copy.deepcopy(t)
        full = B.seat_rows(t_s4r, tn)
        newm = {k: v for k, v in full.items() if k not in rs}
        assert newm and all(".u_sel.m[" in k for k in newm), (tn, len(newm))
        assert all(rs[k] == v for k, v in full.items() if k in rs), tn
        rs.update(newm)
        rq, hops = B.rq_rows(t, tn, a.pins_dir)
        assert not set(rq) & set(rs), tn
        rs.update(rq)
        ch.append(f"relay_sites +{len(newm)} u_sel.m seats, +{len(rq)} request flops rq_*; hops u_r0 bt_word -> rq {hops[0]} um, rq -> far bank {hops[1]} um")
    # key-patch list (path -> value) vs the base
    for tn in row["types"]:
        a_, b_ = p0["partition_types"][tn], q["partition_types"][tn]
        for i, (h0, h1) in enumerate(zip(a_["hard_cores"], b_["hard_cores"])):
            if h0 != h1:
                for k in h1:
                    if h0.get(k) != h1[k]:
                        row["set"].append({"path": f"partition_types.{tn}.hard_cores[{i}].{k}", "inst": h1["inst"], "value": h1[k]})
        row["set"].append({"path": f"partition_types.{tn}.verilog_defines", "value": b_["verilog_defines"]})
        for k, v in b_["relay_sites"].items():
            if k not in a_["relay_sites"]:
                row["set"].append({"path": f"partition_types.{tn}.relay_sites[{k}]", "value": v})
    bt = set(row["types"])
    row["slices"] = {pp["name"].split("_")[1]: pp["type"] for pp in q["partitions"] if pp["type"] in bt}
    row["latency"] = {"lanes_changed": 0, "core_latency_changed": 0, "in_slice_edges_vs_btab_safe": {s: 2 for s in sorted(row["slices"])},
                      "compiler": "stn_transport result(s) +2, busy(s) +2 on these slices (hook record bt_lat 3)"}
    ind = 2 if raw.startswith('{\n  "') else (1 if raw.startswith('{\n "') else None)
    txt = json.dumps(q, indent=ind) + ("\n" if raw.endswith("\n") else "")
    open(a.out, "w").write(txt)
    row["out_plan_sha"] = hashlib.sha256(txt.encode()).hexdigest()[:12]
    json.dump(row, open(a.row, "w"), indent=1)
    print(json.dumps({"types": {k: len(v) for k, v in row["types"].items()}, "masters": {k: len(v["rows"]) for k, v in row["masters"].items()},
                      "slices": row["slices"], "set": len(row["set"]), "base": row["base_plan_sha"], "out": row["out_plan_sha"]}))


if __name__ == "__main__":
    main()
