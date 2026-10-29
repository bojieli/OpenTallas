# ASTK physical continuation parked 2026-10-29 05:03 PDT

Fresh native kit index0 pins1692/1692 preflight passed, source coupon4800 edges/0diff and4798 mutant differences. RTL unchanged by physical generator. Its mapped LEC remains live in intel1 astk_kits2/kv3_astk__190.08x181.44/lec; no equivalence claim yet.

Fresh own PLACE trial completed. Full graph r2r349.22um/0 bad captures; all1692 interfaces registered, pin-regp90 7.93/max12.16; fill45.8%, clock reach176.31. Initial actual column1.633 at E(180,47.5) held CTS/route.

Exact diagnosis: source-identified data input buffers were put in South controller region far from their own fixed face FFs, creating pin-to-South-to-face round trips. All xq face registers stay fixed. Plan relocates352 exact input buffers only, packed against all124987 original cells including TAP occupancy. All FFs/pins/nets/masters remain unchanged, no added cycles. New row orientations explicitly follow row parity. Actual DPL/check PASS with zero displacement; only352 buffers moved.

Actual final source-aware picture was viewed. Full data-only GRT50 probe completed0 overflow,122485 routed nets. Column0.802 is now WARN under existing measured-GRT0 rule; this is not a complete AUTO-GEOM pass because pin-table/macros/tap-set/stage metadata were not supplied. No CTS, clock-inclusive GRT, STA or SIGNED claim. Source-aware buffer placement must be integrated as physical ownership metadata if adopted.

Current own kit intel1:/srv/opentallas-scratch2/claude/codex-kv-kits-1029c/astk_inputbuf_trial1/kv3_astk__190.08x181.44. original_3_place.odb preserved; actual changed checkpoint inputbuf_oriented.odb copied to this own kit3_place.odb. Full dumps/sites retained locally and remotely, omitted from commit bulk. Source proof kit is untouched.
