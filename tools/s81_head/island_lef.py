#!/usr/bin/env python3
# SUPERSEDED 2026-10-26 06:39 (OWNER, METHODOLOGY 12.2a1): in-core islands = PUSHDOWN (driver cells in the core netlist); cut-out macros are not used. Record only, NOT for merge.
"""S81-HEAD v2 core abstract with the centred INFRA ISLAND hole cut out (HEAD-CORE-LAT-R2/LEF, METHODOLOGY 12.2a/12.7c).

PLAN ABSTRACT (the v2 cores are not built yet): outline, pins and PG come from the v2 kit inputs, not from the old
signed 317.672/277.652 LEF, which describes a different floorplan (old ROM sites, M6/M7 routing):
  - SIZE  = island_spec outline (319.68 / 285.12, lattice multiples).
  - PINS  = the v2 kit io.tcl place_pin lines (exact centre + size + layer; E/N face pins already moved out by the
            outline growth; clk/rst_n = M5 interior pins at the island centre / centre-2.16). DIRECTION/USE from the old LEF.
  - PG    = the v2 core pdn.tcl: M5 stripes (w 0.12, VDD/VSS pair spacing 0.072, pitch 4.32, offset 2.064, over the
            core area) as VDD/VSS PORTs, SPLIT at the hole (ends 0.072 outside the hole edge) exactly as pdngen built
            them in elemB_c2 (measured, island_hole_probe.py): the core has NO PG inside the hole (rows cut -> no
            M1/M2 followpins; M5 stripes stop).  The island PG is therefore TOP-OWNED: die rows + M1/M2 followpins in
            the hole + M9->M1 stacks from the die M8/M9 grid; the core PG is exposed at the hole's N/S edges as the
            M5 stripe-end ports.
  - OBS   = bloated (write_abstract_lef -bloat_occupied_layers style): M1..M5 (core MAX_ROUTING_LAYER = M5) over the
            whole outline MINUS the island hole.  Inside the hole the only core-owned shapes are the clk/rst_n pins,
            the M5 PG stripes (ports) and the two 0.384-wide M5 escape slots (clk -> N edge, rst_n -> S edge) that the
            core's own clk/rst_n wires use (island_<t>.tcl); those slots stay OBS on M5.  M6/M7 are not used by the
            v2 core (max M5): no OBS there, so the die M9->M5 via stack and M6/M7 die routes cross freely.
BUILT mode: --from-lef <write_abstract_lef -bloat_occupied_layers of the built v2 core> keeps that LEF's pins + PG
verbatim, renames the macro, clips every OBS rect (incl. implant layers) against the hole and adds the M5 slots.
usage: island_lef.py --spec island_spec.json --type ot_s81hd_elemA_cv --io io.tcl --old-lef old.lef --out DIR [--from-lef L]
"""
import argparse, json, re, os, hashlib
from pathlib import Path

ROW_H = 0.27
OBS_LAYERS = ["M1", "M2", "M3", "M4", "M5"]
SLOT_W = 0.384


def f(v):
    return "%.3f" % round(v, 3)


def rect(r):
    return "        RECT  %s %s %s %s ;" % tuple(f(v) for v in r)


def minus(r, h):
    """r minus hole h -> up to 4 rects."""
    x0, y0, x1, y1 = r
    hx0, hy0, hx1, hy1 = h
    if hx1 <= x0 or hx0 >= x1 or hy1 <= y0 or hy0 >= y1:
        return [r]
    out = [(x0, y0, x1, max(y0, hy0)), (x0, min(y1, hy1), x1, y1),
           (x0, max(y0, hy0), max(x0, hx0), min(y1, hy1)), (min(x1, hx1), max(y0, hy0), x1, min(y1, hy1))]
    return [q for q in out if q[2] - q[0] > 1e-6 and q[3] - q[1] > 1e-6]


def pg_shapes(t, W, core, hole):
    """VDD/VSS M5 stripe ports over the core area, split at the hole like the built core."""
    sh = {"VDD": [], "VSS": []}
    w, sp, pitch, off, gap = 0.12, 0.072, 4.32, 2.064, 0.072
    hx0, hy0, hx1, hy1 = hole
    k = 0
    while True:
        x = core[0] + off - w / 2 + k * pitch   # pdngen -offset = stripe centre; pair order VSS, VDD (measured elemB_c2)
        if x + w + sp + w > core[2] + 1e-6:
            break
        for net, xa in (("VSS", x), ("VDD", x + w + sp)):
            if xa < hx1 and xa + w > hx0:
                sh[net].append(("M5", (xa, core[1], xa + w, hy0 - gap)))
                sh[net].append(("M5", (xa, hy1 + gap, xa + w, core[3])))
            else:
                sh[net].append(("M5", (xa, core[1], xa + w, core[3])))
        k += 1
    return sh


def parse_pins_lef(txt):
    """PIN blocks verbatim (signal + PG), name -> text."""
    return re.findall(r"\n(  PIN (\S+)\n.*?\n  END \2)", txt, re.S)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--spec", required=True); a.add_argument("--type", required=True)
    a.add_argument("--out", required=True); a.add_argument("--name")
    a.add_argument("--io"); a.add_argument("--old-lef")
    a.add_argument("--from-lef")
    A = a.parse_args()
    S = json.loads(Path(A.spec).read_text())
    t = S["types"][A.type]
    W, H = t["outline_um"]
    hole = tuple(t["hole_um"])
    hx0, hy0, hx1, hy1 = hole
    core = (4.32, 4.32, W - 4.32, H - 4.32)
    name = A.name or A.type + "i"
    cx, cy = t["pins"]["clk"]["xy"]
    rx, ry = t["pins"]["rst_n"]["xy"]
    # core-owned M5 escape slots in the hole (clk pin top -> hole N edge, rst_n pin bottom -> hole S edge)
    slots = [(cx - SLOT_W / 2, cy + 0.096, cx + SLOT_W / 2, hy1), (rx - SLOT_W / 2, hy0, rx + SLOT_W / 2, ry - 0.096)]
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', "UNITS", "    DATABASE MICRONS 1000 ;", "END UNITS", "",
         "MACRO " + name, "  FOREIGN %s 0 0 ;" % name, "  CLASS BLOCK ;", "  SIZE %s BY %s ;" % (f(W), f(H))]
    obs = {}
    inputs = [("spec", A.spec)]
    if A.from_lef:
        inputs.append(("from_lef", A.from_lef))
        src = Path(A.from_lef).read_text()
        m = re.search(r"SIZE (\S+) BY (\S+)", src)
        assert abs(float(m.group(1)) - W) < 1e-3 and abs(float(m.group(2)) - H) < 1e-3, ("outline differs from slice", m.groups())
        blocks = parse_pins_lef(src)
        npins = sum(1 for _, n in blocks if n not in ("VDD", "VSS"))
        for txt, n in blocks:
            if n in ("clk", "rst_n"):  # must sit at the slice entry
                r = [float(v) for v in re.search(r"RECT\s+(\S+) (\S+) (\S+) (\S+)", txt).groups()]
                px, py = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
                ex, ey = (cx, cy) if n == "clk" else (rx, ry)
                assert abs(px - ex) < 0.01 and abs(py - ey) < 0.01, (n, px, py, ex, ey)
            L.append(txt)
        ob = src[src.index("\n  OBS"):]
        lay = None
        for ln in ob.splitlines():
            m = re.match(r"\s*LAYER (\S+)", ln)
            if m:
                lay = m.group(1); obs.setdefault(lay, []); continue
            m = re.match(r"\s*RECT\s+(\S+) (\S+) (\S+) (\S+)", ln)
            if m and lay:
                obs[lay] += minus(tuple(map(float, m.groups())), hole)
        pgc = {n: len(re.findall("RECT", txt)) for txt, n in blocks if n in ("VDD", "VSS")}
    else:
        inputs += [("io", A.io), ("old_lef_dirs", A.old_lef)]
        old = Path(A.old_lef).read_text()
        dirs = {n: (re.search(r"DIRECTION (\S+)", b).group(1), re.search(r"USE (\S+)", b).group(1))
                for n, b in re.findall(r"\n  PIN (\S+)\n(.*?)\n  END \1", old, re.S)}
        pins = []
        for ln in Path(A.io).read_text().splitlines():
            m = re.match(r"place_pin -pin_name \{(\S+)\} -layer (\S+) -location \{(\S+) (\S+)\} -pin_size \{(\S+) (\S+)\}", ln)
            if m:
                n, lay = m.group(1), m.group(2)
                x, y, sw, sh_ = map(float, m.group(3, 4, 5, 6))
                pins.append((n, lay, (x - sw / 2, y - sh_ / 2, x + sw / 2, y + sh_ / 2)))
        missing = sorted(set(dirs) - {"VDD", "VSS"} - {p[0] for p in pins})
        extra = sorted({p[0] for p in pins} - set(dirs))
        assert not missing and not extra, (missing, extra)
        npins = len(pins)
        for n, lay, r in sorted(pins):
            d, u = dirs[n]
            L += ["  PIN " + n, "    DIRECTION %s ;" % d, "    USE %s ;" % u, "    PORT", "      LAYER %s ;" % lay, rect(r), "    END", "  END " + n]
        pg = pg_shapes(t, W, core, hole)
        for net, use in (("VDD", "POWER"), ("VSS", "GROUND")):
            L += ["  PIN " + net, "    DIRECTION INOUT ;", "    USE %s ;" % use, "    PORT", "      LAYER M5 ;"]
            L += [rect(r) for _, r in pg[net]] + ["    END", "  END " + net]
        pgc = {n: len(pg[n]) for n in pg}
        for lay in ["RVTN", "RVTP"] + OBS_LAYERS:
            obs[lay] = minus((0, 0, W, H), hole)
    obs.setdefault("M5", []).extend(slots)
    # self-check: nothing but the two M5 slots inside the hole
    inside = [(l, r) for l, rs in obs.items() for r in rs if r[0] < hx1 - 1e-6 and r[2] > hx0 + 1e-6 and r[1] < hy1 - 1e-6 and r[3] > hy0 + 1e-6]
    assert all(l == "M5" and r in slots for l, r in inside), inside
    L += ["  OBS"]
    for lay in sorted(obs):
        L += ["    LAYER %s ;" % lay] + [rect(r) for r in obs[lay]]
    L += ["  END", "END " + name, "", "END LIBRARY", ""]
    os.makedirs(A.out, exist_ok=True)
    lef = Path(A.out) / (name + ".lef")
    lef.write_text("\n".join(L))
    man = {"tool": "tools/s81_head/island_lef.py", "kind": "BUILT abstract, hole cut" if A.from_lef else "PLAN abstract (core not built yet)",
           "type": A.type, "macro": name, "outline_um": [W, H], "hole_um": list(hole), "signal_pins": npins,
           "pg_port_rects": pgc, "hole_contents": "open M1-M7 except the clk/rst_n M5 pins and the two M5 escape slots (OBS)",
           "island_pg": "top-owned: die rows + M1/M2 followpins in the hole + M9->M1 stacks; core PG exposed as M5 stripe ends at the hole N/S edges",
           "m5_escape_slots_obs": slots,
           "inputs": {k: {"path": v, "sha256": hashlib.sha256(Path(v).read_bytes()).hexdigest()} for k, v in inputs},
           "lef_sha256": hashlib.sha256(lef.read_bytes()).hexdigest(),
           "liberty": "not regenerated here (timing views come with the signed-off v2 core)"}
    (Path(A.out) / "MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({k: man[k] for k in ("macro", "kind", "outline_um", "hole_um", "signal_pins", "pg_port_rects")}))


if __name__ == "__main__":
    main()
