#!/usr/bin/env python3
"""hgi-e2e harness driver: prepare a golden export for tb_hgi_e2e, emit the Verilator build / run script, and report.

    python3 tools/hgi_e2e/run.py prep EXPORT_DIR                  -> recs.txt, prep.txt, host.mem, image_e2e.bin
    python3 tools/hgi_e2e/run.py script --vehicle V --real dma,quant,idx --out RUN.sh [--flat 40 --klat 40 --vlat 6]
    python3 tools/hgi_e2e/run.py report RUN_DIR [--out REC.json]  -> per-record / per-unit cycles vs the simulator, verdict

Unit codes (spec 2.3): CTL 0, SM 1, SU 2, SFU 3, FUSED 4, ATT 5, COLL 6, ARGMAX 7, DMA 8, IDX 9, HC 10.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

UNITS = ["CTL", "SM", "SU", "SFU", "FUSED", "ATT", "COLL", "ARGMAX", "DMA", "IDX", "HC", "SIMT"]
OPND = ["A", "B", "C", "D", "O", "R", "I"]
END_TOKEN_VM = 0x3FFF0

# RTL source list of the harness (main paths); a REAL unit adds its own
SRC_BASE = [
    "rtl/hbm_accel/generic/ot_hgi_cfg.sv", "rtl/hbm_accel/generic/ot_hgi_seq.sv", "rtl/hbm_accel/generic/ot_hgi_cp.sv",
    "rtl/hbm_accel/generic/ot_hgi_cp_die.sv", "rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv",
]
SRC_REAL = {
    "dma": ["rtl/hbm_accel/generic/adapters/ot_hgi_dma_record.sv", "rtl/hbm_accel/generic/peers/ot_hgi_dma_mover.sv"],
    "quant": ["rtl/hbm_accel/generic/ot_hgi_quant_unit.sv", "rtl/hbm_accel/generic/ot_hgi_quant_record.sv",
              "rtl/hbm_accel/generic/ot_hgi_quant_vm_transport.sv", "rtl/hbm_accel/generic/ot_hgi_quant_decode.sv",
              "rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv"],
    "idx": ["rtl/hbm_accel/generic/idx/ot_hgi_idx_unit.sv", "rtl/hbm_accel/generic/idx/ot_hgi_idx_merge.sv",
            "rtl/hbm_accel/generic/idx/ot_hgi_idx_index.sv"],
}
VEC = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
       "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fastfp_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
       "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv", "rtl/hdc/v41/ot_hdc_fdiv.sv",
       "rtl/hdc/v41/ot_hdc_softplus.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv", "rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv", "rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv", "rtl/hdc/v41x/ot_hdc_v41x_vec.sv"]
SRC_REAL["su"] = VEC + ["rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv"]
SRC_REAL["sfu"] = VEC + ["rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv", "rtl/hbm_accel/generic/adapters/ot_hgi_sfu_record.sv"]
SRC_REAL["coll"] = ["rtl/hbm_accel/generic/collective/ot_hgi_coll_ep.sv", "rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv",
                    "rtl/hbm_accel/generic/collective/ot_hgi_coll_record.sv", "rtl/hbm_accel/generic/collective/ot_hgi_coll_decode.sv",
                    "rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv", "rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv",
                    "rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv",
                    "rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv", "rtl/hbm_accel/tu/ot_hcoll_port.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
                    "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv"]
TB = ["rtl/hbm_accel/generic/e2e/tb_hgi_e2e.sv", "rtl/hbm_accel/generic/e2e/hgi_e2e_slots.sv",
      "rtl/hbm_accel/generic/e2e/hgi_e2e_dpi.cpp"]


def prep(d: Path):
    from hgi_sim.records import Rec, MDesc, decode_program, encode_program
    meta = json.loads((d / "meta.json").read_text())
    image = (d / "image.bin").read_bytes()
    recs = decode_program(image)
    skip = []
    vm_final = memoryview((d / "vm_final.bin").read_bytes()).cast("I")
    if meta.get("needs_end"):
        end = Rec("CTL", "END", wait=0xFFFE, desc=dict(A=MDesc(space="VM", fmt="U32", base=END_TOKEN_VM, n=1)))
        image = image + end.encode()
        exp_tok = 1234
        skip.append((END_TOKEN_VM, exp_tok))
    else:
        e = recs[-1]
        assert e.unit == "CTL" and e.op == "END", "the layer program must end with CTL.END"
        exp_tok = int(vm_final[e.desc["A"].base])
    (d / "image_e2e.bin").write_bytes(image)
    md = list(meta["md_words"])
    lines = []
    for r in meta["records"]:
        h = int(r["hdr"], 16)
        hw = [(h >> (32 * i)) & 0xFFFFFFFF for i in (3, 2, 1, 0)]
        ops = []
        for nm in OPND:
            e = r["eff"].get(nm)
            ops.append(f"1 {e[0] & ((1 << 40) - 1):x} {e[1] & ((1 << 21) - 1)}" if e else "0 0 0")
        u = UNITS.index(r["unit"])
        from hgi_sim.records import OPS
        op = OPS[r["unit"]].index(r["op"])
        tag = re.sub(r"[^A-Za-z0-9_.+:-]", "_", r["tag"] or "-")[:120]
        lines.append(f"{r['k']} {u} {op} " + " ".join(f"{x:08x}" for x in hw) + " " + " ".join(ops) +
                     f" {r.get('cost', 1)} {r['vm_off']} {r['vm_n']} {r['hbm_off']} {r['hbm_n']} "
                     f"{r.get('s2_disp', 0)} {r.get('s2_start', 0)} {r.get('s2_end', 0)} {tag}")
    (d / "recs.txt").write_text("\n".join(lines) + "\n")
    (d / "prep.txt").write_text(f"{meta['image_base_bytes']} image_e2e.bin\n{len(skip)}\n" +
                                "".join(f"{a} {v}\n" for a, v in skip))
    dyn = meta["dyn"]
    host = md + [dyn[3], dyn[1], exp_tok, meta["rank"], 1] + [0] * 11
    (d / "host.mem").write_text("\n".join(f"{x & 0xFFFFFFFF:08x}" for x in host) + "\n")
    print(f"prep {d}: {len(lines)} records, image {len(image)} B, expected token {exp_tok}")


def script(a):
    real = [x for x in a.real.split(",") if x]
    src = list(dict.fromkeys(SRC_BASE + sum((SRC_REAL[x] for x in real), [])))
    gp = " ".join(f"-G{'REAL_' + x.upper()}=1" for x in real) + "".join(f" -G{g}" for g in a.g if not g.startswith("E2E_DBG"))
    gp += (" +define+E2E_COLL_DEBUG" if any(g.startswith("E2E_DBG") for g in a.g) else "")
    gp += (" +define+E2E_VEC" if {"su", "sfu"} & set(real) else "") + (" +define+E2E_COLL" if "coll" in real else "")
    tag = ("_".join(sorted(real)) or "stubs") + "".join("_" + g.replace("=", "") for g in a.g)
    return f"""#!/bin/bash
# hgi-e2e run: vehicle {a.vehicle}, real units [{', '.join(real) or 'none'}]; FLAT {a.flat} KLAT {a.klat} VLAT {a.vlat}
set -e
S=${{SRC:-src}}; V=${{VEC:-vec}}/{a.vehicle}; O=${{OUT:-out}}/{a.vehicle}_{tag}_f{a.flat}k{a.klat}
mkdir -p $O
VER=${{VERILATOR:-verilator}}
$VER --binary -j 16 --top-module tb_hgi_e2e -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-BLKSEQ --timing -O2 \\
  {gp} -GFLAT={a.flat} -GKLAT={a.klat} -GVLAT={a.vlat} \\
  -I$S/rtl/hbm_accel/generic -I$S/rtl/hbm_accel/generic/tb \\
  {' '.join('$S/' + s for s in src)} \\
  {' '.join('$S/' + t for t in TB)} --Mdir $O/obj -o tb > $O/build.log 2>&1
set +e
$O/obj/tb +DIR=$V +OUT=$O/e2e_records.txt > $O/run.log 2>&1; rc=$?
echo "rc=$rc" >> $O/run.log
"""


def report(run: Path, vec: Path | None):
    log = (run / "run.log").read_text(errors="replace")
    rows = []
    summ = {}
    for line in (run / "e2e_records.txt").read_text().splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("SUMMARY"):
            t = line.split()[1:]
            summ = {t[i]: (int(t[i + 1]) if re.fullmatch(r"-?\d+", t[i + 1]) else t[i + 1]) for i in range(0, len(t) - 1, 2)
                    if not t[i].startswith("dispatched")}
            m = re.search(r"dispatched (\d+)/(\d+)", line)
            summ["dispatched"], summ["golden_records"] = int(m.group(1)), int(m.group(2))
            continue
        f = line.split()
        rows.append(dict(k=int(f[0]), unit=UNITS[int(f[1])], op=int(f[2]), tag=f[3], real=int(f[4]), disp=int(f[5]),
                         ret=int(f[6]), cost=float(f[7]), s2_disp=float(f[8]), s2_start=float(f[9]), s2_end=float(f[10]),
                         dispatch_mismatch=int(f[11], 16), vm_checked=int(f[12]), mismatch=int(f[13]), stray=int(f[14])))
    per_unit = defaultdict(lambda: dict(records=0, real=0, exact=0, rtl_busy=0, sim_cost=0.0))
    for r in rows:
        p = per_unit[r["unit"]]
        p["records"] += 1
        p["real"] += r["real"]
        p["exact"] += int(r["real"] and r["mismatch"] == 0 and r["stray"] == 0)
        if r["ret"] >= 0 and r["disp"] >= 0:
            p["rtl_busy"] += r["ret"] - r["disp"]
        p["sim_cost"] += r["cost"]
    t0 = min((r["disp"] for r in rows if r["disp"] >= 0), default=0)
    out = dict(pass_="HGI_E2E PASS" in log, summary=summ,
               cfg=re.search(r"E2E CFG status err (\d+) loaded (\d+)", log).groups() if "E2E CFG" in log else None,
               completion=re.search(r"E2E completion token (-?\d+) \(golden (\d+)\) status (\d+) cp_cycles (\d+) "
                                    r"doorbell->completion (-?\d+)", log).groups() if "E2E completion" in log else None,
               per_unit={k: dict(v, sim_cost=round(v["sim_cost"], 1)) for k, v in per_unit.items()},
               records=rows, first_dispatch_cycle=t0,
               rtl_lines=[x for x in log.splitlines() if x.startswith("E2E") or "HGI_E2E" in x][:200])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prep"); p.add_argument("dir", type=Path)
    s = sp.add_parser("script")
    s.add_argument("--vehicle", required=True); s.add_argument("--real", default="")
    s.add_argument("--flat", type=int, default=40); s.add_argument("--klat", type=int, default=40)
    s.add_argument("--vlat", type=int, default=6); s.add_argument("--out", type=Path, required=True)
    s.add_argument("--g", action="append", default=[], help="extra tb parameter KEY=VAL")
    r = sp.add_parser("report"); r.add_argument("run", type=Path); r.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.cmd == "prep":
        prep(a.dir)
    elif a.cmd == "script":
        a.out.write_text(script(a))
        a.out.chmod(0o755)
    else:
        res = report(a.run, None)
        txt = json.dumps(res, indent=1, default=int) + "\n"
        if a.out:
            a.out.write_text(txt)
        print(json.dumps({k: v for k, v in res.items() if k not in ("records", "rtl_lines")}, indent=1, default=int))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
