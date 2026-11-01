#!/usr/bin/env python3
"""DIE-QC-59C 11-01: QC crossbar (cb*) fabric/tile ID parameters -> parent-tied ID straps (one class fix).

KIT-WAVE-12 FAIL FLOW @kit_rtl on the cb* types: 'instances of the bound module carry different parameters'
(bind.py kit-rtl).  The per-instance bound parameters of these types are ID-only constants: the crossbar node index
sidx[2:0] of every fabric node u_fab.u_x_<r>_<c> (qfd_c_xstn) and the tile identity tile_id[15:0] of every tile u_t_<r>_<c>
(literal bits [15:4]; bits [3:0] stay the tiles' own internal tie cells).  COORD ruling 10-26 00:59 (2) option B / OWNER
10-25 ID straps: they become parent ID straps (tools/die_plan/parent_id_straps.py; 'sidx' and 'tile_id' are ID_PORTS).

Plan change, only the cb* partition types with more than one instance whose bound parameter sets differ, and there
only the ID parameters whose value differs across the instances (12 types: tile_id x4 on all, sidx x4 too on cbx_q10;
an ID parameter equal on every instance, and the cbf/cbn_q00 S_u_fab_not_*_A = 1'b1, stay parameters):
  * contents u_xstn<r><c>: parent_id_leaf 'u_fab.u_x_<r>_<c>', parent_id_straps {sidx: {width 3, value}};
  * contents u_t<r><c>:    parent_id_leaf 'u_t_<r>_<c>',     parent_id_straps {tile_id: {width 16, value}};
    value = the bind representative (the bound module's parameter default = first instance), as bind.emit_type checks;
    every instance's own value is tied at the die top (bind_parent_id_straps.json, straps.audit_top_ties);
  * count_straps (the type's strap pin table, same form as the strap_r8pad_* entries): one entry per strap port
    strap_u_fab_u_x_<r>_<c>_sidx[3] / strap_u_t_<r>_<c>_tile_id[16], layer M5, one interior site per bit on the
    existing 4.32 um strap lattice around clock.tap_um (next free points by distance, outside every hard core), so
    gen_phys lists them in port_bind_pins.json (PORT_BIND) and the kit SDC false-paths them.
Nothing else changes (outlines, buses, pins, clock, stations, other types).  Single-instance cb types keep their params.
usage: delta_cbid_1101.py PLAN_IN PLAN_OUT BASE_BIND_DIR [REPORT.json]"""
import copy
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

PITCH = 4.32
LAYER = "M5"
NOTE = "OWNER 10-25 option B parent ID strap (COORD 10-26 (2)): %s, tied per instance at the parent (DIE-QC-59C)"
PARAM = re.compile(r"parameter \[(\d+):0\] S_(u_fab_u_x_(\d+)_(\d+)_sidx|u_t_(\d+)_(\d+)_tile_id) = \d+'b([01]+)")


def bound_sets(bind_dir):
    """{bound module: [param text per instance]} from the bound top"""
    top = next((bind_dir / "rtl").glob("*_bound_top.sv")).read_text()
    out = defaultdict(list)
    for m in re.finditer(r"^\s*(\w+)\s*#\((.*?)\)\s*(\w+)\s*\(", top, re.M):
        out[m.group(1)].append(m.group(2))
    return out


def defaults(bind_dir, mod):
    """{(kind, r, c): (width, value)} of the bound module's sidx / tile_id parameter defaults (= representative)"""
    txt = (bind_dir / "rtl" / f"{mod}.sv").read_text()
    res = {}
    for m in PARAM.finditer(txt):
        w = int(m.group(1)) + 1
        if m.group(3) is not None:
            res[("sidx", m.group(3), m.group(4))] = (w, int(m.group(7), 2))
        else:
            res[("tile_id", m.group(5), m.group(6))] = (w, int(m.group(7), 2))
    return res


def sites(t, n):
    """n free strap-lattice points nearest clock.tap_um, inside the outline and outside every hard core"""
    tx, ty = t["clock"]["tap_um"]
    used = {(round(x, 3), round(y, 3)) for s in t.get("count_straps", []) for x, y in s.get("sites_um", [])}
    W, H = t["outline_um"]
    cores = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
              h["origin_um"][1] + h["outline_um"][1]) for h in t.get("hard_cores", [])]
    cand = []
    R = 1 + int(math.sqrt(n + len(used))) + 2
    for i in range(-R, R + 1):
        for j in range(-R, R + 1):
            x, y = round(tx + i * PITCH, 3), round(ty + j * PITCH, 3)
            if (x, y) in used or not (0 < x < W and 0 < y < H):
                continue
            if any(a - PITCH < x < c + PITCH and b - PITCH < y < d + PITCH for a, b, c, d in cores):
                continue
            cand.append((i * i + j * j, math.atan2(j, i), x, y))
    cand.sort()
    assert len(cand) >= n, (n, len(cand))
    return [[x, y] for _, _, x, y in cand[:n]]


def main():
    pin, pout, bdir = sys.argv[1:4]
    rep_p = sys.argv[4] if len(sys.argv) > 4 else None
    text = open(pin).read()
    raw = json.loads(text)
    assert json.dumps(raw) + "\n" == text, "plan text style is not one-line json.dumps"
    orig = copy.deepcopy(raw)
    bdir = Path(bdir)
    brep = json.loads((bdir / "bind_report.json").read_text())
    sets = bound_sets(bdir)
    rep = []
    for tn, t in sorted(raw["partition_types"].items()):
        if not re.match(r"cb[fnx]_q\d\d", tn):
            continue
        mod = brep["types"][tn]["module"]
        inst = sets.get(mod, [])
        if len(set(inst)) <= 1:
            rep.append(dict(type=tn, module=mod, instances=len(inst), action="unchanged (one parameter set)"))
            continue
        ids = defaults(bdir, mod)
        assert ids and len(ids) == 8, (tn, sorted(ids))
        # only the ID parameters whose value differs across the instances become straps; an ID that is the same on
        # every instance stays a parameter (identical value set on every instance, kit-rtl takes it as is)
        vals = defaultdict(set)
        for ptxt in inst:
            for k, v in re.findall(r"\.(S_\w+)\(([^()]*)\)", ptxt):
                vals[k].add(v)
        pn = {key: (f"S_u_fab_u_x_{key[1]}_{key[2]}_sidx" if key[0] == "sidx" else f"S_u_t_{key[1]}_{key[2]}_tile_id")
              for key in ids}
        nonid = sorted(k for k, v in vals.items() if len(v) > 1 and k not in pn.values())
        assert not nonid, (tn, "non-ID parameter differs across instances", nonid)
        ids = {key: wv for key, wv in ids.items() if len(vals[pn[key]]) > 1}
        assert ids, tn
        cont = {c["inst"]: c for c in t["contents"]}
        names = {s["name"] for s in t.get("count_straps", [])}
        new = []
        for (kind, r, c), (w, v) in sorted(ids.items()):
            if kind == "sidx":
                d, leaf, port = cont[f"u_xstn{r}{c}"], f"u_fab.u_x_{r}_{c}", f"strap_u_fab_u_x_{r}_{c}_sidx"
            else:
                d, leaf, port = cont[f"u_t{r}{c}"], f"u_t_{r}_{c}", f"strap_u_t_{r}_{c}_tile_id"
            assert "parent_id_straps" not in d and port not in names, (tn, d["inst"], port)
            d["parent_id_leaf"] = leaf
            d["parent_id_straps"] = {kind: dict(width=w, value=v)}
            new.append((port, w, kind))
        xy = sites(t, sum(w for _, w, _ in new))
        k = 0
        for port, w, kind in new:
            t.setdefault("count_straps", []).append(dict(name=port, width=w, note=NOTE % kind, layer=LAYER,
                                                         sites_um=xy[k:k + w]))
            k += w
        rep.append(dict(type=tn, module=mod, instances=len(inst), distinct_sets=len(set(inst)),
                        straps={p: w for p, w, _ in new}, strap_bits=k,
                        representative={f"{kd}_{r}{c}": v for (kd, r, c), (w, v) in sorted(ids.items())}))
    # only the touched types differ
    for tn in raw["partition_types"]:
        if raw["partition_types"][tn] != orig["partition_types"][tn]:
            assert any(x["type"] == tn and "straps" in x for x in rep), tn
    assert {k: v for k, v in raw.items() if k != "partition_types"} == \
        {k: v for k, v in orig.items() if k != "partition_types"}
    Path(pout).write_text(json.dumps(raw) + "\n")
    if rep_p:
        Path(rep_p).write_text(json.dumps(dict(schema="opentallas.qc_cbid_delta.v1", plan_in=pin, base_bind=str(bdir),
                                               types=rep), indent=1) + "\n")
    for x in rep:
        print(x["type"], x["instances"], x.get("distinct_sets", 1), x.get("strap_bits", x.get("action")))


if __name__ == "__main__":
    main()
