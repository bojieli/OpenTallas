#!/usr/bin/env python3
"""Reattach landing collector sources after a reset-tree snapshot moved relays (DIE-QC-97 11-10, REMAP-REATTACH).

    python3 tools/die_plan/collector_reattach.py BASE_PLAN CAND_PLAN OUT_PLAN REPORT_JSON [--reach-um 405]
        [--sidecar SIDECAR_IN SIDECAR_OUT]

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

--sidecar: the strict bind reads the collector SOURCES from the asbuilt clock_landing_table (sidecar
collector.types[tn].local_sources / children), not from the plan; only the tree comes from the plan
(landing_collector.effective_tree).  a10 (cand21b2, plan sources reattached) still failed `cws1_i -> rst_n_t32` on
the stale sidecar.  With --sidecar the node/tap of every reattached type's sources and children is copied into the
sidecar (sources matched by name, children by index; any count or name mismatch -> exit 1 and no output).  Other
types and keys stay byte-identical, and the output keeps the sidecar's JSON style.

Rerooted collectors (collector_root_node a local relay, the monitor up-link source): the root keeps its SITE.  The new
root is the nearest same-depth relay of the new tree to the old root's site within reach (shift reported).  The tree
root, up pins and parent seam must be unchanged, otherwise exit 1.  cand21c slw_fw_v3 (struct form: 117 -> 239
relays) moved rst_n_t8 from (17.76, 273.12) to (583.71, 64.80).

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


def _reroot(blc, lc, reach_um):
    """A collector rooted at a local relay (collector_root_node != rst_root_n: the up-link source of a monitor edge)
    keeps its SITE, not its name: the new root is the nearest same-depth relay of the new tree to the old root's site,
    within reach_um.  The up pins and the parent seam stay where they are; the shift is reported (an up-edge hop grows
    by at most that much).  None when the collector is rooted at rst_root_n, or the old root keeps its name and site."""
    root = lc.get("collector_root_node", "rst_root_n")
    if root == "rst_root_n":
        return None
    if blc.get("collector_root_node", "rst_root_n") != root:
        raise ValueError(f"collector root changed name {blc.get('collector_root_node')} -> {root} between base and cand")
    ot, nt = blc["collector_tree"], lc["collector_tree"]
    if tuple(ot["root"]) != tuple(nt["root"]):
        raise ValueError("collector tree root moved; requires an explicit parent seam event")
    old = {r["q"]: r for r in ot["relays"]}
    if root not in old:
        raise ValueError(f"collector root {root} absent from the base tree")
    oxy, depth = old[root]["xy"], old[root]["depth"] + nt["depth"] - ot["depth"]
    new = {r["q"]: r for r in nt["relays"]}
    if root in new and new[root]["xy"] == oxy and new[root]["depth"] == depth:
        return None
    d = lambda r: abs(r["xy"][0] - oxy[0]) + abs(r["xy"][1] - oxy[1])
    best = sorted((d(r), q) for q, r in new.items() if r["depth"] == depth)
    if not best or best[0][0] > reach_um + 1e-6:
        raise ValueError(f"collector root {root}: no depth-{depth} relay within {reach_um}um of its site {oxy}")
    return dict(old_node=root, node=best[0][1], shift_um=round(best[0][0], 3), site_um=list(oxy), depth=depth)


def reattach_plan(base, cand, reach_um=405):
    """in place on cand -> report {reattached: {type: ...}, over: {type: [(name, node, hop)]}}"""
    rep = {"reattached": {}, "over": {}}
    for tn in sorted(cand.get("partition_types") or {}):
        lc = _lc(cand, tn)
        if lc is None:
            continue
        blc = _lc(base, tn)
        if blc is not None and blc["collector_tree"] != lc["collector_tree"]:
            reroot = _reroot(blc, lc, reach_um)
            info = dict(tree=copy.deepcopy(blc["collector_tree"]),
                        local_sources=copy.deepcopy(blc.get("collector_local_sources") or []),
                        children=copy.deepcopy(blc.get("collector_children") or []),
                        # the root (rst_root_n or a local relay) is validated by _reroot above: kept at its name and
                        # site, or re-picked at the old site; the sources then follow the tree from the delivered root.
                        # QC-VIS-RESITE 11-12: an UNCHANGED local root used to fall through to reattach_sources' blanket
                        # "rerooted collector" refusal (slw_stm_v1__cle34a73c3, rst_n_t8) while a MOVED one passed.
                        collector_root_node="rst_root_n")
            r = LCO.reattach_sources(info, lc["collector_tree"], reach_um=reach_um)
            lc["collector_local_sources"] = info["local_sources"]
            if "collector_children" in lc or info["children"]:
                lc["collector_children"] = info["children"]
            if reroot:
                lc["collector_root_node"] = reroot["node"]
            rep["reattached"][tn] = dict(added_collector_cycles=r["added_collector_cycles"],
                                         max_source_hop_um=r["max_source_hop_um"],
                                         moved=[x for x in r["sources"] if x["old_node"] != x["node"]],
                                         **(dict(rerooted=reroot) if reroot else {}))
        bad = [h for h in source_hops(lc) if h[2] is None or h[2] > reach_um + 1e-6]
        if bad:
            rep["over"][tn] = bad
    return rep


def sync_sidecar(cand, side, types):
    """in place on side: node/tap of each reattached type's collector sources/children from cand -> {type: n changed}"""
    st = (side.get("collector") or {}).get("types") or {}
    out = {}
    for tn in types:
        if tn not in st:
            raise ValueError(f"sidecar collector has no type {tn}")
        lc, row, n = _lc(cand, tn), st[tn], 0
        srcs, kids = row.get("local_sources") or [], row.get("children") or []
        by_name = {s["name"]: s for s in lc.get("collector_local_sources") or []}
        if sorted(by_name) != sorted(s["name"] for s in srcs):
            raise ValueError(f"sidecar {tn}: sources {sorted(s['name'] for s in srcs)} != plan {sorted(by_name)}")
        pk = lc.get("collector_children") or []
        if len(pk) != len(kids):
            raise ValueError(f"sidecar {tn}: {len(kids)} children, plan {len(pk)}")
        for s, q in [(s, by_name[s["name"]]) for s in srcs] + list(zip(kids, pk)):
            for k in ("node", "tap"):
                if k in q and s.get(k) != q[k]:
                    s[k] = q[k]
                    n += 1
        root = lc.get("collector_root_node")
        if root and row.get("collector_root_node") not in (None, root):
            row["collector_root_node"] = root            # collector_root_xy (the up-link site) stays
            n += 1
        out[tn] = n
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base"); ap.add_argument("cand"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--reach-um", type=float, default=405.0)
    ap.add_argument("--sidecar", nargs=2, metavar=("SIDECAR_IN", "SIDECAR_OUT"))
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
    side_out = None
    if a.sidecar:
        sb = Path(a.sidecar[0]).read_bytes()
        side = json.loads(sb)
        sdump = _style(sb, side)
        try:
            rep["sidecar_changed"] = sync_sidecar(cand, side, sorted(rep["reattached"]))
        except ValueError as e:
            print(f"COLLECTOR_REATTACH FAIL {e}")
            return 1
        side_out = sdump(side)
    Path(a.out).write_text(dump(cand))
    if side_out is not None:
        Path(a.sidecar[1]).write_text(side_out)
        rep["sidecar_sha256"] = hashlib.sha256(Path(a.sidecar[1]).read_bytes()).hexdigest()
    rep["sha256"] = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()
    Path(a.report).write_text(json.dumps(dict(rep, verdict="PASS"), indent=1) + "\n")
    print("COLLECTOR_REATTACH PASS " + " ".join(f"{t}:moved{len(v['moved'])}/+{v['added_collector_cycles']}cyc/"
                                                f"max{v['max_source_hop_um']:.1f}um" for t, v in rep["reattached"].items())
          + f" sha {rep['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
