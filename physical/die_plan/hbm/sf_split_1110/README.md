# SF-SPLIT 11-10 (HBM-COLLECT-1, COORD form b): east/west split of ot_smh_static_front

The SF-C structural form of the 1814.4 x 233.28 um front core routed NOT SIGNED (TT -322.97, FF -589.6). Its hops are
about 600 um, which breaks the 450 um rule. This plan event cuts it into two 907.2 x 233.28 hard cores.

* Cut at x = 907.2. Both halves must be at most 907 um, and that forces the cut here. On the SF-C placement every net
  crossing x = 907.2 is driven by a flop (4551 bits). No unregistered port feedthrough crosses it, and only 147 comb
  cells are duplicated (each is copied to every side its cone reaches). A greedy flop-level min-cut moved 10 flops,
  leaving 4541 seam bits: seam_w2e 3054 and seam_e2w 1487. The seam is launch-registered and adds 0 pin cycles.
* `split.py` (OpenROAD python on SF-C 1_synth.odb + 3_place.odb) writes the W/E gate netlists and the composite
  wrapper `ot_smh_static_front`. The wrapper keeps the original ports, so the parent RTL and pins do not change. Each
  half's buses are compressed to its own bits; the maps are in pinmap.
* `proof.py` is a structural netlist equivalence check. It parses the files independently. For every cell input pin
  and every output port, the composite driver must equal the gold 1_synth.v driver, and every gold cell must exist
  with the same master. Result: EQUIVALENT, 228297 gold cells, 147 duplicate copies, 0 multi-driven nets. A mutant
  that swaps 2 seam bits gives NOT_EQUIVALENT with exactly 2 driver errors.
* `mkkit.py` derives the two half kits from the SF-C kit:
  * pins: outer pins shifted per half; seam pins on M4 (2-track spacing) plus M6 at the shared edge, with equal y in
    both halves;
  * seam SDC: launch half 200 ps, receive half 633 ps, so the two sum to the 833 ps period; -min follows the kit
    contract;
  * clock sites, face flops and freeze/core/sdc_lint json split per half.
* `apply_event.py` applies the event to a copy of the wave plan (plan_r2_restore -> plan_sfs1110), in the
  hard_cores, clock taps, clock_entries, core_clock_regions and core_macros of q_sm0..3.
