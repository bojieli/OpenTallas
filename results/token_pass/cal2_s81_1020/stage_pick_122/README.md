# S81 stage pick (LEAD10-S81, 10-20 18:20)
Pinned static layout (OT_XS_PAIR_ROTATE=0, QPAIRS 12), exact allocator capacity on ep9 codex-s81-stage124-1020:
- 122 frames (inventory sha256 9cce72c051efac39e14301f97c4415997dfce1ab41cd8aaba767da6165a308fb): f122_140 140/140 PASS (44 distinct specs, min q margin 56 words at exp_n113, production n104 margin 224), f122_148 148/148 PASS.
- 116 frames (inventory 76f391e7): req201 201/201, req212 212/212 PASS.
CHOSEN: 140 stages @ 122 frames. stage_map_f122_140.json sha256 f5608b1e5f2a122cb3b22b115d300df4809b75bf24fa65bf9d2ab1315ae96a8e;
static_capacity_receipt_140.json PASS: 560 layer dies + 32 copy-B + 52 = 644 dies (vs 888 for the 116-frame 201-stage fallback).
Requires the non-inline idx3 corner-strip readers (claude/s81-idx3r-1020, dv_plan --idxrd 4). Scope: capacity + identical layouts only; MU schedule and token chain still owed.
