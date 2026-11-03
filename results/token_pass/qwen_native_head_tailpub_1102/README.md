HEAD tail publisher, option A (owner 2026-11-02 17:55): explicit valid-row publisher in the canonical native
Qwen HEAD (stage37) event. RTL + selection + component evidence; no physical build, no change to the event's own
top-level enable (TOK-QW-3 stays held/default-off).

Source
- `rtl/physical/a0_rc16_head_tailpub/ot_qwen_w12_matvec_land32.sv` = rc14 PART1 file (left byte-identical) plus
  one opt-in parameter `TAILPUB` of `ot_qwen_w12_matvec_part` (default 0 = raw publisher). TAILPUB 1 forms, at the
  issue edge where e_v loads, `visible = t*(GT>>S)*IL + (gb>>S)*IL + j < nout/W` (full width) and carries it in a
  plain register line exactly as long as e_v -> t_vout (1+MEM_EXTRA+4+SD+OD+XTD = 46 for the selected set). Only
  t_vout is ANDed. Lease bit (wbase in [18432,20032), split 9, mmode 0, ROM source, W-aligned nout) loads with
  the descriptor; other ops publish raw. Predicate is per word, so an early GO (accepted while the previous op
  still drains) cannot re-label old words (the counterexample against the rejected 5-FF latch).
- Selection: `rtl/physical/a0_rc16_head_tailpub/head_event_part1.f` (replace the rc14 file, define
  OT_QWEN_HEAD_TAILPUB, which makes TAILPUB=1 the default of every PART1 instance, i.e. all NK/NL A0 tiles).

Evidence (epyc2, Verilator 5.050, yosys 0.67 orfs image)
- `bpilot/`: Codex's B-pilot gate (real macro ROM -> PART1, genuine tile0/block0 and tile639/block148 contexts),
  unchanged bench, rc16 file in place of rc14: PASS both contexts + wrongAddress/wrongCycle controls (TAILPUB
  default 0). With the canonical define: tile0 PASS unchanged; tile639 publishes only slots 0..2 per K, so the
  unchanged raw-64 bench fails at published word 3 holding raw ordinal 8 (K1 slot0) where raw ordinal 3 (slot 3,
  zero padding) used to be, as expected.
- `bench/`: lockstep bench `rtl/test/qwen_dv/head_tailpub/tb_head_tailpub_lockstep.sv`: original rc14 PART1
  (renamed only), rc16 TAILPUB 0 and TAILPUB 1, plus mutants TPMUT 1..5, one ROM/X stream. Every cycle: TAILPUB 0
  equals rc14 on every output; TAILPUB 1 equals rc14 on every output except t_vout (requests, addresses, data,
  faults, ready/idle, dates), and its t_vout equals raw valid AND the independent station-contract expectation.
  Genuine contexts check raw and published data against Codex's hdc_golden prefix. Results in `bench/results.tsv`.
- `ff/`: yosys census of PART1 as the A0 tile binds it: rc14 == rc16 TAILPUB 0 (17513 cells, identical FF mix);
  TAILPUB 1 adds 47 FF (46 predicate line + 1 lease bit; nout_r is already live in the selected PART1); total PART1 FF 116245 -> 116292 and 524
  unmapped generic gates (-noabc). Analytic estimate was ~65 FF/tile. Zero added pipeline cycles (t_vout date
  unchanged, checked by lockstep).

Open: TT/FF closure of the predicate cone (t*48 + q*8 + j vs nout/16 into the first line FF) in the A0 tile and
the A0 hard-core rebuild are physical follow-ups; the downstream STN/L6 consumer with the gapped 24-word pattern
(final selected raw ordinal 58) still needs its own source-event lease.
