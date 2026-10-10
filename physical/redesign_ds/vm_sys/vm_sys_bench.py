#!/usr/bin/env python3
"""redesign-ds 2026-10-09: exact lockstep gate of the SYSTOLIC VM tile (rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv),
NS bit-sliced chains of 4 tiles (dsfd_vm_mem_sys), against the committed behavioural-array bench
rtl/dsrom_sys/s81_ph/test/tb_ot_s81ph_vm_mem.sv (patched in a work dir: DUT = dsfd_vm_mem_sys, L = 4*NSTG + QD + 8).
    vm_sys_bench.py OUTDIR TAG NSTG NS [DEFINE ...] [-- +PLUSARGS]      exit 0 iff PASS (PASS_OVF with +OVF)
Mutants: OT_S81PH_VM_MUT_ORDER / _MASK / _J0 (bank queue order, write mask, due-slot index), OT_VM_SYS_MUT_SKEW
(forward bus one stage short: request / return lockstep broken)."""
import pathlib, subprocess, sys
out, tag, nstg, ns = pathlib.Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
rest = sys.argv[5:]
defs = rest[:rest.index("--")] if "--" in rest else rest
plus = rest[rest.index("--") + 1:] if "--" in rest else []
out.mkdir(parents=True, exist_ok=True)
tb = pathlib.Path("rtl/dsrom_sys/s81_ph/test/tb_ot_s81ph_vm_mem.sv").read_text()
R = [("`ifdef TILED\n    // CLAUDE S81-PH vm v2",
      "`ifdef TILED_SYS\n    localparam integer BB = $clog2(NB), RA = BB + 9, L = 4 * `NSTG + QD + 8, NR = NB * 512;\n`elsif TILED\n    // CLAUDE S81-PH vm v2"),
     ("`ifdef TILED_HALF\n",
      "`ifdef TILED_SYS\n    wire slice_mismatch;\n    always @(posedge clk) if (rst_n && slice_mismatch) begin $display(\"FAIL slice mismatch\"); $finish; end\n"
      "    dsfd_vm_mem_sys #(.NS(`NSLICE), .NP(NP), .NB(NB), .QD(QD), .RQ(RQ), .NSTG(`NSTG)) dut (.clk(clk), .rst_n(rst_n), .slice_mismatch(slice_mismatch), .i_v(i_v), .i_we(i_we),\n"
      "`elsif TILED_HALF\n")]
for a, b in R:
    assert tb.count(a) == 1, a
    tb = tb.replace(a, b)
(out / "tb.sv").write_text(tb)
cmd = ["verilator", "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-j", "8",
       "--top-module", "tb_ot_s81ph_vm_mem", "+define+TILED_SYS", f"+define+NSTG={nstg}", f"+define+NSLICE={ns}",
       *[f"+define+{d}" for d in defs], "--Mdir", str(out / f"obj_{tag}"), str(out / "tb.sv"),
       "rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv",
       "physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"]
b = subprocess.run(cmd, capture_output=True, text=True)
(out / f"build_{tag}.log").write_text(b.stdout + b.stderr)
if b.returncode:
    print("BUILD_FAIL"); print("\n".join([l for l in (b.stdout + b.stderr).splitlines() if "rror" in l][:15])); sys.exit(2)
r = subprocess.run([str(out / f"obj_{tag}" / "Vtb_ot_s81ph_vm_mem"), *plus], capture_output=True, text=True)
log = r.stdout + r.stderr
(out / f"run_{tag}.log").write_text(log)
res = [l for l in log.splitlines() if l.startswith(("RESULT", "OVF", "PASS", "FAIL", "MISMATCH"))]
print("\n".join(res[-4:]))
ok = any(l.strip() in ("PASS",) or "PASS_OVF" in l for l in res)
print(f"VM_SYS_{tag}: {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
