#!/usr/bin/env python3
"""QC-A0-KITS-6 10-28: die-local inputs of the A0 parent (macro-composed) kits qfd_tile_n{k,l}_a0c, written beside
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
        ch = [dict(inst=c["inst"], module=c["module"], at=c["at"], orient=c["orient"], size_um=c["size_um"])
              for c in json.loads(fb)]
        (OUT / f"{t}_children.json").write_text(json.dumps(dict(
            schema="opentallas.qc.a0_parent_children.v1", parent=f"qfd_tile_{t}_a0c",
            source=f"Codex A0 child fixture parent_{t}_children.json (sha256 {sha(fb)})", children=ch), indent=1) + "\n")
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
        pins = [dict(q, dir={"INPUT": "in", "OUTPUT": "out"}[dirs[base(q["name"])][0]]) for q in doc["pins"]]
        out = dict(schema="opentallas.core_pins.v1", core=mod, frame=doc.get("frame"),
                   source=f"plan cores/a0_{t}_pins.json (sha256 {sha(pb)}) geometry unchanged + dir from the RTL top "
                          f"ports of rtl/physical/a0_core/{mod}.sv (SYNTHESIS, no OT_A0_CK_TAPS)", pins=pins)
        (OUT / f"a0_{t}_pins_dir.json").write_text(json.dumps(out, indent=1) + "\n")
        rec[f"{t}_pins"] = dict(src=f"cores/a0_{t}_pins.json", sha256=sha(pb), n=len(pins),
                                ports_rtl=len(dirs), ports_unpinned=sorted(set(dirs) - {base(q['name']) for q in pins}))
    (OUT / "inputs.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
