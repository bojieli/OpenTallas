# DIE-KV-31-SRC VDDPHY-interface source rebuild review, 2026-10-29 10:00 PDT
Inputs identical to DIE-KV-30-SRC (claude/die-kv-30-src-1029@51516afac) except kv3_sys_c_part.lef: CORE VDD M7 cut at
phy_sys_c_ucie (+0.096 um gap), 92 VDDPHY M7 pieces inside (pg_regions.prototype_lef; signal pins + OBS asserted identical).
Readback CHECKED (receipts/check_native.json vs DIE-KV-30 check_new_native.json): every field equal except
masters.kv3_sys_c_part.pg_pin_shapes (VDD 294->386, VDDPHY 0->92, VSS 295). Fresh constraints byte-equal except source sha.
Preflight of the same proposal_open placements: READY_FOR_REVIEW, 0 issues. Geometry review of placement inherited
unchanged from DIE-KV-30-SRC review.md (block/clock placement unchanged, PG-pin-only master change).
PASS-COND for provider import. No timing, PG, IR, routed or freeze claim.
