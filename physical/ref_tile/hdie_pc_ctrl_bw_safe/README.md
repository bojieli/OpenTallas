# HBM-BW safe successor, synthesis diagnostic

Opt-in `ot_hbm_svc_pc_ctrl_leaf_cfg_safe`; released masters unchanged. Coordinator authorizes conservative 432x475.2 outline and low-fill waiver from 13 stock SRAM macros plus 43.2 lattice and >=20um channels. Source model is results/rtl/hbm_ds_layer_tput_1018/hbm_bw_safe_1019/model.json. New slot is 0.2052864mm2/PC versus0.0241865mm2 for155.52-square h9c; integration must price the actual delta before adoption.

SAFE checklist before synthesis:
1. PASS: existing K/response/PHY input and output pin registers preserved; two-stage flow reset landing plus RTL relay. Added two reset-release edges are startup only.
2. CHECK AT PLACEMENT: macros at43.2 lattice; boundary-to-register reach and long internal routes must be measured <=405um; outline width432 and height475.2 require placement evidence, no reach waiver.
3. CHECK AT SYNTHESIS: queue storage removed; control fanout must be measured and replicated if >32 in critical cones. Validity-gated row and metadata data registers are reset-free.
4. FIXED:64-entry oldest-first scan removed; per-bank summary with two-stage grouped ACT selector. Refresh argmin is now five registered balanced binary stages, one7-bit comparison/stage; replaces serial32-way reduction. Check resulting depth at synthesis.
5. PASS: all >2kb indexed metadata and identity FIFOs use real128x256 SRAMs. Four write banks with two read replicas, two identity stores, one AQ metadata store, write and response payloads =13 macros. Summary arrays are each<2kb.
6. FIXED:432x475.2, aspect1.10, macros at[43.2+129.6col,43.2+86.4row], >=34.7um horizontal and45.3um vertical channels. Low fill explicitly accepted by coordinator for this macro/channel bound. Actual std area and location are to be measured before CTS gate; preserve one connected full-width standard-cell band.
7. CHECK AT CTS: spine clock; io_hold_margin0.03. No insertion-based rejection; require <=80ps TT/FF pin-flop spread and native neighbor-matched boundary.
8. CONDITIONAL: ACT lookahead +2edges and refresh-key selection +1edge operate before fixed service go. Controller pre-update SAFE stream measured93.02-94.22B/edge (within10% of98.9) but updated source must rerun; production exact-slot and mutants required. New geometry area and full-token descriptor pace are adoption blockers until priced.

No route submission or release bind from this diagnostic kit. Clock/signoff rules unchanged; no data false paths or multicycle masks.
