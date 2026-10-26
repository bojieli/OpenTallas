# TOK-DS fc31 single-die layer cut replays (2026-10-24, epyc3)

Die fc31 (`die.v` 35ba1ef7 = cap30 + 59 chained-frame reset stations), programmes L0/L2/L14/L20 compiled on tree_fc31 with the
main compiler (`dv_layer_compile.py`, single-user, checkpoint fixtures). Vehicles: fc30 cuts patched with the fc31 station
delta (`tools/s81_dv/tokfunc/fc31/prep_fc31.sh`), Verilator 5.050 split builds; harness `tools/s81_dv/tokfunc/run_layers.py`.
Run root `epyc3:/srv/opentallas-scratch/claude/tok-ds/fc31` (run_data, run_c7, run_ctl). Data: `layers_fc31.json`.

| layer | compile ops (LOWERED/PARTIAL/GAP) | cut_0S | cut_0N | cut_7 | cut_3S_ctl (single-job harness) |
|---|---|---|---|---|---|
| L0 | 23/38/4 | 11,589 cyc, 0 faults, 0 checks | 10,657, 0 f, 0 ch | 11,579, 0 f, 0 ch | 855 checks, 231 mismatches, 0 faults |
| L2 | 18/47/18 | 26,863, 0 f, 0 ch | 21,817, 0 f, 0 ch | 26,853, 0 f, 0 ch | 869 checks, 233 mismatches, 0 faults |
| L14 | 18/54/20 | 27,863, 0 f, 0 ch | 21,784, 0 f, 0 ch | 27,853, 0 f, 0 ch | 901 checks, 241 mismatches, 0 faults |
| L20 | 18/49/17 | 30,913, 0 f, 0 ch | 24,685, 0 f, 0 ch | 30,903, 0 f, 0 ch | stopped (superseded) |

Verdicts:
- Data cuts 0S/0N/7: **FAIL by harness rule (zero checks)** — every scheduled input is driven and the cut runs fault-free, but
  the compiler encodes no in-cut output words: their outputs are off-die RD all-gather beats (payload = fixture leaf rows,
  masked) plus the 16-slice NX/XQ norm exchanges that are not compiled (G-COMPILER-ROWS / G-NORMALIZE-SO). Fault-free
  smoke only; NOT an exactness result.
- cut_3S_ctl with the single-job harness: mismatches from cycle 294 on the column-4 CTL line faces (`o__w_xrW_2S_l0_lnd`,
  `o__w_xrE_4S_l0_lnd`): the harness drove no host boot (layer programmes keep two native jobs under prog/job0, prog/job1).
  fc31 removes the fc30 status fault (fault_cycles 0 vs fc30 first fault at 155). Superseded by the native split-layer control
  replay (prepare_split_control.py + run_entry_replay.py, Codex 49f7915d5a: L0 job0+job1 PASS, mutant CAUGHT).
- Cycle counts are replay windows (programme ncyc incl. t0 = 100), not stage latencies.
