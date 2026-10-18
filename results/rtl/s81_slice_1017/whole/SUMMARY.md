# S81-TILES6 XS: whole-slice elaboration and bench (2026-10-17/18, branch claude/s81sl-whole-1017)

Source: claude/s81sl-xs-1017 (1dcaa1b20) merged with origin/main (whose slice/ tree equals claude/s81vq-ring-1017) and
commit 0b0d2caa3.

- Mismatches:
  - The xs ROMs carry `#(.INSTANCE(..))`, but the kit/synthesis ROM black box `ot_rom_4096x72_m8_bb.v` has no INSTANCE
    parameter. 1dcaa1b20 handles this with a SYNTHESIS guard (`OT_S81SL_XS_ROM`).
  - The slice left the `sid` strap port of `ot_s81dv_xfin` unbound (PINMISSING). 0b0d2caa3 binds `.sid(sid)`.
- Whole-slice lint, sim view (full ROM model), `tools/s81_slice/slice_lint.sh lint 0`: verilator rc 0. The only pin
  warnings in the slice are xs_ctl's two open `ot_v41_inc` carry outputs (co). `lint_hb0_slice_sim.log` (run before the
  co filter, which is why that run printed "FAIL").
- Kit view, `TOP=ot_s81sl_xg S81SL_LINT_SYN=1` (+SYNTHESIS, bb ROM): PASS. `lint_xg_kitview.log`.
- Whole-slice bench `tools/s81_slice/slice_bench.sh` (tb_s81sl_slice):
  - inputs: leaf-bench SU cases, entered at the slice pins as CTL beats on ri_w;
  - checks: RDOUT send beats on ro_e and XQ beats on ro_w; the slice fault pin must stay 0.
  - runs on ot-pve1 /home/ubuntu/s81sl_whole_1017b/sb/m{0,1,2}_L0 (PENDING at write time; verdicts appended below).
