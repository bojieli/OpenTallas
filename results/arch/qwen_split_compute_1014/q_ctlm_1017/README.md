# Lane Q-CTLM (Qwen compute die dv2f7): tt_ctlm + sys_face DV re-port, 10-17

Branch `claude/qctlm-1017` (from `claude/qslice-1017` be28f313b), worktree `/home/ubuntu/wt/qctlm-1017`.

## What was built
- `rtl/qwen_dv/qfd_tt_ctlm_dv.sv`: the new master for die instance `tt_ctlm`. It replaces `qfd_tt_ctlm_b2`, which is kept as historical pre-DV.
  - Kept, unchanged RTL: the ME head (`qfd_tt_ctlm_head_static`), native_cmd_route, rom_relocate (ib 380), the XPF loader and static schedule.
  - Removed: the tree controller and the train source.
  - The four clocks are now one `ck` (one regional root).
  - Every new input has a pin register (dh, ss5, ag5, fab). hr, cmd, dc and emb are registers.
- `rtl/qwen_dv/qfd_dv_cmd_cal.sv`: the static slice-command calendar. The format is in its header. In short:
  - It is the 2nd program copy: the full PW image goes into 2x `ot_sram_1r1w_64x512` plus the observer, and it is sink 1 of the record port, replacing the seq_su copy.
  - DW0..7 is the descriptor: base, nent and 4 segments. Segments: s0 = stage 0, s1 = layers, s2 = stage 37, s3 = BOOT, which plays once on the seal.
  - Each entry is 128 b: `{delta 12, cmd 116}`. Entry k is issued at edge S + sum(delta). The first entry needs T >= 4.
  - Kinds:
    - dst 14 is LOCAL: kind 1 EMB is emb_start, kind 2 SEG is an ME segment start with its base.
    - go = 0 is a NOP.
    - Everything else is forwarded on `cmd`.
  - It has no readiness input. A late entry or a bad image FAULTS.
- Token / position source (G9): `dh` = sys_face `seq_dh`, the levels seq_su used to take.
  - The stage h_start goes to the ME start (base 0, +1 edge, as the seq_su stage gate did) and also starts the calendar segment.
  - token / pos come from `dh`.
  - emb_token is the stage-0 token.
- `rtl/qwen_split/qfd_sys_face.sv` (G8):
  - `crom_fault_code` is DROPPED: the qfd_crom_g groups are gone. The CROM is in the slice VM, and its fault arrives as seq_dc[55] = ag5 vm.
  - `res_issue_fault` is DROPPED: its producer, the res trains, is gone.
  - The seq_* ports keep their names; their producer is now tt_ctlm. Everything else is byte-identical.

## Final port lists
**qfd_tt_ctlm_dv: 445 in + 1,291 out = 1,736 bits** (b2 had ~4,594; -62%).

| port | dir | bits | peer |
|---|---|---:|---|
| ck, rst_n | in | 1+1 | regional clock / reset |
| pw | in | 75 | sys_face.tt_pw |
| dh | in | 187 | sys_face.seq_dh |
| kok, kwd, fab | in | 1 each | sys_face.tt_kok / tt_kwd / tt_fab |
| native_ret | in | 95 | native59.native_ret |
| ss5 | in | 74 | dvs_W5.ss_wo |
| ag5 | in | 9 | dvs_W5.ag_wo |
| hr | out | 453 | dvs_W5.hr_wi `{ib 380, xpf 72, v}` |
| cmd | out | 116 | dvs_W5.cmd_wi |
| emb_start / emb_token | out | 1 / 18 | embed_prov.core_start / core_token |
| native_cmd | out | 380 | native59.native_cmd |
| native_tok, native_pos | out | 18 each | sys_face.tt_native_tok/pos + native59.native_token/position |
| command_stage | out | 6 | sys_face.tt_command_stage + native59.command_stage |
| layer_context_v | out | 1 | sys_face.tt_layer_context_v |
| program_obs / control_stores_ready | out | 76 / 1 | sys_face.tt_program_obs / tt_control_stores_ready |
| cal_program_obs / cal_descriptor_obs / cal_image_ready | out | 76 / 69 / 1 | sys_face.seq_program_obs / seq_descriptor_obs / seq_cfg_image_ready |
| dc | out | 56 | sys_face.seq_dc `{ag vm, !su_busy, xc_busy, core_fault, s_fault, s_done, ntok 18, nval 32}` |
| cf | out | 1 | fault observation (also in dc[52]) |

Pins per face:
- W5 face: 652 b.
- sys_face face: 588 b.
- native59: 475 b.
- embed: 19 b.

**qfd_sys_face**: the previous port list minus `crom_fault_code[15:0]` and `res_issue_fault` (−17 inputs).

**Re-shape (die plan):**
- The old slot is 777.6 x 1814.4 (2.3:1) and was sized for the 4.6k-pin tree controller.
- The new tile holds:
  - 4x 64x512 SRAM (2 ME program, 2 calendar);
  - the ME head;
  - XPF;
  - an 8 x 128 b FIFO.
- It has 1.7k pins. Its largest face is W5 at 652 pins, which is 109 um at 6/um.
- Proposed slot: square-ish, start at 777.6 x 777.6 (18 x 43.2 lattice). Confirm against the synthesis area at the first gate.

## Benches (Verilator; `rtl/test/qwen_dv/run_tt_ctlm_dv.sh`)
- **ABI** (`tb_qfd_tt_ctlm_dv_abi.sv`, 256 random vectors): MUT0 PASS. MUT4 (prog/rows swap) and MUT5 (dc rom_fault source) FAIL.
  - Covered: the ss5/ag5 → head x_o* map, dc, and the dh → ME start face.
  - The hr check is structural only: ib and xpf stay 0 without an ME program.
- **Calendar** (`tt_ctlm_cal_bench.py` + `tb_qfd_tt_ctlm_cal.sv`):
  - Coverage: 4 segments, 60 events matched exactly against the Python model. Includes back-to-back deltas, a 4095 NOP, EMB/SEG locals and XC.
  - The record-port sink (`qkd_program_commit`) COMMITS the calendar copy with the AUTH digest.
  - dc s_done/ntok fires +2 edges after ss5 tok_v.
  - MUT0 PASS 62/62. MUT1 (one edge late), MUT2 (entry halves swapped) and MUT3 (no BOOT) FAIL.
- **SETID x12** (`--nsl 12`, 12 real `qfd_dv_slice2` on cmd/hr): verilator_bin needed >84 GB locally, so I killed it. NSL2 result: see the log below. The x12 run needs a fleet host with ≥100 GB.
- **sys_face** (`rtl/test/qwen_split/run_sys_face_bench.sh`, adapted): MUT0 PASS (1512 events exact). MUT1-4 FAIL.

## Contract gaps (exact changes needed; slice RTL not edited)
- **G9b, value**: ss carries no merged argmax value, so dc nval reads 0 and sys_face result_value = 0.
  - Change: ss 74 → 106 with `tok_val[31:0]` beside tok_idx, set from the merged okey value on the same edge as tok_v.
- **G10**: ag/ss carry no ME/station busy. The head's ME ready/idle check has no DV producer: rom_ret = ready 1, idle 1, and fault = ag5 stn.
  - Change: ag 9 → 10 with `stn_busy` (OR of the station windows open). tt_ctlm then drives me_idle = !stn_busy.
- **coll_busy**: this is set on an XC issue and cleared on a rise of ss5 ar_last. A single-beat AR whose ar_last stays 1 never clears it.
  - Change: add an `ar_v` pulse to ss, or a coll_busy bit to ag.
- **dst 14 is reserved** for tt_ctlm-local calendar entries. Slices must never be enumerated to id 14; with 12 slices, ids 0..11 are fine.
- **README text**: the slice README says hr = `{go, ib 379, xpf 72, hr_v}`, but the slice RTL uses `[452:73]` = ib 380 and `[72:1]` = xpf. tt_ctlm follows the RTL and the brief.
- **ME image**: the calendar bench does not install a valid ME image (dc core_fault rises). ME head behaviour is the unchanged b2 RTL; an end-to-end ME + calendar program is next for the first layer vehicle.
- **Die flow**: `tools/qwen_split/sys_face_bind.py` is the pre-DV binder and was not edited. dv_case.py must bind the table above.

## Log
