#!/usr/bin/env python3
"""S81-HEAD island-driven lattice clock mesh (HEAD-CORE-LAT/DIECLK 2026-10-26, INFRA-FIRST method item 2).

Wraps tools/die_plan/die_clock_mesh.py (no fork): same build/balance/combo/mesh/stubsta/report, with three overrides
read from results/head_core_lat_1026/island_spec.json:
  1. keep-outs: every hard core's rect has its ONE top-owned 8.64x8.64 infra-island hole cut out, so die clock cells
     placed at a core site land only in that hole (MODEL ASSUMPTION: the hole is a legal top-level site; the current
     kit abstracts still OBS the hole -- see report).  PHY macro rects stay keep-outs.  Soft partitions stay legal
     (soft islands, no hard-core change).
  2. straps: the uniform nx x ny strap targets snap to the nearest hole-centre lattice line (x/y) or, outside the
     hole array, to the serdes digital-strip centre lines / uniform soft-area lines; no strap runs over a PHY macro.
  3. taps: each core clk_c<k> tap moves to its island clk pin (hole centre x, hole top y) and its early shift is 0:
     every core tap gets the same declared intrinsic insertion T (COMMON_T_PS, one parameter); glue taps are padded to
     T by stub trim (die absorbs residuals, method item 7), so pair skew at the taps is the die's share.
usage: island_clock_mesh.py --spec SPEC [--T-tt 405 --T-ff 325] <die_clock_mesh.py subcommand + args>
"""
import argparse, bisect, json, math, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import die_clock as DC          # noqa: E402
import types as _types          # noqa: E402
# die_clock_mesh.build hard-codes a uniform strap grid; load it with ONE textual hook (no fork): explicit axes if set.
_src = (HERE.parent / "die_plan" / "die_clock_mesh.py").read_text()
for _ax, _n, _L in (("xs", "nx", "W"), ("ys", "ny", "H")):
    _old = f"    {_ax} = [({'i' if _ax == 'xs' else 'j'} + 0.5) * {_L} / {_n} for {'i' if _ax == 'xs' else 'j'} in range({_n})]\n"
    assert _src.count(_old) == 1, _old
    _src = _src.replace(_old, _old.replace(f"{_ax} = [", f"{_ax} = _AXES['{_ax}'] if _AXES else ["))
DCM = _types.ModuleType("die_clock_mesh")
DCM.__file__ = str(HERE.parent / "die_plan" / "die_clock_mesh.py")
DCM._AXES = {}
sys.modules["die_clock_mesh"] = DCM
exec(compile(_src, DCM.__file__, "exec"), DCM.__dict__)

HOLE = 8.64


def load_spec(p):
    s = json.loads(Path(p).read_text())
    holes = [dict(part=i["part"], inst=i["inst"], x=i["die_hole_um"][0], y=i["die_hole_um"][1]) for i in s["instances"]]
    return s, holes


def install(spec_path, T):
    spec, holes = load_spec(spec_path)
    orig_keepouts, orig_taps, orig_early = DC.keepouts, DC.plan_taps, DC.plan_tap_early
    hb = {}
    for h in holes:
        hb.setdefault((int(h["x"] // 500), int(h["y"] // 500)), []).append(h)

    def cut(r, h):
        x0, y0, x1, y1, nm = r
        hx0, hy0, hx1, hy1 = h["x"], h["y"], h["x"] + HOLE, h["y"] + HOLE
        out = [(x0, y0, x1, hy0, nm + "/S"), (x0, hy1, x1, y1, nm + "/N"),
               (x0, hy0, hx0, hy1, nm + "/W"), (hx1, hy0, x1, hy1, nm + "/E")]
        return [q for q in out if q[2] - q[0] > 1e-6 and q[3] - q[1] > 1e-6]

    def keepouts(P):
        out = []
        for r in orig_keepouts(P):
            inside = [h for i in range(int(r[0] // 500), int(r[2] // 500) + 1) for j in range(int(r[1] // 500), int(r[3] // 500) + 1)
                      for h in hb.get((i, j), []) if r[0] <= h["x"] and h["x"] + HOLE <= r[2] and r[1] <= h["y"] and h["y"] + HOLE <= r[3]]
            if len(inside) == 1:
                out += cut(r, inside[0])
            else:
                if len(inside) > 1:
                    raise SystemExit(f"island: {len(inside)} holes inside one keep-out {r[4]}")
                out.append(r)
        return out

    by_part = {}
    for h in holes:
        by_part.setdefault(h["part"], []).append(h)

    def core_pin(part, x, y):
        hs = by_part.get(part) or []
        if not hs:
            return None
        h = min(hs, key=lambda h: abs(h["x"] + HOLE / 2 - x) + abs(h["y"] + HOLE / 2 - y))
        return (round(h["x"] + HOLE / 2, 4), round(h["y"] + HOLE, 4))

    moved = []

    by_inst = {(h["part"], h["inst"]): h for h in holes}
    # v2 spec (12.8a): clk pin = hole centre; v1: hole N edge
    pin_centre = all("centre" in str(t.get("pins", {}).get("clk", {}).get("edge", "")) for t in spec["types"].values())
    import schema as S

    def plan_taps(P):
        out = []
        port_inst = {}
        for n, p in P.parts.items():
            for nm, _, _, tp in S.core_taps(P, p["type"]):
                port_inst[(n, nm)] = (tp.get("name") if isinstance(tp, dict) else str(tp)).rsplit(".clk", 1)[0]
        for part, port, x, y, early in orig_taps(P):
            if (part, port) in port_inst:
                h = by_inst.get((part, port_inst[(part, port)]))
                q = None if h is None else (round(h["x"] + HOLE / 2, 4), round(h["y"] + (HOLE / 2 if pin_centre else HOLE), 4))
                if q is None:
                    raise SystemExit(f"island: core tap {part}/{port} has no island")
                moved.append(abs(q[0] - x) + abs(q[1] - y))
                out.append((part, port, q[0], q[1], 0.0))
            else:
                out.append((part, port, x, y, early))
        return out

    def plan_tap_early(P):
        return {k: {"TT": 0.0, "FF": 0.0} for k in orig_early(P)}

    strict = bool(os.environ.get("ISLAND_STRICT"))
    if strict:
        # hd_tile glue is NOT a die-cell site: inside a tile only the five core holes are legal (other soft partitions =
        # soft islands, model); clock-cell occupancy rects are always honoured first.
        base_keepouts = keepouts
        tb = {}

        def keepouts(P):   # noqa: F811  (census = hard cores with holes cut + PHY; tile glue only blocks the SEARCH)
            if not tb:
                for n, p in P.parts.items():
                    if p["type"] == "hd_tile":
                        r = tuple(P.rect(n))[:4]
                        for i in range(int(r[0] // 500), int(r[2] // 500) + 1):
                            for j in range(int(r[1] // 500), int(r[3] // 500) + 1):
                                tb.setdefault((i, j), []).append(r)
            return base_keepouts(P)
        allowed = [(h["x"] + 2.2, h["y"] + 0.9, h["x"] + HOLE - 2.2, h["y"] + HOLE - 0.9) for h in holes]
        ab = {}
        for r in allowed:
            ab.setdefault((int(r[0] // 500), int(r[1] // 500)), []).append(r)
        orig_hit = DC.KeepIndex.hit

        def hit(self, x, y, m=0.5):
            for r in self.g.get((int(x // self.b), int(y // self.b)), ()):
                if len(r) > 4 and str(r[4]).startswith("clock:") and r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m:
                    return r
            for r in ab.get((int(x // 500), int(y // 500)), ()):
                if r[0] <= x <= r[2] and r[1] <= y <= r[3]:
                    return None
            for r in tb.get((int(x // 500), int(y // 500)), ()):
                if r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m:
                    return tuple(r) + ("tile_glue",)
            return orig_hit(self, x, y, m)
        DC.KeepIndex.hit = hit
    DC.keepouts, DC.plan_taps, DC.plan_tap_early = keepouts, plan_taps, plan_tap_early
    if hasattr(DCM, "DC"):
        DCM.DC = DC

    # strap lattice: hole centre lines + serdes strip centres + uniform soft-area lines, never over a PHY macro
    hx = sorted({round(h["x"] + HOLE / 2, 4) for h in holes})
    hy = sorted({round(h["y"] + HOLE / 2, 4) for h in holes})
    orig_build = DCM.build

    def build(P, nx=64, ny=64, *a, **kw):
        W, H = float(P.W), float(P.H)
        phys = [io["rect_um"] for io in (P.die.get("io") or []) if io.get("rect_um") and io.get("kind") in ("phy_macro", "phy", "serdes")]
        ylo_phy = max(r[3] for r in phys if r[1] < H / 2)
        yhi_phy = min(r[1] for r in phys if r[1] > H / 2)
        s_lo = [p for p in P.parts if P.types[P.parts[p]["type"]].get("name", P.parts[p]["type"]) == "hd_serdes" or P.parts[p]["type"] == "hd_serdes"]
        sb = [P.rect(p) for p in s_lo]
        strip_s = (ylo_phy + max(r[3] for r in sb if r[1] < H / 2)) / 2
        strip_n = (yhi_phy + min(r[1] for r in sb if r[1] > H / 2)) / 2

        def axis(n, span, hole_lines, lo, hi, extra):
            cand = []
            # hole lines inside the array; uniform soft lines outside it (step = hole lattice median pitch)
            step = 8.64 * round(sorted(b - a for a, b in zip(hole_lines, hole_lines[1:]))[len(hole_lines) // 2] / 8.64)
            x = hole_lines[0] - step
            while x > lo:
                cand.append(x); x -= step
            x = hole_lines[-1] + step
            while x < hi:
                cand.append(x); x += step
            cand = sorted(set(cand + hole_lines + extra))
            # soft columns/rows inside the array with no hole line (e.g. the hd_spn spine): uniform soft lines
            fill = []
            for p, q in zip(cand, cand[1:]):
                k = int((q - p) // step)
                if q - p > 1.5 * step:
                    fill += [p + (q - p) * t / (k + 1) for t in range(1, k + 1)]
            cand = sorted(set(cand + fill))
            out, used = [], set()
            for i in range(n):
                t = lo + (i + 0.5) * (hi - lo) / n
                best = min((c for c in cand if c not in used), key=lambda c: abs(c - t))
                used.add(best); out.append(best)
            return sorted(out)
        xs = axis(nx, W, hx, 104.0, W - 104.0, [])
        ys = axis(ny, H, hy, strip_s, strip_n, [strip_s, strip_n])
        ys[0], ys[-1] = strip_s, strip_n
        if os.environ.get("ISLAND_UNIFORM"):
            # equal-length H-tree by construction: uniform strap pitch (x over the die, y between the two serdes
            # digital-strip straps); drivers then slide along their strap to the nearest island.
            xs = [(i + 0.5) * W / nx for i in range(nx)]
            ys = [strip_s + j * (strip_n - strip_s) / (ny - 1) for j in range(ny)]
        rx = [(i + 0.5) * W / nx for i in range(nx)]
        DCM._AXES.update(xs=xs, ys=ys)
        try:
            cells, nets, ports, out = orig_build(P, nx, ny, *a, **kw)
        finally:
            DCM._AXES.clear()
        on_hole_x = sum(1 for x in xs if any(abs(x - h) < 1e-3 for h in hx))
        on_hole_y = sum(1 for y in ys if any(abs(y - h) < 1e-3 for h in hy))
        out["meta"].update(island_spec=str(spec_path), island_lattice=dict(
            xs_on_hole_lines=on_hole_x, ys_on_hole_lines=on_hole_y, hole_x_lines=len(hx), hole_y_lines=len(hy),
            strip_s_um=strip_s, strip_n_um=strip_n, xs=xs, ys=ys,
            strap_x_snap_max_um=round(max(abs(p - q) for p, q in zip(xs, rx)), 2)),
            common_core_T_ps=T, core_tap_move_max_um=round(max(moved or [0]), 2), core_taps_moved=len(moved),
            model_assumption="core infra-island holes treated as legal top-level sites (kit abstracts not yet cut)")
        return cells, nets, ports, out

    DCM.build = build
    return spec


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--T-tt", type=float, default=250.0)
    ap.add_argument("--T-ff", type=float, default=202.5)
    a, rest = ap.parse_known_args()
    install(a.spec, {"TT": a.T_tt, "FF": a.T_ff})
    return DCM.main(rest)


if __name__ == "__main__":
    sys.exit(main())
