Actual HC native source fragment and conditional bit screen

The parent is `dsfd_sp_hc_comb_native`; physical leaf signatures come from the exact closed peer TT models or the measured CCF v10 / pad R2 v7 models. The HDL elaborator uses `SYNTHESIS`, `OT_S81_HC_COMB_HARD`, and `OT_S81_HC_PAD_HARD`, keeping fourteen opaque actual physical leaf masters. It creates no whole-field producer, register, clock phase, or timing arc.

`source_joins.json` contains every internal bit join and all parent-to-leaf endpoints. The graph has fourteen real leaves, fifteen clock endpoints, 39 parent ports, 20,541 parent bits, 74 internal joins / 13,413 bits, and 86 external joins / 20,572 endpoint bits. `sk` is unused in the named physical mode; fourteen distinct `sk_leaf` bits plus the real sequencer `cck` port are required.

The timed 13,411 internal bits pass the owner TT setup / FF hold equations on actual pin coordinates with minima +90.8847 ps / +31.0819 ps. Two nonclocked bits have actual original routed database proofs: sequencer `c_fd[38]` is driven directly by TIEHI, and receiver `c_rv[4]` has no internal ITerm loads. The independent worst-bus screen uses maximum distance for setup and minimum distance for hold, yielding conservative minima +76.0 ps / +23.5 ps. Previous max-distance hold credit was optimistic and remains in historical receipts only.

The clock relation is conditional on the requested common boundary phi and each child's measured per-corner phi-R. Actual PLL/buffer producer-to-consumer mapping, related source phases, reset assertion/release and genuine final release acknowledgment are not bound. The per-corner controller boundary reference is recovered on 41 actual original routed CSEQ face registers; no all-register fallback or published view rewrite was used.

The packet is ready for native whole-field integration. It is not route admission, a released clock phase, a final routed view, a full-field timing proof, or a price ledger entry.

Reproduce the join extraction with `tools/s81_suhc/native_source_graph.py --graph source_graph.json --manifest manifest.json --out source_joins.json`. The generated `elaborate.ys` and complete elaborator log are retained. Reproduce the timing screen with `tools/s81_suhc/native_source_graph_screen.py --plan results/rtl/s81_suhc_20261013/native_repack_v7_v9/milp_r0_headroom_candidate_v10.json --joins source_joins.json --manifest manifest.json --proofs noarc_physical_proofs.json --out actual_bit_screen`.
