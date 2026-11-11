#!/usr/bin/env python3
"""Reattach landing collector sources after a reset-tree snapshot moved relays (DIE-QC-97 11-10, REMAP-REATTACH).

    python3 tools/die_plan/collector_reattach.py BASE_PLAN CAND_PLAN OUT_PLAN REPORT_JSON [--reach-um 405]

A plan writer that refreshes a type's published clock.landing_contract.collector_tree (a same-depth relay re-pick, a
new bins tree, a knee/station event) must move that type's collector_local_sources / collector_children with it: each
source names its reset node by tap index / relay name, and under the new tree the same name may sit somewhere else.
cand21b (sle_ctl__cl67434795 remap --snapshot, 62 relays re-picked) kept the old names and the strict bind failed with
`collector source cws1_i -> rst_n_t32: 1393.760um exceeds 405`.

For every type whose collector_tree differs between BASE and CAND this calls landing_collector.reattach_sources(old
tree -> new tree), which keeps each source's depth (no collector cycle change unless the tree depth changed, then
reported) and picks the nearest same-depth relay within reach.  Afterwards EVERY type's sources are reach-checked
against their own collector_tree (<= reach_um, the bind's landing_collector.build_local rule); any miss -> exit 1 and
no output.  Types whose collector_tree is unchanged are byte-identical; the output keeps CAND's JSON style.

Orthogonal to reset_anchor.py (RELAY-ANCHOR): that one re-picks the START / local-reset relay NAMES at bind time by
recorded site; this one moves the collector status sources in the plan when the tree snapshot itself is refreshed.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_collector as LCO  # noqa: E402


def _style(b, obj):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
              lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
        if f(obj).encode() == b:
            return f
    return lambda p: json.dumps(p, indent=1) + "\n"


def _lc(raw, tn):
    lc = (((raw.get("partition_types") or {}).get(tn) or {}).get("clock") or {}).get("landing_contract")
    return lc if isinstance(lc, dict) and isinstance(lc.get("collector_tree"), dict) else None


def source_hops(lc):
    """[(source name, node, hop_um or None when the node is absent)] for every collector source / child of lc"""
    t = lc["collector_tree"]
    xy = {"rst_root_n": t["root"], **{r["q"]: r["xy"] for r in t.get("relays", [])}}
    out = []
    for grp in ("collector_local_sources", "collector_children"):
        for s in lc.get(grp) or []:
            n = s.get("node", f"rst_n_t{s.get('tap', 0)}")
            if n not in xy:
                out.append((s.get("name"), n, None))
                continue
            pts = s.get("status_pins_xy_um", [s.get("xy_um", xy[n])])
            out.append((s.get("name"), n, max(abs(p[0] - xy[n][0]) + abs(p[1] - xy[n][1]) for p in pts)))
    return out


def reattach_plan(base, cand, reach_um=405):
    """in place on cand -> report {reattached: {type: ...}, over: {type: [(name, node, hop)]}}"""
    rep = {"reattached": {}, "over": {}}
    for tn in sorted(cand.get("partition_types") or {}):
        lc = _lc(cand, tn)
        if lc is None:
            continue
        blc = _lc(base, tn)
        if blc is not None and blc["collector_tree"] != lc["collector_tree"]:
            info = dict(tree=copy.deepcopy(blc["collector_tree"]),
                        local_sources=copy.deepcopy(blc.get("collector_local_sources") or []),
                        children=copy.deepcopy(blc.get("collector_children") or []),
                        collector_root_node=lc.get("collector_root_node", "rst_root_n"))
            r = LCO.reattach_sources(info, lc["collector_tree"], reach_um=reach_um)
            lc["collector_local_sources"] = info["local_sources"]
            if "collector_children" in lc or info["children"]:
                lc["collector_children"] = info["children"]
            rep["reattached"][tn] = dict(added_collector_cycles=r["added_collector_cycles"],
                                         max_source_hop_um=r["max_source_hop_um"],
                                         moved=[x for x in r["sources"] if x["old_node"] != x["node"]])
        bad = [h for h in source_hops(lc) if h[2] is None or h[2] > reach_um + 1e-6]
        if bad:
            rep["over"][tn] = bad
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base"); ap.add_argument("cand"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--reach-um", type=float, default=405.0)
    a = ap.parse_args(argv)
    rb = Path(a.cand).read_bytes()
    cand = json.loads(rb)
    dump = _style(rb, cand)                     # detected before the edit: keep CAND's serialisation
    base = json.loads(Path(a.base).read_text())
    try:
        rep = reattach_plan(base, cand, a.reach_um)
    except ValueError as e:
        print(f"COLLECTOR_REATTACH FAIL {e}")
        return 1
    if rep["over"]:
        Path(a.report).write_text(json.dumps(dict(rep, verdict="FAIL"), indent=1) + "\n")
        print(f"COLLECTOR_REATTACH FAIL sources over {a.reach_um:g} um: {rep['over']}")
        return 1
    Path(a.out).write_text(dump(cand))
    rep["sha256"] = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()
    Path(a.report).write_text(json.dumps(dict(rep, verdict="PASS"), indent=1) + "\n")
    print("COLLECTOR_REATTACH PASS " + " ".join(f"{t}:moved{len(v['moved'])}/+{v['added_collector_cycles']}cyc/"
                                                f"max{v['max_source_hop_um']:.1f}um" for t, v in rep["reattached"].items())
          + f" sha {rep['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
