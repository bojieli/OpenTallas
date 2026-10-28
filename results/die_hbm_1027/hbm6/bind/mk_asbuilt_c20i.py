#!/usr/bin/env python3
"""DIE-HBM-6 (2026-10-28): as-built binding for the HBM C20i plan (hbm_arch B2 lineage).

As-built die = hbm_b2_die (tools/hbm_b2/b2_top.py, Codex HBM-BIND): the r18h5 NW + NE quadrants + die level, transport
collapsed, 341 leaves.  Partition of every leaf = the plan's own census_map.json (365 parts + 12 slice rules -> groups),
the same table G0 checks lane coverage against; nothing is invented here.  Local names = the plan type's canonical
content names (contents[].inst), so the replicas of a mirrored type (NW_x / NE_x) bind to one module.

    python3 mk_asbuilt_c20i.py --plan PLAN_DIR --die die_b2.v[.gz] --base-ab physical/die_plan/hbm/bind/asbuilt.json \
        --netlist-rel <repo-relative die_b2 path> --out OUTDIR

Writes OUTDIR/asbuilt_c20i.json, OUTDIR/asbuilt_map_c20i.json, OUTDIR/asbuilt_c20i_report.json.
Slices (census_map rules -> groups: IDX score quarter 4-way, SFU core 4-way, SU pgslice 2-way) are dissolved through
their alias twins; their per-child rules need the elaborated hierarchy (bind.py elab) and are listed as OPEN until then.
"""
import argparse, collections, gzip, json, re, sys
from pathlib import Path

INST_RE = re.compile(r"^\s+(\w+)\s*(?:#\((?:.|\n)*?\))?\s+(\w+)\s*\(\n", re.M)
QT = re.compile(r"_(NW|NE)(?=\d|_|$)")


def canon_mod(m):
    m = re.sub(r"__pv\d+$", "", m)
    return re.sub(r"(_rc|_s|_h|_sp2|_p|2|_nw2?_t|_nw_t|_w2)$", "", m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True); ap.add_argument("--die", required=True)
    ap.add_argument("--base-ab", required=True); ap.add_argument("--netlist-rel", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    P = json.load(open(Path(a.plan) / "die_plan.json")); CM = json.load(open(Path(a.plan) / "census_map.json"))
    txt = (gzip.open if a.die.endswith(".gz") else open)(a.die, "rt").read()
    leaves = {i: m for m, i in INST_RE.findall(txt)}
    ptype = {pp["name"]: pp["type"] for pp in P["partitions"]}
    rules = [(re.compile(x), g) for x, g in CM["rules"]]
    groups = CM["groups"]
    rep = collections.defaultdict(list)
    by_part = collections.defaultdict(list); sliced = {}
    for i, m in sorted(leaves.items()):
        if i in CM["parts"]:
            by_part[CM["parts"][i]].append(i); continue
        g = next((g for rx, g in rules if rx.search(i)), None)
        if g:
            sliced[i] = groups[g]; continue
        rep["unmapped"].append([i, m])
    parts = {}
    for pn, insts in sorted(by_part.items()):
        t = P["partition_types"][ptype[pn]]
        if t.get("hard") and len(t.get("contents", [])) == 1:      # SM / PHY hard partitions: one slot instance
            for i in insts:
                parts[i] = [pn, t["contents"][0]["inst"]] if len(insts) == 1 else pn
            if len(insts) > 1:
                rep["hard_multi"].append([pn, insts])
            continue
        cont = {c["inst"]: c for c in t.get("contents", [])}
        free = set(cont); todo = []
        for i in insts:
            c1 = "u_" + QT.sub("_Q", i)
            if c1 in free:
                parts[i] = [pn, c1]; free.discard(c1); continue
            todo.append(i)
        left = []
        for i in todo:                                               # NE replicas of per-SM services: index - 4 / - 16
            c1 = "u_" + QT.sub("_Q", i); m = re.match(r"(.*?)(\d+)$", c1)
            hit = None
            if m and pn.startswith("NE_"):
                k = int(m.group(2)); w = len(m.group(2))
                for d in ((16,) if "_ctl_" in c1 else (4,)):
                    c2 = f"{m.group(1)}{k - d:0{w}d}"
                    if k - d >= 0 and c2 in free:
                        hit = c2; break
            if hit:
                parts[i] = [pn, hit]; free.discard(hit); rep["index_shift"].append([i, pn, hit])
            else:
                left.append(i)
        for i in left:                                               # same module family, unique candidate
            cand = [c for c in free if canon_mod(cont[c]["module"]) == canon_mod(leaves[i])]
            if len(cand) == 1:
                parts[i] = [pn, cand[0]]; free.discard(cand[0]); rep["module_match"].append([i, leaves[i], pn, cand[0], cont[cand[0]]["module"]])
            else:
                parts[i] = pn; rep["no_local_name"].append([i, leaves[i], pn, sorted(cand)])
        for c in sorted(free):
            if cont[c].get("status") != "new":
                rep["plan_content_without_asbuilt"].append([pn, c, cont[c]["module"], cont[c].get("cells")])
            else:
                rep["plan_new_content"].append([pn, c, cont[c]["module"]])
    for i, grp in sorted(sliced.items()):
        rep["slice_open"].append([i, leaves[i], grp])
    base = json.load(open(a.base_ab))
    # current-RTL closure (as Codex run_native_bind.sh overlays every rtl file changed since its base): a bundle file
    # whose repository copy differs is replaced by the repository copy (the hard cores are built from it); bundle-only
    # files stay.  Listed in the report.
    B = "physical/die_plan/hbm/bind/r18h5_bundle/"; repo = Path(a.base_ab).resolve().parents[4]
    prefer = []
    for p in base["prefer"]:
        r = p[len(B):] if p.startswith(B) else None
        if r and (repo / r).exists() and (repo / r).read_bytes() != (repo / p).read_bytes():
            prefer.append(r); rep["prefer_repo"].append(r)
        else:
            prefer.append(p)
    ab = dict(
        note=("DIE-HBM-6 10-28: C20i as-built = hbm_b2_die (tools/hbm_b2/b2_top.py; 341 leaves, transport already collapsed); "
              "partition per leaf = plan census_map.json; local names = plan type contents; generated by "
              "results/die_hbm_1027/hbm6/bind/mk_asbuilt_c20i.py"),
        base=base["base"], netlist=[a.netlist_rel], top="hbm_b2_die",
        rtl_roots=base["rtl_roots"], files=base["files"], prefer=prefer, defines=base["defines"],
        defines_note=base.get("defines_note", ""),
        dissolve=base["dissolve"] + sorted({base["alias"].get(leaves[i], leaves[i]) for i in sliced}),
        alias=base["alias"], transport=[], sources=base["sources"], default_clock=base.get("default_clock", "stream"),
        map_file="asbuilt_map_c20i.json", lint_split=True, lint_jobs=2,
        portbind_prefer=base.get("portbind_prefer", []), straps=base["straps"], strap_note=base.get("strap_note", ""))
    mp = dict(note="DIE-HBM-6: from plan census_map.json (parts) + type contents (local names); slice rules OPEN",
              parts=parts, rules=[])
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "asbuilt_c20i.json").write_text(json.dumps(ab, indent=1) + "\n")
    (out / "asbuilt_map_c20i.json").write_text(json.dumps(mp, indent=1) + "\n")
    summ = {k: len(v) for k, v in rep.items()}
    summ.update(leaves=len(leaves), mapped_whole=len(parts), with_local=sum(isinstance(v, list) for v in parts.values()),
                sliced=len(sliced))
    (out / "asbuilt_c20i_report.json").write_text(json.dumps(dict(summary=summ, **rep), indent=1) + "\n")
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
