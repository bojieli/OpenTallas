#!/usr/bin/env python3
"""HBM-MU-QUAD-3 task 3: top-down pin tables for the new MU hard cores (one fixed table per module, TYPE-REDUCE).

Port lists: yosys `dump i:* o:*` of the RTL top (rtl/*.dump.txt, sources pinned in SOURCES below).
Faces: from the plan (top-down, owner 10-13): the side each port's internal_stations endpoint sits on in the core frame
(orient undone), majority over all instances of the module in q_hub_nw + q_hub_ne; ports without a plan partner go to
the N face (VM bank: the existing hfd_vms_bank_native_q0_faces face map for its service ports).  Clock entry: clk /
rst_n at the N-face centre (hc128_templates.north precedent), data in two bands around it.
Pins: W/E faces M4 (y tracks 0.024 + k*0.048), N/S faces M5 (x tracks 0.024 + k*0.048), 0.019 inside the edge, spread
evenly in [8.64, L-8.64] (hc128_templates.face).  Deterministic; no plan geometry is changed.
Usage: gen_mu_pins.py PLAN_DIR RTL_DUMP_DIR OUT_DIR"""
import json, re, sys, collections, hashlib
from pathlib import Path

SOURCES = {  # module label in the plan -> (RTL top, source, branch@sha)
    "hnx_vms_bank_q0_faces": ("hnx_vms_bank_q0_faces", "rtl/hbm_next/vm/hnx_vms_bank_q0_faces.sv",
                              "claude/hbm-next-units-fushub-1019@451b9e86b"),
    "hnx_fused_lane": ("ot_hnx_fused_lane", "rtl/hbm_next/fused/ot_hnx_fused_eng.sv",
                       "claude/hbm-next-units-fushub-1019@451b9e86b"),
    "ot_hnx_fused_tnode": ("ot_hnx_fused_tnode", "rtl/hbm_next/fused/ot_hnx_fused_tree.sv",
                           "claude/hbm-next-units-fushub-1019@451b9e86b"),
    "hnx_idxn_keybuf": ("ot_hnx_idxn_keybuf", "rtl/hbm_next/idxn/ot_hnx_idxn_keybuf.sv",
                        "claude/hbm-next-units-idxn-1019@1228d93d6"),
}
# plan station port label -> RTL port groups (the plan's MU probe names its links rd/wr/rq/up/down)
GROUPS = {
    "hnx_fused_lane": {"rd": ["rr_v", "rr_d"], "rq": ["rq_v", "rq_s"], "wr": ["wq_v", "wq_s", "wq_d"],
                       "dn": ["dn_v", "dn_op", "dn_x", "dn_d"], "uo": ["up_v", "up_t", "up_x", "up_d"]},
    "hnx_vms_bank_q0_faces": {"rd": ["rr0"], "rq": ["rq0"], "wr": ["wq0", "wq_done0"]},
    "ot_hnx_fused_tnode": {"ua": ["ua"], "ub": ["ub"], "uo": ["uo"], "dn": ["dn"], "da": ["da"], "db": ["db"]},
    "hnx_idxn_keybuf": {},
}
OLD_BANK = "hfd_vms_bank_native_q0_faces__270x313.2__q_hub_u_vmb_Q0.json"   # SU face map for the service ports
CLOCKS = ("clk", "rst_n")
PITCH, OFF, INSET, END = 0.048, 0.024, 0.019, 8.64
FLIP_X = {"W": "E", "E": "W"}
FLIP_Y = {"N": "S", "S": "N"}


def ports(dump):
    out = []
    for ln in Path(dump).read_text().splitlines():
        m = re.match(r"\s*wire (?:width (\d+) )?(input|output) \d+ \\(\S+)", ln)
        if m:
            out.append((m.group(3), int(m.group(1) or 1), m.group(2)))
    return out


def bits(name, n):
    return [name] if n == 1 else [f"{name}[{i}]" for i in range(n)]


def face_of(h, pt):
    x0, y0 = h["origin_um"]; w, hh = h["outline_um"]
    lx, ly = pt[0] - x0, pt[1] - y0
    d = {"W": lx, "E": w - lx, "S": ly, "N": hh - ly}
    f = min(d, key=d.get)
    o = h.get("orient", "R0")
    if o in ("MY", "R180"):
        f = FLIP_X.get(f, f)
    if o in ("MX", "R180"):
        f = FLIP_Y.get(f, f)
    return f


def plan_faces(P, module):
    votes = collections.defaultdict(collections.Counter)
    for tn in ("q_hub_nw", "q_hub_ne"):
        t = P["partition_types"][tn]
        hc = {h["inst"]: h for h in t["hard_cores"] if h["module"] == module
              and (module != "hnx_vms_bank_q0_faces" or h["inst"].endswith("_mu1"))}   # MU clones: lane links only
        for s in t.get("internal_stations", []):
            for k, ek, ok in (("launch", "from_um", "capture"), ("capture", "to_um", "launch")):
                v = s.get(k, "")
                b = v.split(".")[0]
                if b not in hc:
                    continue
                lab = v.split(".")[1] if "." in v else s.get(ok, "").split(".")[-1]
                lab = re.sub(r"\d+$", "", lab) if module != "ot_hnx_fused_tnode" else lab
                votes[lab][face_of(hc[b], s[ek])] += 1
    return {lab: c.most_common(1)[0][0] for lab, c in votes.items()}, {k: dict(v) for k, v in votes.items()}


def place(names, side, w, h, lo=END, hi=None, used=None):
    length = h if side in "WE" else w
    hi = length - END if hi is None else hi
    layer = "M4" if side in "WE" else "M5"
    used = set() if used is None else used
    n = len(names)
    cap = int((hi - lo) / PITCH)
    if n > cap:
        raise ValueError(f"{side}: {n} pins > {cap} tracks")
    pins = []
    for i, name in enumerate(names):
        k = round((lo + (i + .5) * (hi - lo) / n - OFF) / PITCH)
        while k in used:
            k += 1
        used.add(k)
        pos = round(OFF + k * PITCH, 6)
        x, y = {"W": (INSET, pos), "E": (w - INSET, pos), "S": (pos, INSET), "N": (pos, h - INSET)}[side]
        pins.append(dict(name=name, layer=layer, x=round(x, 6), y=round(y, 6)))
    return pins


def build(module, plist, fmap, w, h):
    by = collections.defaultdict(list)
    for name, width, _d in plist:
        if name in CLOCKS:
            continue
        by[fmap.get(name, "N")].extend(bits(name, width))
    pins = []
    for f in ("W", "E", "S"):
        if by[f]:
            pins += place(by[f], f, w, h)
    n = by["N"]
    half = (len(n) + 1) // 2
    used = set()
    if n:
        pins += place(n[:half], "N", w, h, hi=w / 2 - 6.0, used=used)
        if n[half:]:
            pins += place(n[half:], "N", w, h, lo=w / 2 + 6.0, used=used)
    pins += place([c for c in CLOCKS if c in {p[0] for p in plist}], "N", w, h, lo=w / 2 - .096, hi=w / 2 + .096,
                  used=used)
    names = [p["name"] for p in pins]
    want = [b for nm, wd, _ in plist for b in bits(nm, wd)]
    assert sorted(names) == sorted(want), module
    return pins, {f: len(v) for f, v in by.items()}


def main():
    plan_dir, dumps, out = map(Path, sys.argv[1:4])
    P = json.loads((plan_dir / "die_plan.json").read_text())
    (out / "cores").mkdir(parents=True, exist_ok=True)
    man = dict(schema="opentallas.hbm.mu_pins.v1", lane="HBM-MU-QUAD-3", modules={}, blockers={})
    old = json.loads((plan_dir / "cores" / OLD_BANK).read_text())
    for module, (top, src, ref) in SOURCES.items():
        outl = {tuple(hc["outline_um"]) for tn in ("q_hub_nw", "q_hub_ne")
                for hc in P["partition_types"][tn]["hard_cores"] if hc["module"] == module}
        assert len(outl) == 1, (module, outl)
        w, h = outl.pop()
        plist = ports(dumps / f"{top}.dump.txt")
        labf, votes = plan_faces(P, module)
        fmap = {}
        if module == "hnx_vms_bank_q0_faces":     # service ports keep the SU bank face map (port-name based)
            ow, oh = 270.0, 313.2
            for q in old:
                nm = re.sub(r"\[\d+\]$", "", q["name"])
                d = {"W": q["x"], "E": ow - q["x"], "S": q["y"], "N": oh - q["y"]}
                fmap.setdefault(nm, min(d, key=d.get))
            fmap.setdefault("clk_macro3", fmap.get("clk_macro0", "W"))
        for lab, f in labf.items():
            for p in GROUPS[module].get(lab, []):
                fmap[p] = f
        try:
            pins, counts = build(module, plist, fmap, w, h)
        except ValueError as e:
            total = sum(wd for _n, wd, _d in plist)
            trk = 4 * int((w - 2 * END) / PITCH)
            man["blockers"][module] = (f"{top}: {total} port bits on a {w}x{h} outline = {total / trk:.2f} of all "
                                       f"{trk} M4/M5 face tracks (> pin_track_max 0.6; {total / (2 * (w + h)):.1f} "
                                       f"pins/um > face_pins_per_um 6); first fail: {e}; needs RTL serialisation of "
                                       f"key_in/key_out or a larger outline (plan links: {votes or 'none'})")
            continue
        fn = f"{module}__{w:g}x{h:g}__mu_template.json"
        s = json.dumps(pins) + "\n"
        (out / "cores" / fn).write_text(s)
        man["modules"][module] = dict(rtl_top=top, rtl_source=src, rtl_ref=ref, outline_um=[w, h], pins=len(pins),
                                      face_counts=counts, plan_face_votes=votes, pins_file="cores/" + fn,
                                      sha256=hashlib.sha256(s.encode()).hexdigest())
    (out / "mu_pins_manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({m: v["pins"] for m, v in man["modules"].items()}), json.dumps(man["blockers"])[:400])


if __name__ == "__main__":
    main()
