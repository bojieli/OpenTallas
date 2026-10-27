# Argmax tree frontend diagnostic

Candidate constant-index generate processes preserve the production LP8/IW18 tree: same 33-bit keys, 32-bit payloads, lane capture enable, tie rule, and three registered reduction stages. No cycles added. Classic Yosys sequential lockstep miter proves 2016/2016 points; deliberately choosing the right lane unconditionally in stage0/pair0 fails. tree.sv contains the exact original and replacement mechanism.

Not adopted or READY: full current-kit new-gold/original-gate LEC runs in intel2:/srv/opentallas-scratch2/claude/codex-hbm-argmax-1027/lec_gen (tool codex/lec-0815@c337ef681). Original tool4 receipt had 34 differences (32 payload bits and two index low bits); a missing sequential index invariant remains plausible, so source shape is a diagnostic until that run finishes.

Terminal diagnostic: NOT EQUIVALENT, 20007/20602 proved, 595 differ. Many cones depend on unmatched constant cq_d fields; changing source process shape did not solve the production correspondence case. Do not adopt this candidate as a closure fix. Original source with 34 differences remains owned by FLOW/LEC. newgold_oldgate_failure.json preserves this failed receipt.
