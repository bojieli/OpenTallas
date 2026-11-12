#!/usr/bin/env python3
"""QC-S28-A delta for the QC s28 event (DIE-QC-99, 11-12): re-appliable, touches ONLY the keys listed in the delta.

  make   BASE_PLAN DELTA_OUT [--views VIEWS.json]  build the delta from the base plan (records every `from` value)
  apply  PLAN_IN PLAN_OUT DELTA                     apply; each edit's `from` must equal PLAN_IN (fail closed), so it
                                                    composes onto any plan (e.g. QC-S28-B's) that left these keys alone
  shape  SIGNED_LEF VIEW_LEF MODULE [--pin ck]      view vs signed: MACRO, SIZE, FOREIGN/ORIGIN, every PIN block
                                                    (name, direction/use, layer+rects) and M1-M5 OBS identical; M6/M7
                                                    OBS may differ (the detail); the clock pin rect printed
  stage  TREE VIEWS.json --from DIR                 install the path+sha views into a kit / gate tree: copy
                                                    DIR/<module>/<module>.lef to its plan path, verify sha256 (fail
                                                    closed: wrong or missing bytes = exit 2), never in place

Items (s28 composer QC-S28-A):
  A4  hard_cores[inst].lef of every qfd_tile_nk_a0c / qfd_tile_nl_a0c instance (16 types, 62 nk + 2 nl) -> the
      OBS-SYNC-1 window-form exact-metal view (abstract_detail splice --pin-window-um 1.0 --top-layer M7, bloat 0, of
      the SAME signed ODB; DRT single-macro probe rc 0 / 0 DRT-0073 incl. the staged access form).  Bound by
      path+sha (VIEWS_A0C_1112.json), not in git.  lib unchanged (signed).
  A5  coll_n clock.tap_group = the cland rec_tx_s0_i landing ring + its u_bin capture flops as ONE tap group
      (VISLAYOUT2-QC ring-bin-tap, COORD 02:33).  Clock tap assignment only.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

A0C = ("qfd_tile_nk_a0c", "qfd_tile_nl_a0c")
VIEW_DIR = "physical/die_plan/qwen_compute/qcviews_1112/views"
COLLN_TAP_GROUP = {
    "re": "(?:^|[/.])u_(?:cland|bin)_(rec_tx_s0_i)[/.]",
    "note": "QC-S28-A 11-12 (VISLAYOUT2-QC ring-bin-tap, COORD 02:33): the cland rec_tx_s0_i landing ring and its "
            "u_bin_rec_tx_s0_i capture flops are ONE tap group (key rec_tx_s0_i) on the tap nearest their centroid "
            "(clock_taps.tcl group form, OT_TAP_GROUP_RE); s25 form-d sign-off had the ring on clk (165 ps) and the "
            "bin on clk_t2 (404-456 ps): 466 reg->reg FF hold endpoints to -45.76 ps. Clock tap assignment only, "
            "+0 cycles."}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _sel(lst, key):
    hits = [x for x in lst if all(x.get(k) == v for k, v in key.items())]
    if len(hits) != 1:
        raise KeyError(f"selector {key}: {len(hits)} matches")
    return hits[0]


def _get(t, path):
    cur = t
    for k in path[:-1]:
        cur = _sel(cur, k) if isinstance(k, dict) else cur[k]
    last = path[-1]
    return cur, last


def make(base, views=None):
    edits = []
    pt = base["partition_types"]
    vmap = {}
    if views:
        vmap = {m: v["path"] for m, v in views["modules"].items()}
    for tn in sorted(pt):
        for h in pt[tn].get("hard_cores", []) or []:
            if h.get("module") in A0C:
                to = vmap.get(h["module"], f"{VIEW_DIR}/{h['module']}/{h['module']}.lef")
                edits.append(dict(item="A4", type=tn, path=["hard_cores", {"inst": h["inst"]}, "lef"],
                                  **{"from": h.get("lef"), "to": to}))
    edits.append(dict(item="A5", type="coll_n", path=["clock", "tap_group"],
                      **{"from": pt["coll_n"].get("clock", {}).get("tap_group"), "to": COLLN_TAP_GROUP}))
    return dict(schema="opentallas.qc_s28a_delta.v1", lane="QC-S28-A", die="qwen_compute",
                touched={tn: sorted({"/".join(k if isinstance(k, str) else "[" + ",".join(f"{a}={b}" for a, b in k.items()) + "]"
                                             for k in e["path"]) for e in edits if e["type"] == tn})
                         for tn in sorted({e["type"] for e in edits})},
                edits=edits)


def apply(plan, delta):
    out = copy.deepcopy(plan)
    pt = out["partition_types"]
    for e in delta["edits"]:
        cur, last = _get(pt[e["type"]], e["path"])
        have = cur.get(last) if isinstance(cur, dict) else None
        if have != e["from"] and have != e["to"]:
            raise ValueError(f"{e['type']} {e['path']}: base has {json.dumps(have)[:200]}, delta expects "
                             f"{json.dumps(e['from'])[:200]} (another delta touched this key: compose by hand)")
        if e["to"] is None:
            cur.pop(last, None)
        else:
            cur[last] = copy.deepcopy(e["to"])
    return out


# ---------------------------------------------------------------- LEF shape check
def lef_parse(text, module):
    m = re.search(rf"^MACRO\s+{re.escape(module)}\s*$(.*?)^END\s+{re.escape(module)}\s*$", text, re.M | re.S)
    if not m:
        raise ValueError(f"no MACRO {module}")
    body = m.group(1)
    hdr = {k: re.search(rf"^\s*{k}\s+([^;]*);", body, re.M) for k in ("CLASS", "FOREIGN", "ORIGIN", "SIZE", "SYMMETRY")}
    hdr = {k: (v.group(1).split() if v else None) for k, v in hdr.items()}
    pins = {}
    for pm in re.finditer(r"^\s*PIN\s+(\S+)\s*$(.*?)^\s*END\s+\1\s*$", body, re.M | re.S):
        name, pb = pm.group(1), pm.group(2)
        attrs = tuple(sorted(" ".join(x.split()) for x in re.findall(r"^\s*(DIRECTION\s+\S+|USE\s+\S+)\s*;", pb, re.M)))
        shapes, lay = [], None
        for ln in pb.splitlines():
            s = ln.split()
            if not s:
                continue
            if s[0] == "LAYER":
                lay = s[1]
            elif s[0] == "RECT":
                shapes.append((lay, tuple(round(float(x), 4) for x in s[1:5])))
        pins[name] = (attrs, tuple(sorted(shapes)))
    obs = {}
    om = re.search(r"^\s*OBS\s*$(.*?)^\s*END\s*$", body, re.M | re.S)
    if om:
        lay = None
        for ln in om.group(1).splitlines():
            s = ln.split()
            if not s:
                continue
            if s[0] == "LAYER":
                lay = s[1]
            elif s[0] == "RECT":
                obs.setdefault(lay, []).append(tuple(round(float(x), 4) for x in s[1:5]))
    return hdr, pins, {k: sorted(v) for k, v in obs.items()}


def shape(signed, view, module, pin="ck", free=("M6", "M7")):
    hs, ps, os_ = lef_parse(Path(signed).read_text(), module)
    hv, pv, ov = lef_parse(Path(view).read_text(), module)
    prob = []
    for k in hs:
        if hs[k] != hv[k]:
            prob.append(f"{k} {hs[k]} != {hv[k]}")
    if set(ps) != set(pv):
        prob.append(f"PIN names differ: -{sorted(set(ps) - set(pv))[:5]} +{sorted(set(pv) - set(ps))[:5]}")
    nd = [n for n in ps if n in pv and ps[n] != pv[n]]
    if nd:
        prob.append(f"{len(nd)} PIN blocks differ, e.g. {nd[:5]}")
    for lay in sorted(set(os_) | set(ov)):
        if lay in free:
            continue
        if os_.get(lay) != ov.get(lay):
            prob.append(f"OBS {lay} differs ({len(os_.get(lay, []))} vs {len(ov.get(lay, []))} rects)")
    obs_area = {}
    w, h = (float(hv["SIZE"][0]), float(hv["SIZE"][2])) if hv["SIZE"] else (0, 0)
    for lay in free:
        for tag, o in (("signed", os_), ("view", ov)):
            a = sum((r[2] - r[0]) * (r[3] - r[1]) for r in o.get(lay, []))
            obs_area[f"{tag}_{lay}"] = round(a / (w * h), 4) if w * h else None
    return dict(module=module, ok=not prob, problems=prob, size=hv["SIZE"], pins=len(pv),
                pin=pin, pin_signed=ps.get(pin), pin_view=pv.get(pin), pin_equal=ps.get(pin) == pv.get(pin),
                obs_layers_signed=sorted(os_), obs_layers_view=sorted(ov), obs_frac=obs_area,
                signed_sha256=sha256(signed), view_sha256=sha256(view))


# ---------------------------------------------------------------- staging by path + sha
def stage(tree, views, src):
    rows = []
    for m, v in sorted(views["modules"].items()):
        dst = Path(tree) / v["path"]
        if dst.is_file() and sha256(dst) == v["sha256"]:
            rows.append(dict(module=m, path=v["path"], status="present"))
            continue
        s = Path(src) / m / Path(v["path"]).name
        if not s.is_file() or sha256(s) != v["sha256"]:
            raise SystemExit(f"STAGE FAIL {m}: {s} missing or sha256 != {v['sha256'][:12]}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=f".{dst.name}.", dir=str(dst.parent))
        os.close(fd)
        shutil.copyfile(s, tmp)
        os.chmod(tmp, 0o444)
        os.replace(tmp, dst)
        if sha256(dst) != v["sha256"]:
            raise SystemExit(f"STAGE FAIL {m}: copy sha256 mismatch")
        rows.append(dict(module=m, path=v["path"], status="staged"))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("make"); a.add_argument("base"); a.add_argument("out"); a.add_argument("--views")
    a = sub.add_parser("apply"); a.add_argument("plan"); a.add_argument("out"); a.add_argument("delta")
    a = sub.add_parser("shape"); a.add_argument("signed"); a.add_argument("view"); a.add_argument("module")
    a.add_argument("--pin", default="ck"); a.add_argument("--json")
    a = sub.add_parser("stage"); a.add_argument("tree"); a.add_argument("views"); a.add_argument("--from", dest="src", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "make":
        views = json.loads(Path(a.views).read_text()) if a.views else None
        d = make(json.loads(Path(a.base).read_text()), views)
        d["base_plan_sha256"] = sha256(a.base)
        Path(a.out).write_text(json.dumps(d, indent=1) + "\n")
        print(f"DELTA {a.out}: {len(d['edits'])} edits on {len(d['touched'])} types")
    elif a.cmd == "apply":
        out = apply(json.loads(Path(a.plan).read_text()), json.loads(Path(a.delta).read_text()))
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
        print(f"APPLIED {a.delta} -> {a.out} sha256 {sha256(a.out)[:12]}")
    elif a.cmd == "shape":
        r = shape(a.signed, a.view, a.module, a.pin)
        print(json.dumps(r, indent=1))
        if a.json:
            Path(a.json).write_text(json.dumps(r, indent=1) + "\n")
        return 0 if r["ok"] and r["pin_equal"] else 1
    elif a.cmd == "stage":
        for r in stage(a.tree, json.loads(Path(a.views).read_text()), a.src):
            print(f"STAGE {r['status']} {r['module']} {r['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
