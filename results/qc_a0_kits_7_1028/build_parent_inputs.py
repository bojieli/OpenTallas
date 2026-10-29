#!/usr/bin/env python3
"""QC-A0-KITS-7 10-28 (successor of results/qc_a0_kits_6_1028/build_parent_inputs.py; changes marked K7):
  K7a children sites = the fixture sites through ONE placement rule (cores/a0/parent/a0_child_sites.py: M5 track phase
      per orientation + >= 10.8 um channels), fixing KIT_PREFLIGHT macro_pin_grid (MY rawleaf 24 nm off M5) and
      macro_channels (5.184 um column gap);
  K7b plan pins on their face: the plan table cores/a0_{nk,nl}_pins.json took the legacy ref-gate pin SHAPE centres
      (W x 0.096 / E x 457.824 = a 0.192-um pin); the kit places the standard 0.084-um M4 edge pin (centre 0.042 /
      457.878), so KIT_PREFLIGHT pins_canonical saw 1041/1042 pins differ (only ck, slice-placed, matched).  The pin
      table here is written ON the face (along-face track coordinate unchanged, same snap as gen_core_kit_qc.py io.tcl).
QC-A0-KITS-6 10-28: die-local inputs of the A0 parent (macro-composed) kits qfd_tile_n{k,l}_a0c, written beside
recipes_a0.json.  Sources (all recorded with sha256 in parent/inputs.json):
  * children sites = Codex A0 child fixture parent_{nk,nl}_children.json (at_exact origins, orient; QC-A0-KITS-3 parent
    trial + DIE-QC-14..17 trunks use the same sites);
  * parent cut RTL = Codex native LSL fault cut wrapper (codex/qc-a0-2157@b7da9afaa rawfault_cut/native_wrapper.v with
    rawleaf_bb.v inserted = intel2 codex-qc-a0-2157/parent_rawcut/rtl/ot_qwen_tile_lsl.sv; parent synth 64,205 cells);
  * pins = plan cores/a0_{nk,nl}_pins.json (geometry unchanged) + dir from the RTL top ports (SYNTHESIS, no tap defines).
    python3 build_parent_inputs.py FIXTURE_DIR CUT_RTL"""
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
QC = REPO / "physical/die_plan/qwen_compute"
OUT = QC / "cores/a0/parent"
sys.path.insert(0, str(QC / "cores/legacy"))
import gen_core_kit_qc as G  # noqa: E402
sys.path.insert(0, str(OUT))
import a0_child_sites as S  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def strip_ifdef(text, defined=("SYNTHESIS",)):
    """drop `ifdef X ... `endif blocks whose X is not defined (nested), keep `ifndef SYNTHESIS false branches out"""
    out, stack = [], []
    for ln in text.splitlines():
        m = re.match(r"\s*`(ifdef|ifndef)\s+(\w+)", ln)
        if m:
            on = (m.group(2) in defined) == (m.group(1) == "ifdef")
            stack.append(on)
            continue
        if re.match(r"\s*`else\b", ln):
            stack[-1] = not stack[-1]
            continue
        if re.match(r"\s*`endif\b", ln):
            stack.pop()
            continue
        if all(stack):
            out.append(ln)
    return "\n".join(out)


def main():
    fx, cut = Path(sys.argv[1]), Path(sys.argv[2])
    rec = {}
    (OUT / "rtl").mkdir(parents=True, exist_ok=True)
    cb = cut.read_bytes()
    (OUT / "rtl/ot_qwen_tile_lsl_rawcut.v").write_bytes(cb)
    rec["cut_rtl"] = dict(src=str(cut), sha256=sha(cb))
    for t in ("nk", "nl"):
        fb = (fx / f"parent_{t}_children.json").read_bytes()
        src = json.loads(fb)
        placed = S.place(src)                                  # K7a: one site rule
        ch = [dict(inst=c["inst"], module=c["module"], at=[p["x"] / S.NM, c["at"][1]], orient=c["orient"],
                   size_um=c["size_um"]) for c, p in zip(src, placed)]
        moves = {c["inst"]: round(d["at"][0] - c["at"][0], 3) for c, d in zip(src, ch) if d["at"][0] != c["at"][0]}
        (OUT / f"{t}_children.json").write_text(json.dumps(dict(
            schema="opentallas.qc.a0_parent_children.v1", parent=f"qfd_tile_{t}_a0c",
            source=f"Codex A0 child fixture parent_{t}_children.json (sha256 {sha(fb)})", site_rule=S.RULE, moves_um=moves,
            children=ch), indent=1) + "\n")
        rec[f"{t}_children"] = dict(src=str(fx / f"parent_{t}_children.json"), sha256=sha(fb), n=len(ch))
        mod = f"qfd_tile_{t}_a0c"
        rtl = strip_ifdef((REPO / f"rtl/physical/a0_core/{mod}.sv").read_text())
        dirs = G.rtl_port_dirs(rtl, mod) or {}
        pb = (QC / f"cores/a0_{t}_pins.json").read_bytes()
        doc = json.loads(pb)
        base = lambda n: re.sub(r"\[\d+\]$", "", n)
        miss = sorted({base(q["name"]) for q in doc["pins"] if base(q["name"]) not in dirs})
        if miss:
            raise SystemExit(f"{mod}: plan pins without an RTL port: {miss[:6]}")
        pins, snapped = [], 0
        W, H = map(float, re.findall(r"outline ([0-9.]+) x ([0-9.]+)", doc["frame"])[0])
        for q in doc["pins"]:                                   # K7b: pin centre on its face
            q = dict(q, dir={"INPUT": "in", "OUTPUT": "out"}[dirs[base(q["name"])][0]])
            f = G.face_of(q["x"], q["y"], W, H)
            pw, ph = G.RECT[q["layer"]]
            k, v = {"W": ("x", pw / 2), "E": ("x", W - pw / 2), "S": ("y", ph / 2), "N": ("y", H - ph / 2)}[f]
            if abs(q[k] - v) > 1e-3:
                if abs(q[k] - v) > 3.0:
                    raise SystemExit(f"{mod}: pin {q[name]} {abs(q[k] - v):.3f} um off its {f} face")
                q[k] = round(v, 4)
                snapped += 1
            pins.append(q)
        out = dict(schema="opentallas.core_pins.v1", core=mod, frame=doc.get("frame"),
                   source=f"plan cores/a0_{t}_pins.json (sha256 {sha(pb)}) centres on their face (K7b; along-face track unchanged) + dir from the RTL top "
                          f"ports of rtl/physical/a0_core/{mod}.sv (SYNTHESIS, no OT_A0_CK_TAPS)", pins=pins)
        (OUT / f"a0_{t}_pins_dir.json").write_text(json.dumps(out, indent=1) + "\n")
        rec[f"{t}_pins"] = dict(src=f"cores/a0_{t}_pins.json", sha256=sha(pb), n=len(pins),
                                ports_rtl=len(dirs), ports_unpinned=sorted(set(dirs) - {base(q['name']) for q in pins}), face_snapped=snapped)
    (OUT / "inputs.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
