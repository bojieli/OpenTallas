# hnx_idxq_link: IDXQ selector merge + IDXN row-slot link (NOT submittable; structural redesign owed)

Top `ot_hnx_idxq_link`. It is a 4-selector OR merge plus `ot_hnx_idxn_link`, which is a copy-fork of the historical d4g `ot_hbm_idx_topk_link_static` with 8 row slots.

## Gate history
- **gate 1** (05:10): synth cap.
- **gate 3** (10-19 06:19, `--synth-cap 0`, 72 GB, ot-epyc6): synthesis finished. It then FAILED at floorplan: `OT_DIRECT_MACRO: instance ownership is not unique: link.core.gm[0].mem`. This is mechanical: the netlist names are `u_ot_pr_core.link.core.gm[k].mem`, so the spec `inst` patterns need a leading `*`.

## SAFE-DESIGN checklist (owner 10-19): FAILS -> structural redesign, no regate of this form

| # | item | result |
|---|---|---|
| 1 | pins | PASS: the IDXN shell registers every data pin. **FAIL**: the 4-selector OR merge + collision sits in front of the input flops (logic behind pins). |
| 2 | reach | unknown (no placement). The outline is 388.8 x 820.8. |
| 3 | fanout | **FAIL**: `ingest_v` and `total[5:0]` fan into the whole 4,608-b pack (~7k loads). This is the d4g r1 finding. |
| 4 | depth | **FAIL**: a 64-record runtime-offset pack into the carry, plus up to 8 flits written at runtime banks, all in ONE edge. That is a 42-level chain plus 4,096-b `wd[bank*512+:512]` and `packed_next[n*64+:64]` runtime part-selects (SHARE stall). The d4g sibling with the same core never closed: hidx_link_pr; hidx_link_g4p r1 TT -78.45. |
| 5 | storage | PASS: 8 real 64x512 SRAMs. Row slots use the spare rows. |
| 6 | floorplan | macros at (108, 69.12 / 146.928 ...) are not on the 43.2 lattice (x 108 = 2.5 x 43.2). |
| 7 | clock | 8 `clk_mem` macro entries; not measured. |
| 8 | schedule | PASS: static, collisions fault. |

## Redesign (next agent)
1. Port the pipelined d4g successor `ot_hbm_idx_topk_link_static_p` into the row-slot core. It is on `origin/claude/hbm-topklink-1019`: r3 e90cf529c, route TT -0.62 / FF -47.62. The port covers:
   - S1 group compaction from kept lane-valid copies;
   - S2/S3 register-select merges;
   - the S4 loop with 16 `total` region copies;
   - S5 ring-W write formation;
   - outputs at the historical timeline +5.
2. Row-slot additions: write address `{wslot, fr[5:3]}`, read address `{emit_slot, grp[3:1]}`. `row_clear` / `in_slot` / `emit_slot` are delayed to the S4 tap (+3) for the slot state and faults, and to the +5 tap for reads.
3. Register the 4 selector inputs at the pins (+1). The OR merge + collision check goes into S1.
4. Calendar: port `--link-pipe 5` (d4g compiler on the topklink branch) into `hnx_idxn_calendar.py`. Then set the tb DTX/DD offsets and rerun the quad lockstep.
5. Kit `hnx_idxq_link2`:
   - macros on the 43.2 lattice;
   - `inst` patterns `*link.core.gm[k].mem`;
   - one std band;
   - one clock root (the `_p` form drives the SRAMs from `clk`).
