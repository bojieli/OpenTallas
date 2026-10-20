# KPV lockstep K-tree infrastructure failure

`ot_qkh_ktree_lkp-lkp1-52f03a544` ended NEEDS_HUMAN after two route attempts. Both fail at CTS before the tile can be judged: `cts.tcl:6 invalid command name "ot_pg_install_unsupported_birth_guards"`. This is the shared PG flow dependency failure, not evidence of a tile timing or routing failure. Preserve the source and approved full-face pin layout; infrastructure recovery belongs to the shared closure owner. No structural successor is justified by this crash.

`failed_state.json`, route `flow.log`, `status`, `STATUS`, and `physical.json` are unmodified snapshots. `classification.json` records their SHA256 hashes and the original two crash excerpts. The original daemon state and run are unchanged by this evidence collection.

The behavioural miter passed 4060 lockstep edges and detected all 32 injected lane mismatches; the old-wiring mutant detects zero. Gate clock evidence passes with TT/FF pin-flop spread 7.6/7.2 ps. Existing review approved full N-face pins at 4.2 pins/um, 151.2 x 97.2 um outline, W clock, and GRT overflow zero. Route textbook lint separately warned of 369 reset loads on one internal reset branch; it is retained in the state snapshot and must remain visible during recovery, not silently waived.

Recovery is not closure: only CLOSED plus own-R native pin audit and the recomputed head_lane_perm qualifies this view for KV-GEN9 binding. Added latency remains zero for the unchanged design.
