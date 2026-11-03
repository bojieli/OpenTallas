# T7 attention staging SRAM_MACRO=1: native gate PASS, UNAPPLIED bound flip (TOK-DS-4)

**Why.** T7 canary2 (`svc_lo_dsdv_svc_rs__t7` GEN/LINT on the current 141-source export, intel1 unit oth-ubuntu-80731-1793597049) fails only `memory_bits`, with 9 items. Five already have their own cut or declaration: LAND 4c805 (`s81_T7_LAND_bound_cut_1102`), PMEM 193c (`s81_T7_pmem_bound_cut_0900`), PVQ 9c281 (`s81_T7_pvq_bound_cut_1040`), the exp table (elab_width 64) and the u_att.sw FIFO (DECLARED_FLOP_MEMORIES). The other four are `ot_hdc_v41x_attn_staging` `g_behavioural.g_lane[0..3].mem`, each 160 x 265 = 42400 bits. In the T7 bound the two staging instances `u_u_rsv_14_u_u_att_u_eng_g_stage2_u_stage{0,1}` are bound with `.SRAM_MACRO(1'b0)`.

**What.** `ot_hdc_v41x_attn_staging` (unchanged, sha 642772e3) already has a physical option, `SRAM_MACRO=1`. It stripes each lane across 256-bit 1R1W macros, and its header says both forms "return the old row one cycle after rd_addr is sampled". At the T7 parameters (D=32, NL=4, TROWS=640: DEPTH 160, ROWW 265, NB 2) that is 2 x `ot_sram_1r1w_256x256_m2_r2c2` per lane, so 8 per instance and 16 for T7.

**Gate** (`run.sh`; Verilator 5.050, two-state zero start, 833 ps):
- Setup: the unchanged module with SRAM_MACRO=0 and with SRAM_MACRO=1, both instantiated on the same stimulus. The macro sim view is the aligned-v2 model (dc4463c0, read-before-write).
- Seeding: all 160 rows of all lanes written.
- Traffic: 4096 random edges. 3843 have writes, 989 are same-edge read/write collisions and 379 are out-of-range writes.
- Compare: all 1060 rd_data bits on every edge whose sampled rd_addr < 160 (3698 compares). Behavioural rows >= 160 do not exist, so their read is undefined. The 398 out-of-range reads are skipped; the macro form is a refinement there.
- Result: PASS, intel2 ot-run unit oth-ubuntu-254689-1793688980, exit 0.

**Controls.** `make_mutants.py` makes renamed copies of the unchanged module with one macro-path fault each. All four are caught:
- every slice written with slice 0's data: edge 0;
- lane write-enable rotated: edge 10;
- read address off by one: edge 0;
- write-first bypass: edge 6.

**Bound flip** (`stage_flip.py --parent <bound> --out <new>`, UNAPPLIED):
- Accepts only three hashes: the original T7 bound 61c902f1, LAND-only b30a4283 and PMEM+PVQ+LAND joint 43dc924c.
- Changes exactly the two staging instance lines from `1'b0` to `1'b1`, and asserts there are exactly 2 staging lines with the expected text.
- Results: joint 43dc924c becomes 12605dc2, the full T7 memory closure bound (`flip_joint.json`); original 61c902f1 becomes 76a0b55b (`flip_original.json`).
- An unapproved hash is refused (extra byte, or already flipped).

**Cost:** -84800 behavioural bits per instance, 169600 for T7. Plus +16 256x256 macros (172.824 x 41.064 um each, 113551 um2 total) and +16 macro clock pins. 0 FF, 0 reset loads, 0 cycles. The macros use 160/256 rows and 265/512 bits, which is the existing module's packing.

**Held:**
- Not applied to a manifest, kit or recipe.
- Physical: the T7 plan must place 16 + 12 + 4 + 34 new macros. Fit, macro clock and 833 ps timing are not qualified.
- 2-state zero-start only.

**Yosys elaboration** (`yosys_stat.txt`, ORFS asap7lock image): the unchanged module with `chparam SRAM_MACRO=1 D=32 NL=4 TROWS=640` plus the 256x256 `_bb.v` gives `hierarchy; proc; memory -nomap; stat` = 8 cells, all `ot_sram_1r1w_256x256_m2_r2c2`, and 0 memories. The `{{(8-AW){1'b0}}, ...}` zero-width pad (AW=8) is accepted.

**T7 memory closure set** (one opt-in application, for the S81 plan/kit owner):
- `T7_memory_closure_bound.sv.gz` (sha 12605dc2) replaces `s81p_svc_lo_dsdv_svc_rs__t7_bound.sv`. It is built from the original 61c902f1 in three steps: the PMEM cut (s81_T7_pmem_bound_cut_0900), then the PVQ cut (s81_T7_pvq_bound_cut_1040), then LAND (s81_T7_LAND_bound_cut_1102), followed by `stage_flip.py`.
- Add three children right after the bound in kit_rtl.f / kit_rtl_sim.f / kit_rtl.json `files`: `ot_t7_pmem_capture_candidate.sv` 3d7ab5aa, `ot_t7_pvq_capture_candidate.sv` 80367218 and `ot_t7_land_capture_candidate.sv` 64e23cf3.
- Use gen_phys with the claude/tok-ds-3-1102 DECLARED_FLOP_MEMORIES/elab_width entries.
- Macro delta for T7: +16 + 12 + 4 x 256x256 and +34 x 32x64. All of these macro types are already in the T7 kit_rtl.json `hard_macros`.
