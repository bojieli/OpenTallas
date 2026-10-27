#!/usr/bin/env python3
"""CLOCK-KV-R22: face clock entry of the signed head-eighth cores vs the 12.3 band (COORD RULING CLOCK-KV-R21 04:02 ASK2,
same rule as HEAD elemB INFRA-FIRST-HEAD-2 02:34).

For every plan core tap that CLOCK-KV-R21 placed on a signed view's face clock pin (kv_r21/view_core_taps.py report),
read the signed view's ROUTED RCX insertion (native clock pin -> sinks; VIEWDIR/<module>.core.json
clock_latency_measured = the sign-off STA on post-route SPEF, sta_<c>.json parasitics "spef"; cross-checked with the
ETM <module>_<c>.lib min/max_clock_tree_path) and judge it with master_plan.signed_face_entry_check (mean within
common +- 20 TT/FF).  Rows in band get the declared signed_face_entry form on their plan tap (--apply OUT_PLAN);
rows out of band are listed for a centre-entry rebuild (KV-CORES-R3).
usage: face_entry_rcx.py PLAN.json TAPS_REPORT.json OUT_REPORT.json [--apply OUT_PLAN.json] --core-view MODULE=DIR"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import die_sta_related as R
import master_plan as MP
import schema as S


def view_rcx(module, vd):
    vd = Path(vd)
    prov = json.loads((vd / "provenance.json").read_text())
    if "SIGNED" not in str(prov.get("verdict", "")):
        raise SystemExit(f"{module}: {vd} not signed off ({prov.get('verdict')})")
    cj = json.loads((vd / f"{module}.core.json").read_text())
    meas = cj["clock_latency_measured"]
    rcx, etm, para = {}, {}, {}
    for c in ("TT", "FF"):
        m = meas[c.lower()]
        rcx[c] = dict(mean=m["mean"], min=m["min"], max=m["max"], n=m["n"], spread=m["spread"])
        e = R.parse_etm(vd / f"{module}_{c.lower()}.lib", 6.0)
        etm[c] = e["clock_tree_path_ps"]
        para[c] = json.loads((vd / f"sta_{c.lower()}.json").read_text()).get("parasitics")
        if para[c] != "spef":
            raise SystemExit(f"{module}: sta_{c.lower()}.json parasitics {para[c]!r}, not routed SPEF")
    sha = {c: hashlib.sha256((vd / f"{module}_{c}.lib").read_bytes()).hexdigest() for c in ("tt", "ff")}
    return dict(view=str(vd), verdict=prov["verdict"], lib_sha256=sha,
                lef_sha256=hashlib.sha256((vd / f"{module}.lef").read_bytes()).hexdigest(),
                core_json_sha256=hashlib.sha256((vd / f"{module}.core.json").read_bytes()).hexdigest(),
                rcx_insertion_ps=rcx, etm_clock_tree_path_ps=etm, parasitics=para,
                source="core.json clock_latency_measured (sign-off STA, post-route RCX SPEF), pin -> sinks",
                clock_pin=json.loads((vd / "provenance.json").read_text())["kit"]["clock_nets"]["clk"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("taps_report"); ap.add_argument("out_report")
    ap.add_argument("--apply", help="write OUT_PLAN with signed_face_entry on the in-band rows")
    ap.add_argument("--core-view", action="append", default=[])
    a = ap.parse_args(argv)
    raw = Path(a.plan).read_bytes()
    P = S.Plan(S.load(a.plan))
    rep_in = json.loads(Path(a.taps_report).read_text())
    views = {}
    for kv in a.core_view:
        m, d = kv.split("=", 1)
        views[m] = view_rcx(m, d)
    rows, accept = [], {}
    for r in rep_in["tapped"]:
        v = views[r["module"]]
        if v["clock_pin"] != r["pin"]:
            raise SystemExit(f"{r['type']}.{r['inst']}: tap pin {r['pin']} != view clock pin {v['clock_pin']}")
        sfe = dict(view=Path(v["view"]).name, lib_sha256=v["lib_sha256"], lef_sha256=v["lef_sha256"],
                   rcx_insertion_ps=v["rcx_insertion_ps"], source=v["source"], ruling="COORD CLOCK-KV-R21 04:02 ASK2")
        ok, rec, issues = MP.signed_face_entry_check(P, sfe)
        rows.append(dict(type=r["type"], inst=r["inst"], module=r["module"], pin=r["pin"],
                         die_instances=r["die_instances"], tt_mean=rec["TT"]["mean"], ff_mean=rec["FF"]["mean"],
                         tt_band=rec["TT"]["band"], ff_band=rec["FF"]["band"], in_band=ok,
                         action="ACCEPT signed face entry" if ok else "REBUILD centre entry (KV-CORES-R3)",
                         issues=issues))
        if ok:
            accept[(r["type"], f"{r['inst']}.{r['pin']}")] = sfe
    out = dict(lane="CLOCK-KV-R22", plan=a.plan, plan_sha256=hashlib.sha256(raw).hexdigest(), rule=__doc__,
               views={m: {k: x for k, x in v.items()} for m, v in views.items()}, rows=rows)
    di = lambda rr: sum(x["die_instances"] for x in rr)
    out["summary"] = dict(rows=len(rows), in_band=sum(x["in_band"] for x in rows),
                          out_of_band=sum(not x["in_band"] for x in rows),
                          die_instances_in_band=di([x for x in rows if x["in_band"]]),
                          die_instances_out_of_band=di([x for x in rows if not x["in_band"]]),
                          by_module={m: dict(rows=sum(x["module"] == m for x in rows),
                                             in_band=sum(x["module"] == m and x["in_band"] for x in rows),
                                             tt_mean=views[m]["rcx_insertion_ps"]["TT"]["mean"],
                                             ff_mean=views[m]["rcx_insertion_ps"]["FF"]["mean"]) for m in views})
    if a.apply:
        J = json.loads(raw)
        n = 0
        for (tn, name), sfe in accept.items():
            for tp in J["partition_types"][tn]["clock"]["taps"]:
                if tp["name"] == name:
                    tp["signed_face_entry"] = sfe
                    n += 1
        s = json.dumps(J, indent=1)
        Path(a.apply).write_text(s)
        out["applied"] = dict(taps=n, out_plan_sha256=hashlib.sha256(s.encode()).hexdigest())
    Path(a.out_report).write_text(json.dumps(out, indent=1))
    print(json.dumps(out["summary"]))


if __name__ == "__main__":
    sys.exit(main())
