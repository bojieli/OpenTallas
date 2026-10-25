# QC token side: tp8 collective link pass with the wavefront reset (owner decision 13 / 13c), 2026-10-25

This re-runs the tp8 pass of `../../qc_1024/link_meth` (codex/qc-meth-receipt-1025, LS 407, COLL_BENCH_ARGS
`--relays 0 11 11 11 --lanes 2 2 21 2 2 20 --lx 23 4 22`, MU window `mu_cal_ls407.json`) with the published wavefront
reset offsets. The schedule starts on an explicit START broadcast after the latest release. Verilator 5.050, run on intel1
through ot-run. The source is the `git archive` of this branch (plain: f408869ff7, start pin: 669d5efe1c; 669d5efe1c only
adds the start-pin option, and its default leaves the plain wavefront unchanged).

## What the tb did before

- The tb had one reset. `rst_n` deasserted at cycle 15 (`rcnt == F`) on all 8 dies and on every instance.
- The issuer program was written from cycle 20, and `stage_start` was a one-cycle pulse at `+START` (default 40).
- All compiled command, producer and output cycles are relative to START, so the start was already an explicit pulse,
  not the reset edge. It sat a fixed 25 clocks after reset.
- Flops that carry reset:
  - In the collective (`ot_coll_tp8_static`), the valid/control replicas (`ot_coll_rep_reg RST(1)`), the local
    `ot_coll_rst_leaf` syncs and the fold slices. The data replicas are `RST(0)`.
  - In the IO calendar / linkcal and the faces, the slot counters, epoch and CDC pointers (each face has its own 2-flop
    `ot_reset_sync`).
  - In the codecs, their state.
  - The paid relay rows (`qfd_coll_static_relay`) reset all W bits. These are datapath flops with reset, which is not
    the decision-13 form. That is RTL-of-record behaviour and not something this bench changes.

## Wavefront model (opt-in: `+define+OT_TP8S_WAVEFRONT`, bench `--wavefront <bind_reset.json>`)

Partition releases come from `bind_reset.json` of the r3 wavefront bind (epyc3 `codex-qc-bind-1025/wavefront_r3`,
sha256 0cac2847…; identical releases to `qc_1024/xt1_meth/reset_offsets_meth.json`; root sl_W0_ctl, max_release 128).
Instances are mapped through that bind's `bind_names.json`. A group releases at its latest member.

| tb reset group | plan partition(s) | tb instances | release |
|---|---|---|---|
| WF_ISS | sl_W5_fw (cmd source) | issuer (ot_coll_cmd_issue / qfd_seq_su_collective_calendar) | 88 |
| WF_CORE | coll_core | u_io.u_collective, g_face[0], g_face[1] | 98 |
| WF_N | coll_n | g_face[2] | 94 |
| WF_S | coll_s | g_face[3], g_face[4] | 104 |
| WF_UCIE | coll_ucie | u_shared, g_six_five.u_gearbox, UCIe PHY model | 103 |
| WF_FT | coll_f0..f5 (max) | relay rows of faces 2-4 | 108 |
| WF_SER0/1/2 | io_serdes, io_serdes_1, io_serdes_2 | SerDes PHY model of port j | 92 / 101 / 111 |

- Each group is a registered tap that releases `t0 + release`.
- The parent's single `rst_n` is re-driven per leaf with `force`. A witness (`WF_RISE`) records the cycle at which each
  forced leaf port actually rises.
- The program write starts at START-20, and START = latest release origin + 130 (the r3 carve value, max_release 128 + 2).
- `--wf-start-pin S` models the decision-13c die START pin (CLOCK-RESET claude/clock-reset-1025@e84452a8fd, start.mode
  broadcast; `start_pin/bind_reset_start.json`, same releases). Soft partitions release at max(rst_n, S) + offset. The
  hard SerDes PHYs are on raw reset (rst_n + offset).

## Verdicts

| set | case | expectation | result |
|---|---|---|---|
| start pin S=60, die rst_n skew 3 (dies 15..36) | cal, cal_seqsu, mu | PASS | **3/3 PASS**, witness exact on all 8 dies |
| start pin | spin_neg_start_rel85 (START = S+85, before coll_core 98) | FAIL | FAIL as required (coll_fault all dies) |
| start pin | spin_neg_start_s25 (START = S+25) | FAIL | FAIL as required |
| plain, skew 0 | cal_wf_skew0 | PASS | **PASS** (4/4 production cases, witness exact) |
| plain, skew 3 | cal, cal_seqsu, mu | PASS | functional checks all clean (mm 0, no faults, every word); **marked FAIL by the release witness**, see below |
| plain, skew 3 | 9 mutants (cal_minus1 … mu_neg_overlap) | FAIL | **9/9 FAIL as required** |
| plain, skew 0 | wf_neg_start_rst_edge (START 40 = old reset-edge timing, issuer released with rst_n) | FAIL | FAIL as required |
| plain, skew 0 | wf_neg_start_rel85 (START before coll_core 98) | FAIL | FAIL as required |
| probe | START rel 90 (issuer early) | info | FAIL (coll faults) |
| probe | START rel 95 seqsu / 100 / 109 (faithful issuer) | info | PASS |

**Cycles** (start_pin and plain skew0) are identical to the non-wavefront pass in every reported value: AR256 E 315,
span 826, first-in→first-out 570, AR256x2 1,082, argmax E 467 / span 475, layer 2xAR+argmax 1,500, token all-reduce
36x2xE 22,680, token_span 59,947, MU4 window 36,780 (E 315), user-0 alone 30,586. Delta 0. All compiled cycles are
relative to START, and START only moves, from 40 to 145-190.

**Negative control: where the path stops caring.** The first command reaches the collective about 11 clocks after
START.
- START at rel 85 or 90: commands hit coll_core (98) while it is still in reset. Every die faults. The failure is real
  and functional.
- START at rel 95 or later: the path is insensitive. Every partition the schedule touches is released before its first
  use. The faces, relays and PHYs see their first frame only after LS/LU, and coll_s/coll_f/io_serdes_2 (104-111) are
  hit much later than START+11.
- The faithful issuer (sl_W5_fw, 88) cannot start before rel 109, because it needs a 17-word program window after its
  release. So with the published offsets, a too-early start is only reachable if the issuer (or start source) leaves
  reset early.
- The tb prints `WF_START_BEFORE_RELEASE` for every such run. The r3 START at rel 130 has 19+ clocks of margin over the
  insensitivity bound.

## Open item: plain-wavefront per-die skew is not realised for forced leaves

With `--wf-skew 3`, `WF_RISE` shows that every die's forced leaf resets rose at die 7's cycle (abs 131 = 33 + 98).
Verilator 5.050 applies the `force` from the generate loop to the replicated, non-inlined parent instances with one
instance's RHS. A small inlined repro does not show this. Effects:
- The issuer and the PHY models (direct ports) did skew per die.
- The collective partitions released uniformly at die 7's origin.
- The functional result of those runs is clean, but it does not prove independent per-die partition release, so the
  witness marks them FAIL. The collector verdict for `plain/` is therefore FAIL.

The start-pin set is the decision-13c form: soft partitions on the common S, raw-reset hard PHYs skewed per die. The
witness is exact there, so it carries the per-die-skew claim. Making the plain skew exact needs per-partition reset
ports instead of `force`. That means either a tb-local copy of qfd_collective_static_io, or the bound partition tops.

## Failed attempts (data deleted, logs kept)

1. Run 1 (`logs/fail1_dieskew_witness/`, commit 6e6f568f7a): a combinational partition reset and a single-cycle witness
   flagged only die 4 (largest skew, 21 > die 7's 18). That was the same force issue showing as "die 4 early". Run 2
   (f408869ff7) added registered taps and the full rise witness, which made the cause visible.
