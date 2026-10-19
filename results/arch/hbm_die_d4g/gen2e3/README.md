# GEN2e3 (L2H-GEN2E, 10-19): GEN2e2 + structural unread fixes as hardware

Base: GEN2e2 pre-relay (codex strict l14-l19, IDX256 programme-depth guard l19 kept, contract fd7492f2).
Layers (all fail-closed, source-only until synthesised in S2):
- l20c calendar role width (epcal/vmfc): 1,045 b capacity tail removed (LH-UNREAD F-C 16ff93f38)
- l20p IDX256R collar packed operand face: 771 b (F-P 3fe6046af)
- l20t HC chain-terminal banks hcb_<q>7: 116 b (F-T 4418ce6ff)
- l20s selected-only IDX selector `ot_hbm_idx_selector_static_sel`: 2,444 b (out_v/out_line/threshold_observe/selected_observe
  and their 4,816 flops removed; op 8 raises the sticky fault; production compiler never issues op 8)
S1 strict bind: structural 0, unread 70,320 -> **65,944** (65,066 = entries of the ROOT-reviewed manifest 2beccb8e transfer; 878 open);
functional bind PASS 1284 paths (`s1_port_bind.log`, `s1_functional_bind.log`).

Selector benches (Verilator 5.050, fleet ep7, `tools/hbm_die_v16/idx_selector_sel_bench.sh`):
- link SMUT0 PASS: canonical full-shape gold bench (3 frames x 512 records, 963 fixed edges, first TX 833 = canonical receipt)
- link SMUT1 (threshold mutant) FAIL witness; eq SMUT0 PASS (selected_v/line/fault every cycle vs canonical shell + op 8 fault);
  eq SMUT3 (op 8 fault dropped) FAIL witness.  The eq tb's hand-built production stream raises the canonical's own fault in
  run 1, so the gold link bench is the equivalence evidence; eq adds the op-8 behaviour.

SAFE-DESIGN (selector_sel): 1 pins PASS (kept pin flops, 2-flop reset) 2 reach PASS (port subset, same slot) 3 fanout PASS
4 depth PASS (one 4-bit compare into the fault flop) 5 storage PASS (12 SRAMs unchanged, 4,816 FF removed) 6 floorplan PASS
(soft SYNTH block, smaller face) 7 clock PASS (single clk_ctl root) 8 schedule PASS (no cycle changed).

Chain `chain_d4g2e3.sh` runs in parallel with the GEN2e2 resume (`../gen2e2/chain_d4g2e2_s3.sh`); SYNTH views are labelled
stand-ins (never closure).
