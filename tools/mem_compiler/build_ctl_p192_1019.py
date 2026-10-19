#!/usr/bin/env python3
"""KV-SRAM-CTL 10-19: rightsized wide-pin-pitch SRAM family for the KV/system die control tile (qkd_kvs_ctl mu6/mu6b).

Why: the mu5 control tile kept its three runtime tables (lprg stage rows 36 x 256 b, lprg next-gap rows 36 x 168 b, wprg
root rows 36 x 160 b) in three ot_sram_1r1w_128x256_m1_r2c2 masters whose W/E faces carry 410/409 contacts on 41.064 um
(9.98 contacts/um on the full face, 10.42/um on the active span at the compiler's 0.096 um pitch): over the owner's
6 pins/um macro-face rule (codex macro-contact FAIL 2d21b4a75).

What: the UNCHANGED SRAM compiler (sram_gen.py: same bitcell, periphery calibration, timing model, behavioural model and
Liberty writer) with the aligned-v2 outline/LEF wrapper (build_aligned_v2.py), run with the signal pin pitch set to
0.192 um (every fourth 48 nm M4 track) instead of 0.096 um.  The compiler's own pin-limited outline rule then grows the
macro height until every contact fits at that pitch, and reports the stretch (area.outline.pin_stretch_um): the face is
long enough, the contacts are truly spread (5.21 contacts/um on the active span, <= 5.1/um on the full face), no
waiver, halo trick or relabelled master.  Pins stay on track: 0.192 = 4 x 0.048 and the first contact keeps the
0.768 um strap offset, so every contact sits on the same track parity as the 0.096 family.

Rightsizing (truthful): every client table has 36 rows (stage 1..36) and reads/writes row = stage - 1 (6 address bits;
the 128-word masters had address bit 6 tied 0), and the repair ports of the r2c2 masters are tied off in every client
(rr_en/cr_en 0).  The family therefore has 64 words (>= 36, power-of-two decode), no spare rows/columns, the same 1R1W
single-clock port (clk, r_ce_in/r_addr_in/rd_out, w_ce_in/w_addr_in/wd_in/w_mask_in), the same registered one-edge read
and the same behavioural collision semantics (same compiler model).  Widths are banked: 64 b (mu6) or 128 b (mu6b).

    python3 tools/mem_compiler/build_ctl_p192_1019.py            # writes the masters + results/arch/kv_sram_ctl_1019/family.json
    python3 tools/mem_compiler/build_ctl_p192_1019.py --check    # rebuild into a temp dir and compare the view hashes

Claim boundary: calibrated analytical abstracts (as every sram_gen master); no transistor layout, no macro SPICE.
The internal routing from the stretched contacts to the periphery (< pin_stretch_um of M4 per contact) is not in the
compiler's timing model; it is reported, and bounded below in the json (Elmore on ASAP7 M4 RC).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
import asap7  # noqa: E402
import sram_gen as S  # noqa: E402
from build_aligned_v2 import aligned_outline, aligned_write_lef, patched, verify_lef  # noqa: E402

PITCH_UM = 0.192
FACE_MAX_PER_UM = 6.0
MASTERS = [  # (name, words, bits, mux)
    ("ctl_sram_1r1w_64x64_p192", 64, 64, 1),
    ("ctl_sram_1r1w_64x128_p192", 64, 128, 1),
]
# client tables (rows used, bits used) -> banks per master width
CLIENTS = {
    "lprg.u_rowa (stage rows P_ctrl..P_quiet)": (36, 256),
    "lprg.u_rowb (P_end, next gap x4, ==0/==1 flags)": (36, 168),
    "wprg.u_rows (5 cycle32 roots)": (36, 160),
}
M4_R_OHM_PER_UM = 31.25   # ASAP7 setRC M4 (0.024 um wide) order of magnitude, used only for the stretch bound below
M4_C_FF_PER_UM = 0.20


def face_audit(lef_text: str, w: float, h: float) -> dict:
    """Contacts per face from the LEF itself: count, full-face density and worst 1 um window density."""
    faces = {"W": [], "E": [], "N": [], "S": []}
    for m in re.finditer(r"PIN (\S+)\n(.*?)END \1\n", lef_text, re.S):
        name, body = m.group(1), m.group(2)
        if "USE POWER" in body or "USE GROUND" in body:
            continue
        r = re.search(r"RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)", body)
        x1, y1, x2, y2 = map(float, r.groups())
        if x1 <= 1e-6:
            faces["W"].append((y1 + y2) / 2)
        elif abs(x2 - w) <= 1e-6:
            faces["E"].append((y1 + y2) / 2)
        elif abs(y2 - h) <= 1e-6:
            faces["N"].append((x1 + x2) / 2)
        else:
            faces["S"].append((x1 + x2) / 2)
    out = {}
    for f, ys in faces.items():
        if not ys:
            continue
        ys.sort()
        length = h if f in "WE" else w
        win = 0
        j = 0
        for i in range(len(ys)):
            while ys[i] - ys[j] >= 1.0:
                j += 1
            win = max(win, i - j + 1)
        pitch = min((b - a for a, b in zip(ys, ys[1:])), default=None)
        out[f] = {"contacts": len(ys), "face_um": length, "full_face_per_um": round(len(ys) / length, 4),
                  "worst_1um_window": win, "min_pitch_um": round(pitch, 4) if pitch else None,
                  "span_um": round(ys[-1] - ys[0], 3)}
    return out


def build(out_dir: Path) -> dict:
    records = []
    for name, words, bits, mux in MASTERS:
        spec = S.SramSpec(name, words, bits, mux, 1, "1r1w", 0, 0)
        old = asap7.METAL["pin_pitch_um"]
        asap7.METAL["pin_pitch_um"] = PITCH_UM
        try:
            with patched(S, macro_outline=aligned_outline, write_lef=aligned_write_lef):
                sheet = S.compile_macro(spec, out_dir)
        finally:
            asap7.METAL["pin_pitch_um"] = old
        d = out_dir / name
        lef = (d / f"{name}.lef").read_text()
        a = sheet["area"]
        w, h = a["macro_width_um"], a["macro_height_um"]
        faces = face_audit(lef, w, h)
        ver = verify_lef(lef, str(d / f"{name}.lef"))[name]
        worst = max(v["full_face_per_um"] for v in faces.values())
        worst_win = max(v["worst_1um_window"] for v in faces.values())
        assert worst <= FACE_MAX_PER_UM and worst_win <= FACE_MAX_PER_UM, (name, faces)
        assert ver["pass"], (name, ver)
        stretch = a["outline"]["pin_stretch_um"]
        # worst added internal lead: stretch um of M4 driving the periphery input / output (lumped Elmore, ps)
        lead_ps = 0.69 * (M4_R_OHM_PER_UM * stretch) * (M4_C_FF_PER_UM * stretch) * 1e-3 * 0.5
        rec = {"master": name, "words": words, "bits": bits, "mux": mux, "ports": "1r1w (single clock clk)",
               "spare_rows": 0, "spare_cols": 0, "addr_bits": spec.addr_bits,
               "width_um": w, "height_um": h, "area_um2": round(w * h, 4),
               "core_um": [a["core_width_um"], a["core_height_um"]], "pin_stretch_um": stretch,
               "pin_pitch_um": PITCH_UM, "faces": faces, "track_legal_all_orientations": ver["pass"],
               "allowed_orientations": ver["allowed_orientations"],
               "clk_to_q_ps": {c: round(sheet["timing"][c]["clk_to_q_ps"], 2) for c in ("tt", "ss", "ff")},
               "setup_ps": {c: round(sheet["timing"][c]["setup_ps"], 2) for c in ("tt", "ss", "ff")},
               "hold_ps": {c: round(sheet["timing"][c]["hold_ps"], 2) for c in ("tt", "ss", "ff")},
               "min_period_ps": {c: round(sheet["timing"][c]["min_period_ps"], 2) for c in ("tt", "ss", "ff")},
               "stretch_lead_elmore_bound_ps": round(lead_ps, 4),
               "views": sheet["views"]}
        records.append(rec)
    clients = []
    for client, (rows, need) in CLIENTS.items():
        for r in records:
            banks = math.ceil(need / r["bits"])
            clients.append({"client": client, "rows_used": rows, "bits_used": need, "master": r["master"],
                            "banks": banks, "physical_bits": banks * r["bits"] * r["words"],
                            "raw_area_um2": round(banks * r["area_um2"], 3),
                            "capacity_ok": rows <= r["words"] and banks * r["bits"] >= need})
    return {"schema": "opentallas.kv-sram-ctl-family.1019", "pitch_um": PITCH_UM,
            "face_rule": f"<= {FACE_MAX_PER_UM} contacts/um on every pin face (full face AND worst 1 um window)",
            "replaces": {"master": "ot_sram_1r1w_128x256_m1_r2c2", "count": 3,
                         "faces": {"W": [410, 41.064, 9.984], "E": [409, 41.064, 9.960]},
                         "raw_area_um2": round(3 * 3893.853, 3)},
            "masters": records, "clients": clients,
            "kits": {"qkd_kvs_ctl_mu6": "10 x ctl_sram_1r1w_64x64_p192 (rowa 4, rowb 3, rows 3)",
                     "qkd_kvs_ctl_mu6b": "6 x ctl_sram_1r1w_64x128_p192 (rowa 2, rowb 2, rows 2)"},
            "claim_boundary": "calibrated analytical abstracts from the unchanged compiler (bitcell, periphery, timing, "
                              "behaviour); no transistor layout / macro SPICE; stretch lead bounded analytically"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "physical/asap7_memory_macros_v2")
    ap.add_argument("--json", type=Path, default=ROOT / "results/arch/kv_sram_ctl_1019/family.json")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        with tempfile.TemporaryDirectory() as td:
            fam = build(Path(td))
        ok = all(hashlib.sha256((a.out / r["master"] / f).read_bytes()).hexdigest() == h
                 for r in fam["masters"] for f, h in r["views"].items())
        print("CTL_P192_FAMILY", "CHECK PASS" if ok else "CHECK FAIL")
        return 0 if ok else 1
    fam = build(a.out)
    files = [Path(__file__), ROOT / "tools/mem_compiler/sram_gen.py", ROOT / "tools/mem_compiler/views.py",
             ROOT / "tools/mem_compiler/build_aligned_v2.py", ROOT / "tools/mem_compiler/asap7.py",
             ROOT / "tools/mem_compiler/asap7_calibration.json"]
    fam["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    a.json.parent.mkdir(parents=True, exist_ok=True)
    a.json.write_text(json.dumps(fam, indent=1) + "\n")
    for r in fam["masters"]:
        f = r["faces"]
        print(f"{r['master']}: {r['width_um']} x {r['height_um']} um, W {f['W']['contacts']}/{f['W']['full_face_per_um']}/um "
              f"(1um window {f['W']['worst_1um_window']}), E {f['E']['contacts']}/{f['E']['full_face_per_um']}/um, "
              f"cq tt/ss {r['clk_to_q_ps']['tt']}/{r['clk_to_q_ps']['ss']} ps, stretch {r['pin_stretch_um']} um")
    print("CTL_P192_FAMILY PASS face<=6/um (full and 1 um window), track-legal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
