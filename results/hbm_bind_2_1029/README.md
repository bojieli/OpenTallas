# HBM-BIND-2 (2026-10-29): scorer/SFU landing homes, SU form S1 vs S2, dead-input proof, EMIT diagnosis

Base: HBM-BIND-1 B1s (claude/hbm-bind-1-1029@9e1fb425c3). Plan 16e0513d (Codex /plan, read-only), netlist c0eadd4c,
elab reused from HBM-BIND-1 b1s/out/asbuilt.json (map-only changes; the elab does not depend on the map).
Bind step = tools/die_plan/bind.py of this branch, --strict. Runs: intel1:/srv/opentallas-scratch2/claude/hbm-bind-2-1029/{h1,s2,h2,h3}.
All bind numbers below are CHECKED from out/bind_report.json (*_bind_head.txt, *_unplanned_vs_b1s.txt).

## (1) Landing homes for the 5,572 residual scorer/SFU cells (landing_homes.py -> homes_h1.json)
Whole cells, no FF fracture, no duplication, no semantic edit.
- Scorer quarter (ot_hbm_idx_score_quarter_static_h): leaf glue (W/E pin regs, sum bus, chunk core glue, u_qlate/u_vl/u_rr)
  with its own leaf's u_hc partition; 10 leaves whose 8 u_hc sit in two partitions go whole to the majority partition
  (bit vote, listed in homes_h1.json report.split_leaves). Quarter glue: E side = forward-reachable from the last leaf /
  u_t / md / keep_pipe -> tail partition T (E glue, tail regs, output score regs, score_fault_check, md, keep_pipe: 58 cells);
  the rest (input pin flops + W glue, reset relay: 159 cells) -> r0c0 front partition F. keybuf glue + quarter fault $or -> keybuf hub.
  NE/NW: F=b100, T=b103; SE/SW: F=b000, T=b002.
- SFU: all residual (store glue 1143, u_output, u_vm bridge, u_core/u_engine glue, u_rst) -> b113 (operand store, SU lanes L47/L54).
Result h1: unmapped 5,572 -> 0. UNPLANNED 106 pairs/94,141 b -> 158/179,387 b. TIED 0 -> 2,080 bits (now visible, see (3)).

## SU slice form, run in parallel (12.17(3)), both with the h1 homes
| form | UNPLANNED pairs | UNPLANNED bits | other errors |
|---|---|---|---|
| S1 = B1s two halves (Codex SU ownership r3) | 158 | 179,387 | same |
| S2 = Codex central counterfactual (all SU residual in the primary half, records[].primary_counterfactual) | 158 | 199,335 (+19,948) | same |
Neither reaches bind 0 without plan lanes; S1 has fewer crossing bits -> S1 WINS (agrees with Codex 60,296 vs 86,328 estimate). S2 stopped.
SFU variant h2 (non-store SFU control at the hub landing b110 instead of b113): 170 pairs / 182,059 b -> worse, rejected.

## (2) EMIT hcb bank128_pair0 rst_n: diagnosed, not caused by the cones compose
Plan type q_b000 declares 8 hard cores u_hcb_Q0.ot_hbm_hc_bank128_pair0..7 (native128 pair cut). The manifest elaborates
hcb_NE0 as ONE opaque leaf ot_hbm_hc_bankq0_static (r18h5 bundle hcb0.sv; hcb_NE1.. = ot_hbm_hc_bankq_static,
hcb_NE7 = ..._term_static). No source or compose entry produces the pair cores: physical/die_plan/hbm_arch_cores/native128/
templates.json says qualification PARENT_BIND_PENDING, pending exact_native_parent_cut_maps. bind.py raises at the first
core reset it cannot find, so this was hidden behind the mca EMIT in Codex r2. Fix = the native128 parent cut map
(compose cores for each hcb bank's 8 pair cuts, as for the SU __cut_lane_exp cores) -> successor / native128 owner.

## (3) Constant-tied leaf pins
- scorer u_qlate.rst_n = 1 (32 pins): ot_hdc_delay W=569 D=0 (QLATE=0) is a wire, rst_n has no fanout. Proven dead
  (opentallas.dead_inputs.v1, Yosys proc+opt in the ORFS image, dead_inputs.dead_bits; dead_qlate_proof.json, 16 per-type
  declarations). Validated in h3 (plan COPY with apply_plan_declarations + manifest dead_input_proofs): TIED 2,080 -> 2,048,
  nothing else changed. The plan owner applies the same declarations in the C25c event.
- sfucore u_store.u_output (ot_hgi_su_lgroup2 NS=2 NLW=16; 2,048 bits on 20 pins: rq/rr/ra/sw_*/s1_*): the parent RTL ties
  the unused read port and stage-write port to literals; the ports are LIVE inside lgroup2 (read port drives rd, stage
  writes drive the store), so they are not provably dead and are not ID straps -> RTL owner (drain-only lgroup2 form whose
  unused ports have no fanout, or a wrapper leaf). Not declared.

## (4) Lane list for DIE-HBM-14 (s1_unplanned_lanes.json; winner S1)
158 pairs / 179,387 b: IDX scorer 60 pairs/66,323 b (leaf W->E chain b100->b101 3,332 b, ge1 input b100->b102 2,777 b,
split leaves 1,146 b, tail ->root score 297 b, root->front 180 b, S-quarter hub->b000 4,986 b (plan has 304 b));
SU two-halves 38/67,878 b; SFU 24/23,536 b + SFU<->SU 12/6,672 b; other (pre-existing) 24/14,978 b.
Plan landing note: root->scorer (L80m 171 b, L124m 9 b) and score->root (L64m 297 b) land at b101; extend by hops.

## Strict bind now (h3 = best): 360 error lines (TIED lines capped at 200) = 0 unmapped + 158 UNPLANNED + 2,048 TIED bits
(u_output, RTL owner) + 1 EMIT (hcb native128 parent cut). Count of root causes: 3 (plan lanes, u_output ports, hcb cut map).
