# GEN2e4 quadrant channel candidate

Source: `11bf17f45` (run4). Owner decision LEAD3-HBM 10-19 22:57.

The GEN2d-only shift cannot apply directly: four HC centres collide with current GEN2e4 HCB banks. This candidate shifts each complete eight-bank HCB ring with its centre, preserving ring geometry. Thirty-nine slots move by exactly one 43.2um step; plan DBK/HC centres follow the original FP script. No active chain/source/grants were changed.

`review.py` verifies unmoved slot equality, outlines/Y equality, lattice displacement and all ring relative offsets. The shift script refuses partial HCB rings, repeated application, new slot overlaps and moved slots outside the die. Result: 28 inherited slot overlaps remain, zero new. `grant_shift_review.png` was inspected: quadrant rings retain contiguous seams and the NW/SW DBK gap grows. This is a grant-geometry review, not a placement/route PASS.

A fresh source-pinned GEN must use candidate grants/plan and regenerate stations/relay lanes. Do not reuse old placed relay positions or claim <=405um reach until fresh emitted-hop checks pass. Baseline case_a agent GO still requires its actual PNG. Existing S1 unread manifest is valid only for its exact recorded die identity.

SAFE checklist: 1 pin/reset RTL unchanged; 2 reach UNMEASURED pending fresh GEN/lanes; 3 fanout RTL unchanged; 4 depth RTL unchanged; 5 storage unchanged; 6 slot outlines unchanged, all moves 43.2um, zero new overlaps; 7 clock references unchanged, fresh native/die checks owed; 8 no schedule change claimed, reprice any changed emitted hop count. Label unclosed controllers/tails SYNTH stand-ins.
