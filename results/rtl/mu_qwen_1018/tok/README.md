# MU.TOK.QW: the Qwen ROM 4-user token pass (bench spec, case generator, smoke)

Lane MU-ADOPT-TOK (sub-lane of MU-QWEN-ADOPT), 2026-10-19. Branch `claude/mu-adopt-tok-1019`, based on
`claude/mu-qwen-adopt-1019` 06fa3d55b.

The release gate is the token pass (owner 10-18). For 4 users it needs:
- per-layer RTL runs on the current dies, carrying the MU RTL;
- the compiler's static 4-user calendar;
- the compute <-> KV D2D link and the TP8 collectives;
- every user bit-exact against its golden;
- the latency user cycle-identical to the single-user pass;
- per-user and aggregate rates measured in real cycles.

This record is the harness. The real run waits on the blockers in section 4.

## 1. What runs today: the command-plane smoke (MEASURED, Verilator 5.050, fleet)

**DUT.** `rtl/test/mu_qwen_tok/tb_mu_tok_compose.sv` composes the three MU RTL blocks. Every start and the image come
from the generator (`tools/qwen_static_schedule/mu_tok_cases.py`).

| block | role |
|---|---|
| `qfd_dv_cmd_cal_mu` NU 4 (R1/R5) | 4 playheads, one shared image |
| `qfd_dv_amax_mu` NU 4 (R4) | fed by the issued STN / AMAX words |
| `qkd_kv_mu_wrow` / `qkd_kv_mu_rrow` (R6) | applied to every attention q record |

**Glue under test.** The adoption lanes must wire the same contract:
- STN `cmd[52:51]` and AMAX `cmd[9:8]` = `cmd_user`;
- the KV row user = the user of the issuing playhead, with the layer = that user's stage - 1.

**Station model.** The station is behavioural. It returns 16 result words a chunk, with logits = hash(user, token, row),
and has many exact ties on purpose.

**Run.**
- Command: `rtl/test/mu_qwen_tok/run_mu_tok_smoke.sh WORK` (fleet: `launch_mu_tok.sh smoke`).
- Run: ot-epyc5 unit oth-ubuntu-2854432-1792394564.
- Logs: `smoke/*.out`, `smoke/summary_0.json`.

| case | calendar | users | starts | events | argmax emits | KV records | measured token period (cycles) | tok/s (1.2 GHz) |
|---|---|---|---|---|---|---|---|---|
| solo | rtl_layer, user 0 only | 1 | 135 | 2,436 | 3 | 108 | 251,615 | 4,769.2 |
| pos2 | **rtl_layer** (of-record resources, layer granularity) | 2 placed | 256 | 4,742 | 3 / 2 | 211 | 251,615 / 265,387 | **9,290.9** aggregate |
| pos4 | cmdplane4 (STRESS: only command-plane resources) | 4 | 515 | 9,648 | 3 / 2 / 2 / 2 | 426 | 251,615 / 254,604 / 255,562 / 256,574 | 18,855 (not a production rate) |
| neg | pos2 with user 1 shifted +36 edges | 2 | - | - | - | - | - | fault_code[1] rises at edge 4,802 (as required) |

**Checks (PASS, mut 0).**
- **K1.** No calendar fault, no amax `mu_fault`, no KV range fault, no station clash, no empty emit.
- **K2.** User 0's events in pos2 equal the solo run exactly. That covers CMD, SUI, XCI, EMB, SEG, DONE, the argmax
  and the KV rows.
- **K3.** Every user's events equal the compiled starts plus the image entries, with that user's relocation, at the
  exact cycle (C_issue_offset 0).
- **K4.** Every emitted argmax equals the user's golden single-shot argmax. The head is 8 chunks x 256 rows, and ties
  go to the lower index.
- **K5.** Every q record's row equals 64 + l + 256 u, in rrow, in wrow xa and in the wrow lane.
- **K6.** The measured per-user token period equals the calendar's token_period.
- **K7.** The negative control faults.

**Mutants (all FAIL, witnesses in `smoke/`).**

| mutant | what it breaks | fails |
|---|---|---|
| cal11 | `qfd_dv_cmd_cal_mu` MUT 11: wrong-user relocation and tag | K3, K4, K6 |
| amax1 | `qfd_dv_amax_mu` MUT 1: ties go to the later chunk | K4 |
| glue1 | KV row user = the last START's user | K5, K2 |
| glue2 | STN user field not applied | K1 (empty emits), K4, K2 |

`amax2` (MUT 2: results merge into the current STN user) **passes**. It is equivalent once the calendar keeps the
station exclusive (F-TOK-1), so it is kept only as a diagnostic (`smoke/amax2.out`).

**Grade.** The command plane is MEASURED: the order, cycle and user field of every command, the head argmax on the
command stream, the KV row map and the per-user token cadence. The compute, KV and collective dataflow inside each
window is still the calendar's (measured-old-RTL plus priced) windows. **So the 9,290.9 tok/s for 2 users is a
command-plane measurement of the layer-granular calendar, not a token-pass rate.**

## 2. Findings

**F-TOK-1 (R4, MU-ADOPT-SLICE / MU-QWEN-HEAD).**
- **Problem.** `qfd_dv_amax_mu`, like `qfd_dv_slice2` today, gates station results with the CURRENT STN register
  (`stn_amax`) and attributes them to it (`stn_u`). An STN of ANY user, issued while a head chunk's results still
  stream, silently drops or misattributes those results. No `mu_fault` rises.
- **Witness.** `smoke/f_tok1_witness_no_cp_stn.out`. With mut 0 and no station rule, pos4 user 2 token 1 emitted
  index 865 instead of 431: equal value, and chunk 1's results were dropped.
- **Workaround in the generator.** The compiler reserves the station (`cp.stn`) from an amax STN's issue to its last
  result.
- **RTL fix owed.** Either carry {amax, user} with the station result, or make an STN issued while results are pending
  a sticky fault.

**F-TOK-2 (B1).** The calendar of record cannot be played by the MU RTL as built.
- `qfd_dv_cmd_cal_mu` has 4 descriptors: token start (stage 0), decode layer (stages 1..36), head (37) and boot. It
  plays a layer as ONE rigid segment a start.
- The record is op-granular. In 6 tokens, users 1 / 2 / 3 have 29 / 638 / 622 intra-layer op waits.
- The layer-granular calendar is what the RTL can play: 2 users, **9,291** modelled (the pos2 cadence above). Users 2
  and 3 never fit.

**F-TOK-3.** The calendar of record does not model the shared command plane: one start port, one cmd register, one
done register and the station.
- `record_cp` adds them at the smoke image's offsets: **13,981 vs 14,054 tok/s (-0.5%)**.
- At layer granularity they cost 0, with 0 clashes with or without them.
- Fold them into the calendar of record once B1 defines the op segments.

**F-TOK-4 (head clear/emit placement).** The image has a single head-chunk segment, so a chunk cannot clear or emit.
- The smoke puts AMAX emit plus clear in the stage-0 segment, which is the next token's start and embedding hand-off.
- It also adds a per-user AMAX prime (clear) at boot.
- The die must define the same: either chunk-first/last segments, or emit/clear in stage 0 plus a boot prime for every
  user.

**F-TOK-5 (L0).** The calendar's L0 puts the cold-fill +399 cycles inside qkv, so every later L0 op is shifted. The die
plays stages 1..36 from one layer segment.
- Either L0 gets its own descriptor, or the cold fill stays off the compute command plane and the calendar's L0 op
  windows are re-derived.

## 3. The real MU.TOK.QW bench (cases, operands, pass criteria, inputs)

**Case table.** Run `launch_mu_tok.sh cases OUT`, or `python3 -m qwen_static_schedule.mu_tok_cases --out OUT` from
`tools/`. Summary: `cases_summary.json`. The RTL-playable table is `cases_rtl_layer.json`. For every user it gives:
- every unit's start cycle and stage (layer l -> stage l+1, head chunk -> 37, head / next token -> 0);
- the user fields: VM / AR / DD / EM base + u x 4,096 (`mu_calendar.DV_UVM_STRIDE`; the smoke's 0x4000 is outside the
  16k-word slice VM), SU pidx + u x 128 (`DV_PIDX_STRIDE`; the smoke used 64), XC tag[7:6] = u, STN cmd[52:51] = u,
  AMAX cmd[9:8] = u, hc pos[17:16] = u;
- the KV rows 64 + l + 256 u;
- the positions. Every user sits in the T8192 bucket: user 0 starts at 8186, user 1 at 8180, user 2 at 8174 and user 3
  at 8168, each adding k per token. The attention window is therefore the single-user one, while the operands differ
  per user.

**Calendars.**
- The record: `compile_calendar(users=4, occupancy=measured, head_chunks=8, tokens=6, policy=priority)`.
- `record_cp` is the record plus the command plane.
- **`record_op` is the case table of record (MU-QW-B1, 10-19).** It is the op-granular PERIODIC frame of
  `mu_opcal.compile_frame(16)`: 16 latency tokens a frame (H = 4,026,800 edges), the command plane and the argmax root
  scheduled, **13,708.2 tok/s** (4,768.1 / 4,470.1 / 2,384.0 / 2,086.0). MU-OPCAL-EMB (10-19) moved the token-start
  LOCAL EMB after the user's argmax result (T = 60, was 16: 13,711.4); see `b1/README.md` section 6. The face plays user 0's stage starts and the
  op-start leaf plays the fillers' op starts with explicit entry ranges. It is RTL-playable: see
  `results/rtl/mu_qwen_1018/b1/README.md`. Run `launch_mu_tok.sh cases OUT` (variant `record_op`).
- `record` (14,054, finite horizon, no command plane) and `rtl_layer` (2 users, 9,291) are superseded as case tables;
  they stay as references.

**Cases.** Each extends a single-user TOK.QW bench and runs on the fleet with Verilator 5.050.

| case | extends | DUT / netlist | per-user operands | PASS |
|---|---|---|---|---|
| T1 compute layer x 4 | QW-CLAYER2 stage benches (`tb_qfd_dv2` N12 reg_vec/reg_mat, dv_layer composition; claude/qw-clayer2-1018 ca089ac2d) + QW-REALSTG real operands | colW5 column slice cut (`slice_cut.py`) from the compute GEN that carries `qfd_dv_cmd_cal_mu` NU 4 in `qfd_tt_ctlm_dv` OPSEG 1 (the op-start leaf + its ROM image from `mu_opcal.rom_words`) and the `qfd_dv_slice2` _e/_w MU faces (Q-DIE15 successor of dv2f14bi) | user u: its own x_u (hidden in), position pos_u, RoPE row, VM region base + u x 4,096; the user's op starts from `record_op` | each user's stage outputs bit-exact vs its golden; user 0's issue log and stage spans cycle-identical to the single-user T1 run; 0 faults |
| T2 KV attention x 4 | QW-KVATTN (0e509e763: service on real L0/L1, 1,561 cycles at T8192) + QW-KVATTN2 (die-netlist step) | `kvs_attn` + `kvs_ctl` slices of the KV GEN with `qkd_kv_mu_wrow` in `qkd_kvs_ctl` and `qkd_kv_mu_rrow` in `qkd_static_kv_pc_path_nc` (MU-ADOPT-KV), host MU1 | user u: its own KV (rows 64+l+256u filled from its prompt), q_u, pos_u | every user's attention output exact; each user's HBM PC stream inside its own kvs window; user 0's service cycles = single-user |
| T3 D2D pair x 4 | Q-XDIE pair_r2 (results/rtl/xdie_qwen_1018) | both D2D endpoints of the MU GENs | per-user q / o records at the calendar's cycles, user tag as a check field | every record lands at its compiled cycle for its user; exposed cycles a layer per user |
| T4 TP8 collective | MU-QWEN mu_bi (c82d57f7c, PASS: 30 ARs, 4 users, 61,440 words exact) | production wrapper, dv2f14bi lanes, LS 378 | from `mu_calendar.bench_cases` | rerun only if the MU GEN changes the collective calendar (LS) |
| T5 LM head chunks | MU-QWEN-HEAD `tb_amax_mu` (600/600 single-shot) | slice of the MU GEN; F-TOK-1 = the SLICE2 `stn_pend` sticky fault + the `cp.stn` rule (B2 closed) | each filler's head in 8 row chunks interleaved per the calendar | per-user argmax = single-shot over 151,936 rows; latency user's head as single-user |
| T6 host | MU-QWEN-HOST `tb_qkd_host_mu_out` | KV GEN host plane MU_OUT NSLOT 4 | 4 outstanding users | per-user CQ exact, in order |
| T7 composition | TOKEN-PASS `token_compose` | measured T1-T6 spans placed on the `record_op` frame (the leaf's playback, `mu_opseg_bench` C3/C4) | - | per-user token cycles and aggregate tok/s from MEASURED spans; latency user = single-user TOK.QW |

**Goldens.**
- User 0 uses the single-user TP4 realmem P8191 gold for L0..L2. The last layer and the head wait for the 36-layer gold.
- Users 1..3 need per-user fixtures (`tools/qwen_layerbench/gen_fixtures.py`) at their own position / prompt (B5).
- The numerics flag on TP8 P·V order vs the TP4 gold (QW-KVATTN) applies to every user.

**Launch.** `launch_mu_tok.sh gate COMPUTE_DIE_V KV_DIE_V TOKQW_RECORD GOLD_DIR` refuses only on B3 (the die
netlists lack the MU RTL, including the OPSEG leaf), B4 (no single-user TOK.QW PASS record) and B5 (no per-user goldens).
It no longer refuses on B1 or B2. When open it prints the T1-T7 steps.

## 4. Blockers of the real run

- **B1 CLOSED (MU-QW-B1 10-19, `results/rtl/mu_qwen_1018/b1/README.md`).** Coordinator option 2: the closed
  `qfd_sys_face` is unchanged, and an op-start leaf (ROM) in `qfd_tt_ctlm_dv` OPSEG 1 plays the fillers' op starts with
  explicit ranges. The fleet bench plays the `mu_opcal` frame. What follows is the original spec, kept as history.
- **B1 (MU-ADOPT-CTLM, R1). Op-granular playback.** (history)
  - `qfd_dv_cmd_cal_mu` needs per-op segments: about 12 op descriptors, plus L0 (F-TOK-5) and the head chunk
    first/last (F-TOK-4).
  - Today it has 4 descriptors (`dwr[1..4]`; `dwr[5..6]` must be 0).
  - Until then the RTL plays 2 users (9,291 modelled), not the record's 4 (14,054).
  - The image store's capacity (976 PW, against the 13,910 PW single-user need) is the same Q-DIE15 item.
- **B2 CLOSED (MU-ADOPT-SLICE2 a540f1f9f).** F-TOK-1 is now a sticky fault (`stn_pend`), and the calendar keeps the
  station exclusive (`cp.stn` in `mu_opcal`). Original text: carry the result's user and amax with the result, or
  fault.
- **B3 (MU-ADOPT-CTLM / -SLICE / -KV). Die GENs carrying the MU RTL.**
  - Compute die: `qfd_tt_ctlm_dv` binds `qfd_dv_cmd_cal_mu` NU 4, with start_user on the start face and `cmd_user`
    forwarded into STN `cmd[52:51]` and AMAX `cmd[9:8]` (the glue the smoke proves; glue2 shows its absence).
  - Compute die, MU-QW-B1: `qfd_tt_ctlm_dv` OPSEG 1 with its leaf ROM (`ot_rom_4096x72_m8`, the `record_op` image),
    and `ss5[27:26]` = the result's user from the slice root (the MU-QW-AMIX contract). The HF-4 kit regeneration must
    take the OPSEG RTL (lanes/HF-4.md).
  - KV die: the rowoff leaves get the issuing stage's user (glue1 shows what a "last start user" wiring breaks), and the
    host runs MU1 with NSLOT 4.
- **B4. Single-user TOK.QW gaps (inherited):**
  - G-C4 lowering, the 13,910 PW vs 976 capacity, the AR tag/last framer and the RoPE row (Q-DIE15);
  - attention return -> o_proj (QW-ATTNRET); xhead / tile delivery (QW-XHEAD);
  - real-operand stages (QW-REALSTG); the KV die-netlist step (QW-KVATTN2);
  - the TP8 P·V order numerics decision;
  - the 36-layer gold for the last layer and the head.
- **B5. Per-user goldens for users 1..3.** Distinct position or prompt in the T8192 bucket, for L0, L1, L35 and the
  head.

## Files

- `tools/qwen_static_schedule/mu_tok_cases.py` (+ `test_mu_tok_cases.py`, 4 PASS) is the case generator: variants,
  image, user fields, KV rows, playability and command-plane clashes.
- `tools/qwen_static_schedule/mu_calendar.py` has an opt-in `seg_windows` / `drop_resources` hook. It is off by
  default, and `test_mu_calendar` gives 11 PASS.
- `rtl/test/mu_qwen_tok/` holds the bench:
  - `tb_mu_tok_compose.sv` and `mu_tok_smoke.py`;
  - `run_mu_tok_smoke.sh`;
  - `launch_mu_tok.sh` (cases / smoke / gate).
- `results/rtl/mu_qwen_1018/tok/`:
  - `cases_summary.json` and `cases_rtl_layer.json`;
  - `smoke/` with the logs, the summary and the witnesses.
