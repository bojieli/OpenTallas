#!/usr/bin/env python3
"""HBM-BIND-13: split the SU cuts' merged `bank_rst_n` into the source/kit reset inputs (fail-closed).

The as-built top ties su_*'s rst_n, rst_lane_n[*] and rst_bcast_n[*] to one POR net, so the Codex native compose
merged every reset terminal of an SU cut into one input `bank_rst_n`.  Source (ot_hbm_su_static_pgslice_s.sv) and the
plan kits (sw2.py wrappers, e.g. ot_hbm_su_static_pgslice_lg__lane_exp0.sv: .bank_rst_n(rst_n), .lane_rst_n(rst_lane_n))
keep them apart:
  rst_n          <- g_bank[n].u_bank.rst_n            (slice rst_n; the plan core reset target, kit pin rst_n)
  rst_lane_n[k]  <- g_lane[n_k].g_pr.u_lane.rst_n      (rst_lane_n[n]; kit pin rst_lane_n[k], lanes in ascending n)
  rst_bcast_n    <- ARST of the g_bcast[n/8] ctl replica flops (pgslice_s.sv:135, rst_bcast_n[b]; not a kit pin:
                    the kit has these flops outside the core, the as-built cut has them inside)
Every terminal keeps its as-built net (bind_compose allows several input ports on one original net when all its
input terminals are mapped); nothing is tied.  Modules are renamed (structure changes).
usage: mk_compose_rst.py COMPOSE_IN YOSYS_JSON COMPOSE_OUT REPORT"""
import json, re, sys
src, yjs, dst, repf = sys.argv[1:5]
C = json.load(open(src))
RENAME = {"ot_hnx_su_exp__efa9ca4d9700": "ot_hnx_su_exp__rst3", "ot_hnx_su_plain4__lid9": "ot_hnx_su_plain4__lid9_rst3",
          "ot_hnx_su_plain4__7dd6a1bbbf47": "ot_hnx_su_plain4__7dd6a1bbbf47_rst3"}
want = set()
for core in C["cores"]:
    if core["module"] in RENAME:
        for b in core["ports"]["bank_rst_n"]["bits"]:
            want |= {a["member"].split(".")[-2] for a in b if a["port"] == "ARST"}
Y = json.load(open(yjs))["modules"]
srcs = {}
for mn, m in Y.items():
    if "ot_hbm_su_static_pgslice_s" in mn:
        for cn, c in m["cells"].items():
            if cn in want:
                srcs.setdefault(cn, set()).add(c["attributes"].get("src", "").rsplit("/", 1)[-1])
bad = {k: v for k, v in srcs.items() if v != {"ot_hbm_su_static_pgslice_s.sv:135.4-136.56"}}
assert set(srcs) == want and not bad, (sorted(want - set(srcs))[:5], bad)
rep = dict(changed=[], renames=RENAME, flop_src="ot_hbm_su_static_pgslice_s.sv:135.4-136.56 (rst_bcast_n[b] ctl replicas)")
lane_re = re.compile(r"\.u_slice\.g_lane\[(\d+)\]\.g_pr\.u_lane$")
for core in C["cores"]:
    if core["module"] not in RENAME:
        continue
    P = core["ports"]
    assert "bank_rst_n" in P and not ({"rst_n", "rst_lane_n", "rst_bcast_n"} & set(P)), core["inst"]
    p = P.pop("bank_rst_n")
    assert p["dir"] == "input" and len(p["bits"]) == 1, core["inst"]
    bank, lanes, flops = [], {}, []
    for a in p["bits"][0]:
        if a["member"].endswith(".u_bank") and ".u_slice.g_bank[" in a["member"] and a["port"] == "rst_n":
            bank.append(a)
        elif (m := lane_re.search(a["member"])) and a["port"] == "rst_n":
            assert int(m[1]) not in lanes
            lanes[int(m[1])] = a
        elif a["port"] == "ARST" and ".u_slice.$procdff$" in a["member"]:
            flops.append(a)
        else:
            raise SystemExit(f"{core['inst']}: unexpected reset terminal {a}")
    assert bank and lanes and flops, core["inst"]
    assert len({n // 8 for n in lanes}) == 1, core["inst"]          # one g_bcast[b] for the cut's lanes
    P["rst_n"] = dict(dir="input", bits=[bank])
    P["rst_lane_n"] = dict(dir="input", bits=[[lanes[n]] for n in sorted(lanes)])
    P["rst_bcast_n"] = dict(dir="input", bits=[flops])
    old = core["module"]
    core["module"] = RENAME[old]
    rep["changed"].append(dict(inst=core["inst"], old=old, new=core["module"], banks=len(bank), lanes=sorted(lanes),
                               flops=len(flops), bcast=sorted(lanes)[0] // 8))
json.dump(C, open(dst, "w"))
rep["n_changed"] = len(rep["changed"])
json.dump(rep, open(repf, "w"), indent=1)
import collections
print("changed", rep["n_changed"], collections.Counter(c["new"] for c in rep["changed"]))
