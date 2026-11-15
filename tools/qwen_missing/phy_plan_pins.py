#!/usr/bin/env python3
"""QC PHY macro abstracts with the FDI pins ON the die-plan pin sites (FABLE-PD-PHY-0710 fix 4/5, QC-PHYSERDES).

The plan of record (S4P) declares every PHY bus as a face window with a layer list; tools/die_plan/schema.py
pin_positions() turns that into one track-snapped pin site per bit (epoch bit included in the spread, as Plan.port_pins
does for a lane port).  The earlier abstracts (nface_tall_1017, qwen_kv_die_phy) put a centred block on M5 instead, so
the macro pins were 0-383 um (2,972 um for phy_serdes_b: N edge macro, E-face windows) from the windows.

This tool rewrites ONLY the signal PIN blocks and the OBS block of an existing LEF: pin names, directions, VDD/VSS,
SIZE and every other view (LIB, blackbox, model) are kept; the E-face variant (phy_serdes_b) renames the macro with a
suffix so one flow never sees two LEFs under one cell name (LIB / bb / model are the same text with the name replaced).
Pins without a plan bus (clk, rst_n, UCIe line side) go on a free block of the same edge, clear of every plan pin.

  python3 tools/qwen_missing/phy_plan_pins.py --plan-types tests/qc_phy_s4p_types.json --out physical/qwen_missing_phy/qc_s4p_1115
  (then the ucie view dir moves to physical/qwen_kv_die_phy/qc_s4p_1115/)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402

LAYERS = {L["name"]: L for L in S.ASAP7_LAYERS}
PIN_LEN = 0.192
OBS_CLEAR = 0.4          # M4/M5 OBS stops this far from an edge that carries M4 pins (as the west-face variant)
SPEC = {   # type -> (face, old view dir, macro name, new macro name, leftover layer, leftover start um)
    "phy_serdes": dict(src="physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597", dst="qwen_missing_phy",
                       name="ot_qfd_serdes_112g_x12_phy_s597", new="ot_qfd_serdes_112g_x12_phy_s597", rest_start=100.0),
    "phy_serdes_b": dict(src="physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597", dst="qwen_missing_phy",
                         name="ot_qfd_serdes_112g_x12_phy_s597", new="ot_qfd_serdes_112g_x12_phy_s597_e", rest_start=600.0),
    "phy_ucie_kv": dict(src="physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy", dst="qwen_kv_die_phy",
                        name="ot_qkvd_ucie_x64_phy", new="ot_qkvd_ucie_x64_phy", rest_start=300.0),
}


def pin_width(layer: str) -> float:
    return round(LAYERS[layer]["pitch_um"] / 2.0, 4)


def pin_name(leaf: str, bit: int, width: int) -> str:
    base = leaf.rsplit(".", 1)[-1]
    return f"{base}[{bit}]" if width > 1 else base


def plan_sites(tinfo: dict, epoch: bool = True) -> dict:
    """{macro pin name: (layer, coord along the face, face)} from the type's bus table, per plan pin_positions."""
    out = {}
    for b in tinfo["buses"]:
        port = dict(id=b["name"], width=b["width"], kind=b["kind"], face=b["face"], window_um=b["window_um"],
                    layers=b["layers"], order=b.get("order", "lsb_low"), epoch=epoch)
        for bit, ln, c in S.pin_positions(port, LAYERS):
            if bit < b["width"]:                      # the epoch bit (index == width) is a wrapper pin, not a macro pin
                out[pin_name(b["leaf"], bit, b["width"])] = (ln, c, b["face"])
    return out


def plan_only_pins(sites: dict, lef_text: str) -> list:
    return sorted(set(sites) - {p for p, _d, _u in parse_lef(lef_text)[1]})


def parse_lef(text: str):
    """(header lines up to the first PIN, [(name, direction, use)] signal pins, [VDD/VSS blocks], SIZE (w, h), name)."""
    m = re.search(r"SIZE ([\d.]+) BY ([\d.]+) ;", text)
    w, h = float(m.group(1)), float(m.group(2))
    pos = text.index("  PIN ")
    head = text[:pos]
    obs = text.index("  OBS")
    body = text[pos:obs]
    blocks = re.findall(r"  PIN (\S+)\n(.*?)  END \1\n", body, re.S)
    sig, pg = [], []
    for name, b in blocks:
        if name in ("VDD", "VSS"):
            pg.append(f"  PIN {name}\n{b}  END {name}\n")
        else:
            d = re.search(r"DIRECTION (\w+) ;", b).group(1)
            u = re.search(r"USE (\w+) ;", b).group(1)
            sig.append((name, d, u))
    return head, sig, pg, (w, h), re.search(r"MACRO (\S+)", text).group(1)


def track_after(layer: str, c0: float) -> int:
    L = LAYERS[layer]
    return math.ceil((c0 - L["offset_um"]) / L["pitch_um"] - 1e-9)


def build_lef(text: str, sites: dict, face: str, rest_start: float, new_name: str | None = None):
    head, sig, pg, (w, h), name = parse_lef(text)
    new_name = new_name or name
    rest_layer = "M5" if face == "N" else "M4"
    L = LAYERS[rest_layer]
    taken = {(ln, round(c, 6)) for ln, c, _ in sites.values()}
    k = track_after(rest_layer, rest_start)
    pos, rest = {}, 0
    sites = {k_: v for k_, v in sites.items() if k_ in {p for p, _d, _u in sig}}
    for pn, _d, _u in sig:
        if pn in sites:
            pos[pn] = sites[pn][:2]
            continue
        while (rest_layer, round(L["offset_um"] + k * L["pitch_um"], 6)) in taken:
            k += 1
        pos[pn] = (rest_layer, round(L["offset_um"] + k * L["pitch_um"], 6))
        k += 1
        rest += 1
    # plan buses with no macro pin (UCIe phy_rst_i: absent from the LIB / bb.v, LIB stays unchanged) are a plan content
    # matter (contents[].local_reset_pins), listed by plan_only_pins()
    out = []
    for pn, d, u in sig:
        ln, c = pos[pn]
        hw = pin_width(ln) / 2.0
        if face == "N":
            rect = f"{c - hw:.3f} {h - PIN_LEN:.3f} {c + hw:.3f} {h:.3f}"
        else:
            rect = f"{w - PIN_LEN:.3f} {c - hw:.3f} {w:.3f} {c + hw:.3f}"
        out.append(f"  PIN {pn}\n    DIRECTION {d} ;\n    USE {u} ;\n    SHAPE ABUTMENT ;\n    PORT\n      LAYER {ln} ;\n"
                   f"      RECT {rect} ;\n    END\n  END {pn}\n")
    if face == "N":
        obs = [(1, w, h), (2, w, h), (3, w, h), (4, w, h), (5, w, h - OBS_CLEAR)]
    else:
        obs = [(1, w, h), (2, w, h), (3, w, h), (4, w - OBS_CLEAR, h), (5, w - OBS_CLEAR, h)]
    ob = ["  OBS"]
    for k_, ow, oh in obs:
        ob += [f"    LAYER M{k_} ;", f"    RECT 0 0 {ow:.3f} {oh:.3f} ;"]
    ob += ["  END", f"END {new_name}", "", "END LIBRARY", ""]
    new_head = head.replace(name, new_name) if new_name != name else head
    new_head = new_head.replace("link_phy_gen.py:", "phy_plan_pins.py (plan pin sites, QC S4P):", 1)
    return new_head + "".join(out) + "".join(pg) + "\n".join(ob), pos, rest


def generate(types_json: Path, out_root: Path, repo: Path = ROOT) -> dict:
    tj = json.loads(types_json.read_text())
    res = {}
    for t, sp in SPEC.items():
        tinfo = tj["types"][t]
        src = repo / sp["src"]
        old = sp["name"]
        face = tinfo["buses"][0]["face"]
        sites = plan_sites(tinfo)
        lef, pos, rest = build_lef((src / f"{old}.lef").read_text(), sites, face, sp["rest_start"], sp["new"])
        d = out_root / sp["new"]
        po = plan_only_pins(sites, (src / f"{old}.lef").read_text())
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{sp['new']}.lef").write_text(lef)
        for f in sorted(src.iterdir()):
            if f.name == f"{old}.lef" or f.name == f"{old}.json":
                continue
            (d / f.name.replace(old, sp["new"])).write_text(f.read_text().replace(old, sp["new"]))
        sheet = json.loads((src / f"{old}.json").read_text())
        sheet = json.loads(json.dumps(sheet).replace(old, sp["new"]))
        sheet["generator"] = "tools/qwen_missing/phy_plan_pins.py"
        sheet["derived_from"] = (f"{sp['src']} (same footprint, latency, timing, LIB); FDI pins on the S4P plan pin sites of "
                                 f"{t} ({face} face), plan sha256 {tj['plan_sha256']}")
        sheet["pins"] = dict(sheet.get("pins", {}), pin_edge=f"{face} (plan pin sites, per-bit)", plan_type=t,
                             plan_sha256=tj["plan_sha256"], plan_pins=len(sites) - len(po), plan_only_pins=po, free_block_pins=rest,
                             pin_layer="/".join(sorted({ln for ln, _c, _f in sites.values()})))
        sheet.pop("views", None)
        sheet["views"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                          for f in sorted(d.iterdir()) if f.name != f"{sp['new']}.json"}
        (d / f"{sp['new']}.json").write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
        res[t] = dict(dir=str(d), plan_pins=len(sites) - len(po), plan_only_pins=po, free_pins=rest, face=face)
    return res


def lef_pin_centres(lef_text: str, face: str) -> dict:
    """{pin: (layer, centre coord along the face)} of the first port rect of every signal pin."""
    out = {}
    for name, b in re.findall(r"  PIN (\S+)\n(.*?)  END \1\n", lef_text, re.S):
        if name in ("VDD", "VSS"):
            continue
        ln = re.search(r"LAYER (\S+) ;", b).group(1)
        x0, y0, x1, y1 = map(float, re.search(r"RECT (\S+) (\S+) (\S+) (\S+) ;", b).groups())
        out[name] = (ln, round((x0 + x1) / 2 if face == "N" else (y0 + y1) / 2, 6))
    return out


def offsets(tinfo: dict, lef_text: str, origin_um=(0.0, 0.0)) -> dict:
    """per bus: pin count, max |lateral offset| of a macro pin from its plan pin site (um, type frame), pins off layer,
    pins outside the bus window.  origin_um = macro origin in the partition (type frame)."""
    face = tinfo["buses"][0]["face"]
    sites = plan_sites(tinfo)
    pins = lef_pin_centres(lef_text, face)
    ax = 0 if face == "N" else 1
    res = {}
    for b in tinfo["buses"]:
        lo, hi = sorted(b["window_um"])
        names = [pin_name(b["leaf"], i, b["width"]) for i in range(b["width"])]
        have = [n for n in names if n in pins]
        offs = [abs(pins[n][1] + origin_um[ax] - sites[n][1]) for n in have]
        res[b["name"]] = dict(pins=len(have), of=len(names), max_offset_um=round(max(offs), 6) if offs else None,
                              wrong_layer=sum(pins[n][0] != sites[n][0] for n in have),
                              outside_window=sum(not (lo - 1e-6 <= pins[n][1] + origin_um[ax] <= hi + 1e-6) for n in have))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan-types", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="view revision root; kv views go to <out>/<macro>/")
    a = ap.parse_args()
    print(json.dumps(generate(a.plan_types, a.out), indent=1))


if __name__ == "__main__":
    main()
