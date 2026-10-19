# MU-QW-B1: op-granular playback of the Qwen ROM 4-user calendar (B1, option 2)

Lane MU-QW-B1, 2026-10-19. Branch `claude/mu-qw-b1-1019`.

**Coordinator decision (B1 = option 2).** The closed `qfd_sys_face` is NOT changed. An observer leaf plays the filler
users' op starts. The compiler half is `tools/qwen_static_schedule/mu_opcal.py` (b30525ff0). This record adds the RTL
half, the fleet bench and the MU.TOK.QW case table.

## 1. Result

| | value |
|---|---|
| Calendar played | `mu_opcal.compile_frame(16)`: F = 16 latency tokens a frame. H = 4,025,840 edges and T = 251,615. The command plane and the argmax root are scheduled. |
| Rate (1.2 GHz) | **13,711.4 tok/s** aggregate: user 0 4,769.2 (= single user), user 1 4,471.1, user 2 2,384.6, user 3 2,086.5 |
| Starts and fires | 4,036 leaf entries (ROM 4,037 of 4,096 words) and 720 face starts a frame. 21,988 command fires a frame. |
| RTL playback (fleet, Verilator 5.050) | Every u_cal start and every command fire (cycle and word) equals the compiled playback. User 0 is cycle-identical to the single-user block. 0 faults. |
| Measured rate | Frame 1 is the steady state. Each user's token-start count times 1.2 GHz / H equals the compiled rate (table in s4). |

The RTL plays the 4-user op-granular frame. Before B1 it played 2 users at layer granularity (9,291 tok/s,
MU-ADOPT-TOK F-TOK-2). This is a **command-plane** measurement: the cycle, user and word of every start and command.
The compute, KV and collective dataflow inside each window is still the calendar's priced windows. The token pass
(MU.TOK.QW, T1-T7) measures that dataflow.

## 2. Design

Every new mode is opt-in. The defaults are unchanged in behaviour: the existing OPSEG 0 benches still PASS (s4).

### 2.1 `rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv` OPSEG 1: the op-start leaf

- **ROM.** One `ot_rom_4096x72_m8` with a 1-edge read. The image comes from `VIAMAP`, or from
  `+OT_ROM_DIR=<dir>` with `INSTANCE`. `mu_opcal.rom_words()` and `via_map()` / `viamap_hex()` build it. The F16 image
  is `rom/qfd_tt_ctlm_opseg.viamap.hex`.
  - Word 0 is the header: {magic 0x4F50, H 22, nent 12, T 22}. T is new in this lane; the bits were spare.
  - Words 1..nent are the entries, sorted by t_rom: {FIRST, cnt 10, first 10, stage 6, user 2, t_rom 22}.
- **Frame counter.** fc has period H and tc has period T. Both are anchored on the first stage-1 h_start that arrives
  after a good header. That edge has fc = tc = 0, which is calendar time 0: the latency user's L0 start.
- **Fire.** On the edge where fc == t_rom, the leaf consumes the entry. It presents a REGISTERED op start {user,
  stage, first, cnt} in the next cycle, so u_cal starts the playhead on edge t_rom + 1, which is the compiled S.
- **Prefetch.** One entry register. The consuming edge issues the ROM read of the next entry. After entry nent, the
  leaf reads entry 1 again for the next frame.
  - Compiler rule `mu_opcal.LEAF_MIN_GAP = 2`: consecutive t_rom values, including the frame wrap, must be at least
    2 edges apart. The F16 minimum is 6 and the wrap gap is 24,186.
  - `leaf_list` also checks 4-aligned ranges, user != 0 and the field ranges.
- **FIRST.** The entries of filler u that come before its FIRST entry are the tails of tokens that began in the
  previous frame. In the first frame after the anchor they have no beginning, so the leaf consumes them without
  starting anything. Once it has seen u's FIRST entry, every frame plays all of u's entries.
- **Sticky faults** (`op_fcode`; `mu_fault = |op_fcode`). None of them stalls.

  | bit | condition |
  |---|---|
  | [0] | Bad header: magic, H / T / nent zero, T > H, or nent > 4,095. The leaf never anchors. |
  | [1] | Anchor drift. Every stage-1 h_start must land on tc == 0, and every tc == 0 edge must carry one (none missing). tc must also wrap with fc. |
  | [2] | Missed or late entry: the entry is captured after its edge has passed, or an entry of the frame is still unconsumed when the frame wraps. |
  | [3] | Bad entry: user 0 or >= NU, stage > LAST_STAGE, cnt 0, unaligned first, t_rom >= H, or t_rom out of order or closer than 2 edges. |

- **Face side.** In OPSEG mode, dh_user and res_user are 0, because the face carries user 0 only. MUT 1..3 of the
  existing dh_user leaf are unchanged.

### 2.2 `rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv`: explicit-range start

- **New inputs.** `start_rng`, `start_first[9:0]` and `start_cnt[9:0]`. When `start_rng` = 1, the start plays image
  entries [first, first + cnt) instead of the stage class's descriptor.
- **Unchanged.** The same playhead start, fetch, T_k and faults. The first entry's delta counts from the start edge, as
  a descriptor's first entry does.
- **Range check.** A start is refused with `fault_code[0]` if cnt = 0, first is not 4-aligned (one store row holds 4
  entries) or first + cnt > nent.
- **Other sites.** `start_rng` = 0 is identical to the old block. The other instantiation sites (`_lpf_parts` u_gi,
  `tb_mu_cmd_cal`, `tb_mu_tok_compose`) tie it to 0.

### 2.3 `rtl/qwen_dv/qfd_tt_ctlm_dv.sv` OPSEG (NU 2..4)

**No port change.** The new parameters are `OPSEG`, `OPSEG_VIAMAP` and `OPSEG_INST` (default `qfd_tt_ctlm_opseg`).

- **Leaf placement.** The leaf `g_op.u_leaf` sits **inside the cluster** and observes `dh_q`, on the same edge as
  u_cal's start. There is no reason to place it at the die top:
  - its only consumer is u_cal;
  - inside the cluster, the anchor and the face start are the same flop.
- **Start mux.** u_cal start = face start (user 0) | leaf start (the leaf's user, stage and range).
  - A face start and a leaf start on the same edge set the sticky `op_fault`.
  - The face start wins, so the latency user is never delayed.
  - The compiler reserves one start port (`cp.start`).
- **Stage bank.** The per-user stage bank is written on the face start (user 0) and on every leaf start (the leaf's
  user). The head's running stage on LOCAL SEG then follows each user's own layer.
- **Filler token / position.** The face carries user 0 only, so:
  - on ss5 `tok_v` with `ss5[27:26]` = u != 0, `tok_b[u]` <= `tok_idx` and `pos_b[u]` <= `pos_b[u]` + 1;
  - `dc` `ntok` / `nval` / `tok_seen` take user-0 results only, so the face's RESULT capture never sees a filler
    token.
- **Contract with MU-QW-AMIX** (claude/mu-qw-amix-1019): `ss5[27:26]` = the user of `tok_idx` when `tok_v`. Those
  bits are part of ar_rank, which this cluster does not use, so they are spare today.
- **Faults.** `op_fault` = leaf fault | start collision, ORed into core_fault (dc[52], cf).
- **New macro in the cluster.** 1 x `ot_rom_4096x72_m8` (2,392 um²).
- **Sources.** `rtl/test/qwen_dv/tt_ctlm_dv_sources.f` adds the leaf and the ROM model.

## 3. Open items (honest)

1. **Filler initial context.** A filler's prompt token and position have no path through the closed face; its
   tok/pos bank starts at 0.
   - The bench preloads it only under ``ifdef QFD_CTLM_MU_BENCH_PRELOAD`` (`+MU_PRE_TOK<u>` / `+MU_PRE_POS<u>`). This
     is a bench-only path and not hardware.
   - Candidates are a host-side first result (an ss5 `tok_v` from the root before the user's first token) or a
     filler-context word in the leaf ROM.
   - This needs a coordinator decision.
2. **EMB before the result (image convention).** FIXED for the fillers by MU-OPCAL-EMB (section 6): EMB at T = 60.
   User 0 still sends the face's token (section 6, open RTL item). Original note: The token-start segment's LOCAL EMB is at T = 16, and the argmax
   emit is at T = 8.
   - The root result lands at most `AM_ROOT_SPAN` = 48 edges later, so the EMB sends the bank's PREVIOUS token. This
     applies to every user; the face's user-0 path has the same order.
   - The real image must place EMB at T >= AM_EMIT_T + AM_ROOT_SPAN, or take the token from the next stage start.
   - The bench models it exactly as built (C5), so it is a compiler image item, not an RTL fault.
3. **Kit.** `qfd_tt_ctlm_dv` is NOT closed: the HF-4d gate runs on a pre-MU kit. The next kit regen must take this
   commit (block in `lanes/HF-4.md`).
   - The kit synthesises the landed form `qfd_tt_ctlm_dv_lpf` (+ `_lpf_parts`). The OPSEG leaf must be ported into it:
     - the leaf and ROM in u_gi (core region, beside u_cal);
     - `ss5[27:26]` into u_go for the dc user-0 gate.
   - The lp / eq lockstep benches must be re-run at OPSEG 1. This lane did not port lpf: it stays OPSEG-free and
     PASSES at OPSEG 0.
4. **ROM headroom.** F16 uses 4,037 of 4,096 words, so a larger frame needs a second macro or a smaller F.
5. **Steady state only from frame 1.** In frame 0 the fillers' cross-frame token tails are skipped (FIRST), as
   designed. Rates are therefore read from frame 1.

## 4. Benches (fleet, Verilator 5.050, ot-run on ot-epyc4)

`rtl/test/mu_qwen_seq/run_mu_opseg.sh WORK` (parts `pass mut old`) and `mu_opseg_bench.py`. The harness is
`tb_mu_opseg_dv.sv`. Logs are in `runs/`.

**Cases.** Each mu run is `qfd_tt_ctlm_dv` NU 4 OPSEG 1, and each reference is NU 1 OPSEG 0 with user 0's starts
only.

| case | calendar | edges | starts | fires (u0/u1/u2/u3) | verdict |
|---|---|---|---|---|---|
| full | F16 x 36 layers, frame 0 + 30k edges of frame 1 | 4,056,940 | 4,792 | 22,146 (7,703 / 7,221 / 3,853 / 3,369) | PASS |
| full2 | F16 x 36 layers, frames 0-1 + 30k edges | 8,082,780 | 9,548 | 44,134 (15,351 / 14,391 / 7,677 / 6,715) | PASS |
| red | F16 x 2 layers (H 279,856), 3 frames | 842,668 | 1,481 | 3,677 (1,731 / 1,082 / 540 / 324) | PASS |
| neg_drift | red, user 0's 2nd L0 start one edge late | | | | `op_fcode[1]` at edge 18,592 (want 18,591 + 1) PASS |
| neg_coll | red, an extra face start on a leaf start's edge | | | | `op_fault` at 6,470 (want 6,469 + 1), lcode 0000 PASS |

**Checks.** Every check below passes in full, full2 and red.

| check | requirement |
|---|---|
| C1 | No calendar fault, no start_fault, no `op_fault`, leaf code 0000. |
| C2 | User 0 is identical to the reference: CMD (cycle and word), EMB / SEG / MES, the head SU count, **dc on every change** (no filler result reaches the face's RESULT capture), and the head-side outputs up to the first filler LOCAL SEG. |
| C3 | Every u_cal start (cycle, user, stage, range) equals the compiled playback. |
| C4 | Every user's command fire (cycle and the relocated word) equals the compiled fire. |
| C5 | Every filler EMB and SEG carries its own bank: the preload, then tok = the root token and pos + 1 at each of the user's results. |
| C6 | After every ME start, the head running stage is the stage of that segment's user. |

**Measured rate in frame 1** (steady state). Each value is token-start segments of the user times 1.2 GHz / H.

| case | user 0 | user 1 | user 2 | user 3 | aggregate | compiled |
|---|---|---|---|---|---|---|
| red (2 layers) | 16 -> 68,606.7 | 10 -> 42,879.2 | 5 -> 21,439.6 | 3 -> 12,863.8 | 145,789.3 | identical |
| full2 (36 layers) | 16 -> 4,769.2 | 15 -> 4,471.1 | 8 -> 2,384.6 | 7 -> 2,086.5 | **13,711.4** | identical |

**Mutants.** Each must FAIL, and each fail witness is committed in `runs/`.

| MUT | what it breaks | case | fails on |
|---|---|---|---|
| 21 | u_cal range ignored: the stage descriptor plays | red | C1 (u_cal fault_code[0]: descriptor overruns) + C3/C4 (4,607 fires vs 3,677) + C5 |
| 22 | face + leaf start collision not flagged | neg_coll | neg_coll: no op_fault |
| 23 | filler result written to the next filler's bank | red | C5 EMB/SEG tok/pos from the wrong bank |
| 24 | leaf entry consumed one edge late (off by one) | red | C1 (fault_code[1] cmd collision) + C3 starts one edge late + C4 |
| 25 | leaf re-anchors on every L0 start (anchor drift) | red | C3 (547 of 1,481 starts) + C4 |
| 26 | leaf drift / missing check dropped | neg_drift | neg_drift: no op_fcode[1] |

**OPSEG 0 stays PASS** (`old` and `dhuser` parts; logs in `runs/w2/old_*`, `runs/w4/`):
- `run_mu_ctlm.sh`:
  - mu 0 PASS, and 16-20 FAIL;
  - prog `--hard 1 --landed 1` PASS, with LANDED_LOCKSTEP 18,071 / 0 mismatches, and mut 1 FAIL;
  - lp: audit PASS, MUT 0 PASS, 1 and 2 FAIL;
  - eq NU 4 PASS, and 5 and 6 FAIL;
  - seq PASS;
  - ctlm part:
    - ABI 0 PASS, 4-8 FAIL;
    - cal 0 PASS, 1-3 FAIL.
- ctlm `--nsl12` (12-slice SETID): MUT 0 PASS 74/74 and MUT 3 FAIL 61/74 (`runs/w7/ctlm.out`, ot-epyc5, after the
  pre-existing source-list fix d3044d6af).
  - The first w2 attempt lacked a staged source directory (`rtl/test/full_sm_service`).
  - The w5 attempt failed MODMISSING on `qfd_dv_amax_mu`, which `qfd_dv_slice2` has instantiated since MU-ADOPT-SLICE.
- `run_mu_tok_smoke.sh`: 0 PASS; cal11, amax1, glue1 and glue2 FAIL.
- The existing R3 leaf bench `adopt_slice/tb_dhuser.sv` still compiles the leaf file ALONE at OPSEG 0. The OPSEG branch
  and the ROM are not elaborated.
  - MUT 0 seeds 7 and 11 and +slip all PASS.
  - The mutants FAIL with the same counts as in adopt_slice: MUT 1 with 3,494 mismatches, MUT 3 with 349, and MUT 2
    +slip with "slip not detected".

## 4b. The leaf as its own kit (coordinator note 10-19)

`qfd_sys_face_mu_dhuser #(.NU(4), .OPSEG(1), .LAST_STAGE(37), .VIAMAP("<image>.viamap.hex"), .INSTANCE(""), .MUT(0))`
is a self-contained leaf. Its ROM (`u_rom`, `ot_rom_4096x72_m8`, macro 38.016 x 62.91 um) sits inside it.

**Ports.**

| direction | port | width | meaning |
|---|---|---|---|
| in | `ck` | 1 | the cluster clock |
| in | `rst_n` | 1 | asynchronous reset |
| in | `dh_run` | 44 | `seq_dh[43:0]`, registered by the parent (`dh_q[43:0]`): h_start [42] and stage [41:36] only |
| out | `dh_user`, `res_user` | 2 each | 0 in OPSEG; leave open |
| out | `mu_fault` | 1 | the leaf's sticky fault |
| out | `op_v` | 1 | registered op start |
| out | `op_user` | 2 | the op's user |
| out | `op_stage` | 6 | the op's stage |
| out | `op_first`, `op_cnt` | 10 each | the explicit entry range |
| out | `op_ff` | 1 | observability only |
| out | `op_fcode` | 4 | the sticky fault code |

**Kit details.**
- Every output is a flop, so the outputs are pin-registered by construction.
- The only input used is `dh_run[42:36]`; the other bits are unused.
- Parameters `USER_SEQ`, `STG_SEQ`, `RES_SEQ` and `NS` are unused in OPSEG.
- The ROM content is the via-map file `rom/qfd_tt_ctlm_opseg.viamap.hex` (F16). For a hardened kit, pass it as
  `VIAMAP`, or pass the instance name as `INSTANCE` for `+OT_ROM_DIR`. The macro's layout and timing do not depend on
  the content.
- The logic is about 200 flops: fc / tc 44, the prefetch entry about 55, the outputs 31, the header about 56, and
  pointers / flags.
- Timing paths:
  - the 22-bit fc == t_rom compare into the ROM address and the output registers;
  - the ROM read clk->q (1-edge) into the prefetch register.

## 5. MU.TOK.QW preparation

- `tools/qwen_static_schedule/mu_tok_cases.py` has a new variant **`record_op`** (`cases_record_op`). It is the
  mu_opcal frame as the RTL plays it:
  - every start {cycle, user, stage, first, cnt, src face/leaf, first_of_frame};
  - the DV strides (4,096 / 128), the KV rows and the leaf ROM header.
  - It is the case table of record. `test_mu_tok_cases.py` passes 5 tests (new: `test_record_op_playable`).
- `rtl/test/mu_qwen_tok/launch_mu_tok.sh gate COMPUTE_DIE_V KV_DIE_V TOKQW_RECORD GOLD_DIR` now refuses only on:
  - B3: the die GENs lack the MU RTL, now including the OPSEG leaf;
  - B4: no single-user TOK.QW PASS record;
  - B5: no per-user goldens.
- The gate no longer refuses on B1 or B2. `tok/README.md` T1-T7 and section 4 are updated.

## Files

- RTL:
  - `rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv` (OPSEG leaf);
  - `rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv` (explicit range);
  - `rtl/qwen_dv/qfd_tt_ctlm_dv.sv` (OPSEG);
  - ties in `rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv`, `rtl/test/mu_qwen_seq/tb_mu_cmd_cal.sv` and
    `rtl/test/mu_qwen_tok/tb_mu_tok_compose.sv`.
- Compiler: `tools/qwen_static_schedule/mu_opcal.py`:
  - `LEAF_MIN_GAP`, alignment and field checks in `leaf_list`;
  - T in the header;
  - `viamap_hex`;
  - `--layers`.
- Compiler: `tools/qwen_static_schedule/mu_tok_cases.py` (`record_op`).
- Bench: `rtl/test/mu_qwen_seq/{tb_mu_opseg_dv.sv, mu_opseg_bench.py, run_mu_opseg.sh}`.
- Records in this directory:
  - `receipt_F16.json` and `receipt_F16_L2.json`;
  - `rom/qfd_tt_ctlm_opseg.viamap.hex` (the F16 leaf image);
  - `runs/` (logs and summaries).

## 6. MU-OPCAL-EMB (10-19): the token-start EMB issues after the user's result

Branch `claude/mu-opcal-emb-1019`. **Compiler image only. No RTL changed.** The leaf ROM content changed, so the kit takes
the new via-map `rom/qfd_tt_ctlm_opseg.viamap.hex`; the macro does not depend on the content.

**Derived edge** (`mu_opcal.tok_slice0_edge`, `RES_SSQ`, `RES_BANK`, `EMB_T`). Edges count from the AMAX emit's u_cal
issue edge I = S + 8:

| step | RTL | edges |
|---|---|---|
| u_cal `cmd` register -> W5 `cmd_q` | `qfd_dv_slice2` pin register; die bind tt_ctlm.cmd -> dvs_W5.cmd_wi is direct (`dv_case.W5_PEERS`) | +1 = e |
| root merge + TOK to W5 | `qfd_dv_scalar2`: last candidate merges on X(r) = max(2r + 2, 2k + 2\|k - r\| + 3); TOK leaves dn_o on X + 1, 2 edges a hop; W5 tok_v on X + 2r + 1. Worst over the root r = e + 48 | +48 |
| W5 `st` (ss_wo) | `st[24]` <= tok_v | +1 |
| ctlm `ss_q` | pin register (die bind dvs_W5.ss_wo -> tt_ctlm.ss5 direct) | +1 = I + 51 |
| `tok_b[u]` | r_fill write | +1 = I + 52 |
| EMB | `emb_token <= tok_b[b_rd]` on the edge after the issue edge: issue >= I + 52 | **EMB_T = 8 + 52 = 60** |

A relay stage that the die GEN inserts on cmd or ss5 adds one edge to `AM_CMD_PIN` or `SS_PIN`.

**Compiler.**
- `mu_opcal.segments` places the LOCAL EMB of segment 0 at `EMB_T`. The `mu_tok_cases` smoke image keeps 16 and is
  labelled as stale.
- `check_emb_after_result` runs in every `compile_frame`. For every token start of every user, it reads the image's
  real emit and EMB entries and raises `ScheduleError` when the EMB is earlier than the emit + `RES_BANK`. The tests
  cover EMB_T 16 and 59 (both raise) and 60 (passes).
- The embedding request, host return and row fetch need the new token, so the token-start block's priced windows
  (d2d_o, host and the 272-edge fetch) start at the EMB (`mu_calendar.head_blocks` `head_tok_ofs`, default 0, and
  `mu_opcal` sets it to EMB_T). **The token is 60 edges longer.**
- LOCAL entries now also reserve `cp.cmd`, because they use the one u_cal issue register (`i_col`). The frame did not
  change because of this.

**Rate (F16).**

| | before | now |
|---|---|---|
| T (edges) | 251,615 | 251,675 |
| H (edges) | 4,025,840 | 4,026,800 |
| user 0 (latency) | 4,769.2 | **4,768.1** |
| user 1 | 4,471.1 | 4,470.1 |
| user 2 | 2,384.6 | 2,384.0 |
| user 3 | 2,086.5 | 2,086.0 |
| aggregate | 13,711.4 | **13,708.2** |

- Tokens a frame are unchanged (16 / 15 / 8 / 7), and so are the leaf entries (4,036).
- **User 0 is still cycle-identical to the single user** (`compile_frame` checks this, and so does bench C2). The single
  user's token is also 60 edges longer: the solo image has the same segment 0, and its embedding cannot start before
  its own argmax result either. So 4,769.2 was optimistic by 60 edges a token, and the new latency figure is 4,768.1.
- Red (2 layers): 145,789.3 -> 145,290.9.

**Open RTL item: user 0.** `tok_b[0]` is written only from the face's dh start (`s_tok`), and r_fill excludes ss_tu 0.
- User 0's EMB therefore sends the token the face presented at its stage-0 start. The face takes the result only at its
  RESULT capture, which comes after that start.
- Moving the EMB in the image cannot fix this. It needs a `qfd_tt_ctlm_dv` change (for example, r_fill also writes
  tok_b[0] in OPSEG), or the face's own E-calendar embedding for user 0.
- This is not the leaf. It is left to the coordinator, and bench C7 reports user 0 for information only.

**Bench** (`run_mu_opseg.sh` parts `pass mut emb full2`, fleet, Verilator 5.050, sources = this branch).
- RES events now come at the RTL-derived edge (start + 8 + C 1 + 51; it was start + 40).
- The bank model is exact (RES_APPLY = BANK_WR 1, with no ambiguity margin), and the calibration K = 0, C = 1 is checked.
- New check **C7**: every filler EMB equals the result of its own segment's emit.
- New witnesses (mut 0 RTL; each must FAIL C7):
  - `--emb-t 16`: the pre-fix image;
  - `--res-skew 1`: the result one edge late. The EMB sits exactly on the first edge that sees the result.

**Results** (ot-epyc4, sources 99dd2515f; logs and summaries are in `runs/emb/`):

| run | verdict |
|---|---|
| pass: red, neg_drift, neg_coll, full | **MU_OPSEG_PASS**, C1-C7 |
| C7, red | 54 of 54 filler EMBs carry their just-computed token, 0 wrong |
| C7, full | 30 of 30 filler EMBs carry their just-computed token, 0 wrong |
| calibration | K 0, C 1 |
| red frame-1 measured rate | 68,372.2 / 42,732.6 / 21,366.3 / 12,819.8, identical to the compiled rate |
| neg_drift | op_fcode[1] at 18,652 |
| neg_coll | op_fault at 6,470 |
| mut 21-26 | each MU_OPSEG_FAIL, on the same checks as in section 4 |
| emb16 witness | **FAIL C7**: 54 of 54 stale |
| skew1 witness | **FAIL C7**: 54 of 54 stale |
| user 0 (information only) | 48 (red) and 16 (full) EMBs send the face token, 0 the just-computed one: the open RTL item above |
| full2, the steady-state 36-layer rate | still running at hand-off: `ot-epyc4:/home/ubuntu/ot-bench/mu-opcal-emb-1019/w_full2`, listed in pending_results |
