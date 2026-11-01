# DIE-QC-55 PROG (qfd_dv_s8x_prog) rebuild after the routed-DB loss (COORD 15:5x, 2026-10-31)

The signed DIE-QC-35 ffh10r DB (intel2 die-qc-34-kits/prog/kit_ffh10r) and every input dir it came from were deleted on
10-31 between 13:09 and 15:08. No copy exists on intel1, intel2 or epyc2 (CHECKED). The only surviving source is the autopilot
archive intel2 `autopilot/closed/qwen_compute/qfd_dv_s8x_prog__s8b__6aa7f1fc4d`. Its 5_2_route.odb is the
Codex native-move input before the move. Its pins equal the plan_qc52 `cores/su/signed/qfd_dv_s8x_prog_pins.json` (ce7d776a) pin for pin.
The outline is 259.2x354.24, and the SRAM master is asap7_memory_macros_v2 (CHECKED).

Kit (intel2 `/srv/opentallas-scratch2/claude/die-qc-55/prog/kit_base`):
- the archive kit records (config.mk, constraint.sdc, sdc_lint/face_guard/pins/freeze);
- main v2 SRAM views;
- RTL 66b68bff2 qfd_dv_s5_vm8x.sv (6680b721) + the 3 SRAM _bb.v (d5e85b37/9352069d/35e0905c);
- cf/rc_cal.tcl (288424b1);
- tools exported from flow-20261031-h-qc.

## V2 = the lost recipe (counted variant)
1. `v2/prog_mover.py`: re-creates the Codex native pin-reach move with existing flops only (no RTL, pin, outline or cycle change):
   - each pin's registering flop goes into a 26-um Manhattan lens;
   - r2r pairs are pulled to <= 392 um;
   - then DPL runs (`v2/apply.tcl`; max displacement 3 um, check_placement clean). 591 flops moved.

   AUTO-GEOM (main geom_rules --all-kits) changes as follows. Every other rule is unchanged from the GEOM-58 PASS-COND state; the renders v2/native_a.png and src.png were VIEWED.

   | Rule | Before (source) | After |
   |---|---|---|
   | pin_reg p90 | 32.74 | 26.21 |
   | pin_reg max | 42.47 | 28.47 |
   | r2r (max / count > 405) | 446.36 / 89 | 393.34 / 0 |
2. cand-2 prep (`results/qc_die34_1029/prog/prep_prog.tcl`): PG hook, 0 open of 59,604, strip 23,932 nets. The census is identical to 10-29.
3. ffh10 route with the two-mode measured FF hold repair (margin 10, SLEW_MARGIN 40, vclk 496.03/381.14):
   - GRT stage: TT +346.81, FF +9.45;
   - routed: TT +355.0, FF hold -3.18 / 4 endpoints (as on 10-29, -4.12 / 7).
4. ffh10r: FF-only post-route hold ECO from the routed 5_2_route.odb + its 6_final.spef:
   - 160 hold buffers;
   - clock wires FIXED, freeze assert OK;
   - DRT 0 violations.
5. signoff.py (h-qc) **SIGNED**:
   - TT +354.99, FF hold +7.25;
   - pair TT/FF 85.2/76.4 (info);
   - DRC 0, antenna 0.

   LEC **EQUIVALENT** 7221/7221. `resign.py` wrote the PROVENANCE kind:resign (`rs_v2r/`).

   Routed DB: intel2 `die-qc-55/prog/kit_v2r/run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base/6_final.odb`, sha256 66fba745...

## V1 = fast variant (fallback only)
The archived s8b 6_final got the protected-instance PG hook (`pg_v1.tcl`: 108 insts / 216 terms -> 0 open of 408,482) and the ffh10 vclk binding repair.
- Result: SIGNED. TT +334.72, FF hold +4.45, pair 51.0/48.2, DRC 0. LEC EQUIVALENT. Record in `rs_v1/`.
- Caveat: this is the old geometry (AUTO-GEOM pin_reg p90 32.74, r2r 446.36 / 89 > 405).
