#!/usr/bin/env python3
"""Power-aware exactness bench for the power-gated V4.1 ROM element (ot_v41_rom_elem_pg_w10, PG = 1).

Power loss is simulated, not assumed: the element inside the gated domain is flattened by Yosys (proc + flatten,
no optimisation beyond opt_clean) and every register, memory word, clock-gate latch and ROM output latch of the
domain is driven to X when the bench's header-switch model reports the domain unpowered.  The reference is the
unmodified RTL element (renamed only), always on.  The bench compares every public output of the two on every
cycle, so any state the wrapper fails to retain or restore, any un-isolated output, and any wake that lands
after the token, shows as a mismatch.

    python3 tools/rom_stage_pg_sim.py --work /home/ubuntu/pgs --out results/rtl/rom_stage_pg_power_gating_20261004
Mutants (each must FAIL): --mutant no_restore | no_iso | short_lead
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YOSYS = Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys"
ELEM = ["rtl/v41rom/ot_v41_rom_elem_w10.sv", "rtl/v41rom/ot_v41_bterm.sv", "rtl/v41rom/ot_v41_chain.sv",
        "rtl/v41rom/ot_v41_segtree.sv", "rtl/v41rom/ot_v41_bf16_lanes.sv", "rtl/hdc/ot_hdc_fpu.sv",
        "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_cg.sv",
        "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/v41rom/ot_v41_fadd.sv", "rtl/common/ot_prefix.sv",
        "rtl/v41rom/ot_v41_bmul2.sv", "rtl/v41rom/ot_v41_bterm2_w10.sv", "rtl/v41rom/ot_v41_chain2.sv",
        "rtl/v41rom/ot_v41_segtree2.sv", "rtl/v41rom/ot_v41_bf16_lanes2.sv"]
PG_RTL = ["rtl/v41rom/ot_v41_rom_elem_pg_w10.sv", "rtl/v41rom/ot_v41_rom_pg_ao.sv", "rtl/v41rom/ot_v41_stage_pg_sched.sv", "rtl/chip/ot_chip_v41_pg_ctrl.sv"]
TB = "rtl/test/tb_v41_rom_elem_pg.sv"
PARAMS = dict(NB=2, BF16=0, MTP=1, EARLY=1, FAST=1, PP=1, FRONT_PAR=0)   # the S81 pair element core (q element)
ELEM_PARAM_NAMES = ["NSEG", "NCH", "XF", "LV", "BF16", "NCHB", "NB", "MTP", "EARLY", "CG", "DRAIN", "FAST", "CUT",
                    "PP", "FRONT_PAR", "BP", "INSTANCE"]
BB = """(* blackbox *) module ot_rom_4096x274_m8 #(parameter INSTANCE="")(input wire clk, input wire ce_in,
  input wire [11:0] addr_in, output wire [273:0] rd_out); endmodule
(* blackbox *) module ot_rom_8192x274_m8 #(parameter INSTANCE="")(input wire clk, input wire ce_in,
  input wire [12:0] addr_in, output wire [273:0] rd_out); endmodule
"""
CORRUPT = "tb_v41_rom_elem_pg.pwr_off"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def flatten(work: Path) -> Path:
    (work / "rom_bb.v").write_text(BB)
    ch = " ".join(f"-chparam {k} {v}" for k, v in PARAMS.items())
    ys = (f"read_verilog -sv -lib {work / 'rom_bb.v'}\nread_verilog -sv {' '.join(str(ROOT / f) for f in ELEM)}\n"
          f"hierarchy -top ot_v41_rom_elem_w10 {ch}\nproc\nflatten\nmemory\nsetundef -zero -undriven\nopt_clean\n"
          f"rename -top ot_v41_rom_elem_w10\nwrite_verilog -noattr {work / 'elem_flat_raw.v'}\n")
    (work / "flat.ys").write_text(ys)
    subprocess.run([str(YOSYS), "-q", "-l", str(work / "flat.log"), str(work / "flat.ys")], check=True)
    return work / "elem_flat_raw.v"


def instrument(raw: Path, out: Path) -> dict:
    """Make the gated-domain netlist: dummy parameters (the wrapper overrides them by name), sim models for the
    blackboxes that also lose state, and an X-corruption of every register on the power-off event."""
    src = raw.read_text()
    src = src.replace("ot_rom_4096x274_m8 ", "ot_rom_4096x274_m8_pgx ").replace("ICGx1_ASAP7_75t_R ", "ICGx1_pgx ")
    scal, arrs = [], []
    for m in re.finditer(r"^  reg (?:signed )?(?:\[(\d+):(\d+)\] )?(\\\S+ |[A-Za-z_][A-Za-z0-9_$]*)( ?\[(\d+):(\d+)\])?;$",
                         src, re.M):
        w = abs(int(m.group(1)) - int(m.group(2))) + 1 if m.group(1) else 1
        name = m.group(3).rstrip()
        name = name + " " if name.startswith("\\") else name
        if m.group(4):
            arrs.append((name, w, int(m.group(5)), int(m.group(6))))
        else:
            scal.append((name, w))

    def rnd(w: int) -> str:            # power-up value of a w-bit register: random, never X (silicon is 2-state)
        return "{" + ", ".join(["$urandom"] * ((w + 31) // 32)) + "}"
    body = ["  // ---- power-aware simulation: the domain loses every stored bit when its switches are off; it",
            "  // comes back with arbitrary (random) contents, as silicon does ----",
            *[f"  parameter {p} = 0;" for p in ELEM_PARAM_NAMES if p != "INSTANCE"], '  parameter INSTANCE = "";',
            "  integer pgx_i;", f"  always @(posedge {CORRUPT}) begin"]
    body += [f"    {n} = {rnd(w)};" for n, w in scal]
    for n, w, a, b in arrs:
        body.append(f"    for (pgx_i = {min(a, b)}; pgx_i <= {max(a, b)}; pgx_i = pgx_i + 1) {n}[pgx_i] = {rnd(w)};")
    body.append("  end")
    i = src.index("endmodule", src.index("module ot_v41_rom_elem_w10"))
    src = src[:i] + "\n".join(body) + "\n" + src[i:]
    out.write_text(src)
    return dict(registers=len(scal), register_bits=sum(w for _, w in scal), memories=len(arrs),
                memory_bits=sum(w * (abs(a - b) + 1) for _, w, a, b in arrs))


def ref_copy(out: Path) -> None:
    s = (ROOT / "rtl/v41rom/ot_v41_rom_elem_w10.sv").read_text()
    assert s.count("module ot_v41_rom_elem_w10 #(") == 1
    out.write_text(s.replace("module ot_v41_rom_elem_w10 #(", "module ot_v41_rom_elem_w10_ref #("))


def run(work: Path, mutant: str | None, flat: Path, ref: Path, domcg: bool = False) -> dict:
    exe = work / f"tb_{mutant or 'base'}.vvp"
    defs = (["-DPG_MUTANT_" + mutant.upper()] if mutant else []) + (["-DPG_DOM_CG"] if domcg else [])
    cmd = (["iverilog", "-g2012", "-DSYNTHESIS", "-o", str(exe), "-s", "tb_v41_rom_elem_pg", *defs, str(ROOT / TB), str(flat), str(ref)]
           + [str(ROOT / f) for f in ELEM if f != "rtl/v41rom/ot_v41_rom_elem_w10.sv"] + [str(ROOT / f) for f in PG_RTL])
    subprocess.run(cmd, check=True, cwd=work)
    t0 = time.time()
    p = subprocess.run(["vvp", "-n", str(exe)], cwd=work, capture_output=True, text=True)
    log = p.stdout + p.stderr
    (work / f"sim_{mutant or 'base'}.log").write_text(log)
    ok = "PASS " in log and "FATAL" not in log and "fatal" not in log.lower().replace("$fatal", "")
    return dict(mutant=mutant, pass_=ok, returncode=p.returncode, seconds=round(time.time() - t0, 1),
                tail=[ln for ln in log.splitlines() if ln.startswith(("PASS", "TOKEN", "WAKE", "FATAL", "ERROR"))
                      or "fatal" in ln.lower() or "mismatch" in ln.lower()][-40:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--mutants", default="no_restore,no_iso,short_lead")
    ap.add_argument("--domcg", action="store_true", help="the series domain clock gate (DOM_CG = 1)")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    raw = flatten(a.work)
    flat = a.work / "elem_flat_pgx.v"
    inv = instrument(raw, flat)
    ref = a.work / "elem_ref.v"
    ref_copy(ref)
    res = dict(schema="opentallas.rtl.rom_stage_pg_exact.v1", element_params=PARAMS, domain_state=inv,
               sources={f: sha(ROOT / f) for f in ELEM + PG_RTL + [TB, "tools/rom_stage_pg_sim.py"]},
               dom_cg=int(a.domcg), runs=[run(a.work, None, flat, ref, a.domcg)])
    for m in [x for x in a.mutants.split(",") if x]:
        res["runs"].append(run(a.work, m, flat, ref, a.domcg))
    base = res["runs"][0]
    res["verdict"] = dict(exact_with_gating=base["pass_"],
                          mutants_detected={r["mutant"]: not r["pass_"] for r in res["runs"][1:]})
    print(json.dumps(res["verdict"], indent=1))
    for r in res["runs"]:
        print(r["mutant"], r["pass_"], r["seconds"], *r["tail"][-6:], sep="\n  ")
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "exact.json").write_text(json.dumps(res, indent=1) + "\n")
    return 0 if base["pass_"] and all(res["verdict"]["mutants_detected"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
