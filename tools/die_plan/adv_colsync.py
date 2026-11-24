"""adv_colsync.py -- PRECHECK ADV-COLSYNC (COORD 11-24, QC-OPEN-SU COLSYNC-SU hub 4e34fc48; report only).

The strict bind reads the landed SIDECAR's collector nodes (sidecar collector.types[<t>].children / local_sources / collector_root_node);
landing_place and the kit generator read the PLAN's clock.landing_contract.collector_children[].node / collector_local_sources[].node /
collector_root_node.  Both are tap-INDEX keyed; when a type's tap count changes the plan copy goes 4-8 indices stale: strict passes, kit gen
dies with KeyError rst_n_t88 or the row points 230-1390 um from its source (QC su_c C1g).

For every type with a landing_contract and a sidecar row, per plan row:
  DIFF      node != the sidecar's node for the same child index / source name (root: collector_root_node)
  MISSING   the plan node is not a relay of the type's own collector_tree (and is not rst_root_n)
  FAR       the node's relay site is more than REACH_UM (405) from the row's xy_um
Sidecar: kw sidecar= / env OT_ADV_COLSYNC_SIDECAR, else the newest *sidecar*.json under <tree>/physical/die_plan/*/*/runtime holding a
`collector` section (the file used is named in the summary).  findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import glob
import json
import os
import sys
from pathlib import Path

CHECK = "ADV-COLSYNC"
REACH_UM = 405.0
MAX_LINES = 25


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def judge_type(lc, st):
    """lc = plan landing_contract, st = sidecar collector.types[t] -> (n_diff, n_missing, n_far, rows_checked, worst_far_um, sample)"""
    R = {r.get("q"): r for r in ((lc.get("collector_tree") or {}).get("relays") or [])}
    nd = nm = nf = nr = 0
    worst, sample = 0.0, None
    for g, sg, k in (("collector_children", "children", "index"), ("collector_local_sources", "local_sources", "name")):
        sm = {r.get(k): r for r in st.get(sg) or []}
        for r in lc.get(g) or []:
            nr += 1
            node, xy = r.get("node"), r.get("xy_um")
            s = sm.get(r.get(k))
            bad = []
            if s is not None and s.get("node") != node:
                nd += 1
                bad.append(f"{g}[{r.get(k)}] {node} != sidecar {s.get('node')}")
            if node not in R and node != "rst_root_n":
                nm += 1
                bad.append(f"{g}[{r.get(k)}] {node} not in the type's tree")
            elif node in R and xy:
                h = man(R[node]["xy"], xy)
                if h > REACH_UM:
                    nf += 1
                    worst = max(worst, h)
                    bad.append(f"{g}[{r.get(k)}] {node} {h:.0f} um from its row")
            if bad and sample is None:
                sample = "; ".join(bad)
    nr += 1
    if lc.get("collector_root_node") != st.get("collector_root_node") and st.get("collector_root_node") is not None:
        nd += 1
        sample = sample or f"root {lc.get('collector_root_node')} != sidecar {st.get('collector_root_node')}"
    return nd, nm, nf, nr, worst, sample


def _find_sidecar(tree, kw):
    p = kw.get("sidecar") or os.environ.get("OT_ADV_COLSYNC_SIDECAR")
    if p:
        return str(p)
    c = sorted(glob.glob(str(Path(tree) / "physical" / "die_plan" / "*" / "*" / "runtime" / "*sidecar*.json")), key=os.path.getmtime, reverse=True)
    c += sorted(glob.glob(str(Path(tree) / "physical" / "die_plan" / "*" / "*sidecar*.json")), key=os.path.getmtime, reverse=True)
    for f in c[:6]:
        try:
            if os.path.getsize(f) < 200_000_000 and '"collector"' in Path(f).read_text()[:50_000_000]:
                return f
        except OSError:
            continue
    return None


def _findings(raw, plan_path, tree=None, **kw):
    sc = kw.get("sidecar_obj")
    path = None
    if sc is None:
        path = _find_sidecar(tree, kw) if tree or kw.get("sidecar") else None
        if not path:
            return [_w("NOT-RUN: no landed sidecar with a collector section found (pass sidecar= / OT_ADV_COLSYNC_SIDECAR)")]
        sc = json.loads(Path(path).read_text())
    S = ((sc.get("collector") or {}).get("types")) or {}
    out, nt, nbad, tot = [], 0, 0, [0, 0, 0]
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        lc = ((t or {}).get("clock") or {}).get("landing_contract") if isinstance(t, dict) else None
        if not lc or tn not in S:
            continue
        nt += 1
        nd, nm, nf, nr, worst, sample = judge_type(lc, S[tn])
        if nd or nm or nf:
            nbad += 1
            tot = [tot[0] + nd, tot[1] + nm, tot[2] + nf]
            out.append((nd + nm + nf, _w(f"{tn}: {nd} node(s) differ from the sidecar, {nm} not in the type's tree, {nf} over {REACH_UM:g} um from their row"
                                         f"{f' (worst {worst:.0f} um)' if worst else ''} of {nr} rows; first: {sample}; strict reads the sidecar, landing_place / kit gen read the plan: "
                                         f"sync the plan row to the sidecar node (QC-OPEN-SU colsync.py)")))
    out.sort(key=lambda x: -x[0])
    lines = [m for _, m in out[:MAX_LINES]]
    lines.append(_w("summary", f"{nbad} of {nt} types with a collector sidecar row disagree ({tot[0]} DIFF, {tot[1]} MISSING, {tot[2]} FAR); sidecar {path or '<given>'}"))
    return lines


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else None, sidecar=sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
