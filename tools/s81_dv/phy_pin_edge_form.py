#!/usr/bin/env python3
"""Emit a separate PHY abstract with one channel's signal pins moved onto a side edge.

PHY-T1-NECORNER-1 (FAM-S81-SERDES-R7 11-23): on phy__t1 the E-face channel (dfi_i0 / hbmrd_o0, macro channel 7 = the
MSB slice of every k_* / kr_* bus) had its pins on the macro N edge at x 8160-8330, interleaved with channel 6
(x 8037-8498).  Its 2488 nets therefore wrapped from the partition E face around the NE corner into the 45-um N strip,
on top of channel 6's pins and the dfi_i6 N-face window: GRT-0116, 44 overflow in 31 gcells at x 8385-8461.
This tool moves the pins named in a spec onto the macro E (or W) edge, one horizontal layer, on that layer's parent
tracks, spread evenly over a per-group y range (the matching partition face window), avoiding the PG stripe bands of
that layer.  The raw input is preserved; outline, ports, timing arcs, RTL and cycles are unchanged.  This is an
explicit new version of the generated PHY macro physical contract (same basis as phy_pin_track_form.py).

  phy_pin_edge_form.py SOURCE.lef OUT_DIR --spec SPEC.json

SPEC: {"edge": "E"|"W", "layer": "M6", "pitch_nm": 64, "offset_nm": 32, "pin_len_nm": 192, "pin_w_nm": 32,
       "origin_um": [x, y]  (macro origin in the parent, for the track phase),
       "pg_bands": [{"period_nm": 4320, "lo_nm": 1968, "hi_nm": 2640}]  (parent coords, same layer, keep clear),
       "clearance_nm": 72,
       "groups": [{"name": .., "range_um": [lo, hi] (macro-local), "order": "asc"|"desc",
                   "bits": [["k_addr", 840, 960], ...]}]}   (pins k_addr[840] .. k_addr[959], in this order)
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

PIN = re.compile(r"(  PIN (\S+)\n)(.*?)(\n  END \2)", re.S)
PORT = re.compile(r"(    PORT\n)(.*?)(\n    END)", re.S)


def pin_names(group):
    out = []
    for bus, lo, hi in group["bits"]:
        out += [f"{bus}[{i}]" for i in range(lo, hi)]
    return out


def tracks(spec, lo_um, hi_um, size_y_nm):
    """parent-track centres (macro-local nm) inside [lo, hi] that keep the clearance to every PG band."""
    pitch, off, w, clr = spec["pitch_nm"], spec["offset_nm"], spec["pin_w_nm"], spec["clearance_nm"]
    oy = round(spec["origin_um"][1] * 1000)
    lo, hi = round(lo_um * 1000), round(hi_um * 1000)
    k0 = -(-(lo + oy - off) // pitch)
    out = []
    k = k0
    while True:
        c = off + k * pitch - oy                         # macro-local centre
        if c > hi:
            break
        k += 1
        if c - w // 2 < 0 or c + w // 2 > size_y_nm or c - w // 2 < lo or c + w // 2 > hi:
            continue
        g = c + oy
        bad = False
        for b in spec.get("pg_bands", []):
            ph = g % b["period_nm"]
            for shift in (-b["period_nm"], 0, b["period_nm"]):
                blo, bhi = b["lo_nm"] + shift, b["hi_nm"] + shift
                if ph + w // 2 + clr > blo and ph - w // 2 - clr < bhi:
                    bad = True
        if not bad:
            out.append(c)
    return out


def pick(cands, n, min_step_nm):
    assert n <= len(cands), (n, len(cands))
    if n == 1:
        return [cands[len(cands) // 2]]
    idx = [round(i * (len(cands) - 1) / (n - 1)) for i in range(n)]
    got = [cands[i] for i in idx]
    steps = [b - a for a, b in zip(got, got[1:])]
    assert min(steps) >= min_step_nm, ("pins too dense for the range", min(steps), min_step_nm)
    return got


def transform(text, spec):
    size = re.search(r"SIZE ([\d.]+) BY ([\d.]+)", text)
    sx, sy = (round(float(v) * 1000) for v in size.groups())
    edge, layer, plen, w = spec["edge"], spec["layer"], spec["pin_len_nm"], spec["pin_w_nm"]
    assert edge in ("E", "W")
    x0, x1 = (sx - plen, sx) if edge == "E" else (0, plen)
    min_step = w + spec["clearance_nm"]
    target, report_groups = {}, []
    for g in spec["groups"]:
        names = pin_names(g)
        cands = tracks(spec, g["range_um"][0], g["range_um"][1], sy)
        ys = pick(cands, len(names), min_step)
        if g.get("order", "asc") == "desc":
            ys = ys[::-1]
        for n, y in zip(names, ys):
            assert n not in target, ("pin in two groups", n)
            target[n] = y
        report_groups.append({"name": g["name"], "pins": len(names), "range_um": g["range_um"],
                              "candidate_tracks": len(cands), "min_step_nm": min(b - a for a, b in zip(sorted(ys), sorted(ys)[1:]))
                              if len(ys) > 1 else None})
    seen = set()

    def pin(m):
        name, body = m[2], m[3]
        if name not in target:
            return m[0]
        seen.add(name)
        assert len(PORT.findall(body)) == 1, ("pin with more than one PORT", name)
        y = target[name]
        rect = f"      LAYER {layer} ;\n      RECT {x0/1000:.3f} {(y - w//2)/1000:.3f} {x1/1000:.3f} {(y + w//2)/1000:.3f} ;"
        return m[1] + PORT.sub(lambda p: p[1] + rect + p[3], body) + m[4]

    out = PIN.sub(pin, text)
    missing = sorted(set(target) - seen)
    assert not missing, ("spec pins not in the LEF", missing[:5], len(missing))
    # same-layer clearance among the moved pins (other pins never use this edge strip)
    ys = sorted(target.values())
    gap = min(b - a for a, b in zip(ys, ys[1:])) - w if len(ys) > 1 else None
    assert gap is None or gap >= spec["clearance_nm"], gap
    for m in PIN.finditer(out):
        if m[2] in target:
            assert re.findall(r"LAYER (\S+) ;", m[3]) == [layer], ("moved pin keeps an old shape", m[2])
    report = {"schema": "opentallas.phy.pin_edge_form.v1", "moved_pins": len(target), "edge": edge, "layer": layer,
              "edge_rect_x_nm": [x0, x1], "groups": report_groups, "minimum_same_layer_clearance_nm": gap,
              "names_sha256": hashlib.sha256("\n".join(sorted(target)).encode()).hexdigest(),
              "outline_unchanged": True, "added_cells": 0, "added_cycles": 0, "timing_arcs_unchanged": True,
              "pg_bands": spec.get("pg_bands", []), "origin_um": spec["origin_um"],
              "contract_basis": "Generated PHY macro abstract, not a routed hard-child/GDS view. Pin moves are explicit "
                                "new physical contract; timing arcs unchanged, no invented routed timing."}
    return out, report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--spec", type=Path, required=True)
    args = ap.parse_args()
    spec = json.loads(args.spec.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    raw = args.source.read_text()
    out, report = transform(raw, spec)
    (args.out / (args.source.stem + ".raw.lef")).write_text(raw)
    (args.out / args.source.name).write_text(out)
    (args.out / "pin_edge_spec.json").write_text(json.dumps(spec, indent=1) + "\n")
    report["source_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    report["output_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    (args.out / "pin_access.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
