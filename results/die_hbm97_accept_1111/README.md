# DIE-HBM-97 accept-early 11-11: u_control acceptance rebalance (RTL event (C), COORD yes on dma-vpose3)

**Problem.** In the routed vPose3 form of `ot_hgi_dma_back_static_vp4_banks_cp` (DRC 0, core hold clean), TT setup is
-108.13 ps over 330 endpoints. Placement already fixed the distance part; what is left is depth in the u_control
descriptor-acceptance stage:
- `b_mv -> c_hok` -108.1 ps: `c_hend_d = b_hbase_end + b_hprod` (41-bit add) and the range compare, in one stage;
- `c_hok`/`valid_move` fan-out into the 17 load groups (`wb_fill_epoch`, `land_left`, `wb_reserve_v`, `m_end`,
  `pending_sectors`, `fa_m2`: -45 to -85 ps);
- `chunks -> drain_slot` fan-out (`read_mask_q`, `drain_chunk_hbm`, `nd_m2`, `drain_index`: -51 to -80 ps);
- `drain_chunk_hbm -> bank_read_addr` (eight 32-bit adds) -47 ps.

**Change (define-gated, 0 cycles).** Under `OT_DMA_ACCEPT_EARLY`, in `ot_hgi_dma_back_static_vp4_controller`
(`rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv`, applied by `accept_early_patch.py`):
1. `q_hbase_end` is formed one stage earlier (p -> q), and `b_hend = q_hbase_end + q_hlo + (q_hhi << 16)` (q -> b). The
   c-stage horizontal check is then a compare only.
2. `valid_move` becomes a flop: four kept copies `c_valid_0..3 <=` the AND of the same next-state terms. The loads are
   split by group (g < 5, < 9, < 13, else); `cv` gets four kept copies for the same groups.
3. `chunks` gets four kept copies, one per consumer: issue compare, match/nd registers, read enables and masks, and drain
   address registers. Each copy has its own `drain_slot_*` compare.
4. `bank_read_addr` uses a carry-select: `{(lo3 + b) carry ? hi + 1 : hi, (lo3 + b)[2:0]}`, with one shared 29-bit
   increment.

There is no schedule, pin, latency or interface change. The kit keeps the copies through `ot_keep_regs.tcl`
(SYNTH_CANONICALIZE_TCL).

**Scope.** Only the dma type kit `vp4_vPose3C` sets `-DOT_DMA_ACCEPT_EARLY` (together with B's `-DOT_CMD_FIRE_EARLY`).
This branch is on top of `claude/die-hbm-97-cpfire-1110`.

Users of the controller found by grepping rtl/:
- `ot_hgi_dma_back_static_vp4_banks`, `_banks_cp`, `_banks_cplw`;
- `ot_hbm_svc_wb_kport`;
- benches: `tb_dma_vp4_*`, `tb_dma_back_vp4_banks_equiv`, `tb_dma_counter_prefix`, `tb_hbm_svc_wb_kshare_*`.

The parameter sets are MUT 0/1/2/3, RR_RT 7/9/80, LOCAL_CTRL 0/1 and STACK_BYTES. With the define off, the
preprocessed token stream is the original one: only `` `ifdef``/`` `define`` lines are added, and every use goes through
`` `OT_ACC_SEL(new, old)``.

**EQ step A (yosys sat, `eq/run_eq_c.sh`, logs in `eq/logs`).**
- inv, `sat -tempinduct` of the FORMAL invariants: PROVEN (base and induction at length 1). The invariants are:
  - each pipeline valid bit implies its age since local reset release;
  - `q_hbase_end` equals its q-stage formula, and `b_hend == b_hbase_end + b_hprod`;
  - under `cv`, every `c_valid_k` equals the old `valid_move` AND (valid_move and chunk_valid are only consumed under
    cv or its copies);
  - `cv_k == cv`, `chunks_* == chunks` and `drain_slot_* == drain_slot`;
  - the carry-select address equals `drain_chunk_hbm[36:5] + b (+ MUT 1)` for all eight banks.

  Every replaced use therefore sees the same value, so the define-on controller is cycle-equivalent to the define-off
  one (substitution argument, as in cpfire).
- Negative controls must FAIL, and all do with a real base-case counterexample:
  - NEG (`c_valid` drops the hok term): fails at length 9;
  - NEG2 (`b_hend + 1`): fails at length 7;
  - NEG3 (carry-select `hi + 2`): fails at length 1.
- identity: the define-off controller is elaborated (`proc`; `write_verilog -noattr`) under 9 parameter sets, and the
  sha before and after is compared. The source file:line embedded in function-local wire names
  (`\inc32$func$<file>:<line>$...`) is stripped before hashing. The first run without that normalization showed exactly
  those 4 lines as the only difference. Results are in `eq/identity.tsv`.
- bmc: a bounded miter of old vs new (and of old vs NEG) is added when it finishes.

**EQ step B.** `lec.py` runs in the kit flow (async LEC, VERILOG_DEFINES honoured): the define-on netlist against the
define-on RTL.
