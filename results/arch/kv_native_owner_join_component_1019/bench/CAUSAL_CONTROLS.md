# Nine causal source controls — not yet executed

Source script make_mutant.py materializes exactly one functional source mutation from a frozen complete hash manifest. It copies only manifested sources, refuses existing outputs and wrong anchor counts, changes one source, rehashes it and records source SHA, scenario and required named failure. No simulator is launched by the script. A control is caught only after the SAME baseline stimulus passes and the source mutant fails its named runtime invariant; generic timeout and process status alone never qualify. No caught claim is made here.

| Category | Source change | Genuine source/interface stimulus | Required witness |
|---|---|---|---|
| Epoch | Exclude epoch16 from join certificate-key equality | Case10 corrupts epoch only on real scheduler certificate event at private join input | CORRUPT_CERTIFICATE_WAS_ACCEPTED |
| Generation | Exclude native generation2 equality | Case11 corrupts generation only on same real event | CORRUPT_CERTIFICATE_WAS_ACCEPTED |
| Stage | Exclude stage6 equality | Case12 puts request stage0 in the actual terminal37 certificate input | CORRUPT_CERTIFICATE_WAS_ACCEPTED |
| Input vs next | Exclude input-token18 equality | Case13 substitutes independently known returned next token on real event | CORRUPT_CERTIFICATE_WAS_ACCEPTED |
| Client substitution | Capture zeroextended clientTAG as native TAG in actual join active record | Case0 real wide native key differs from descriptor client | BOUND_KEY_IS_NATIVE_TAG59 |
| Latest pending owner | CQ B compares old saved event to latest pending tuple instead of active native owner | Case3 actual next unbound issue coexists with old saved CQ B stall | HEALTHY_SOURCE_FAULT; must also show real pending overlap |
| Merge rank masks | Result credit accepts any rank return instead of all8 | Case14 stalls actual rank7 opcode4 transport ready while all other7 real return packets are accepted | ENGINE_CREDIT_BEFORE_ALL_RESULT_RETURNS |
| Early POST | Drop actual CQ-observed POST gate | Case3 delays real generated CQ word0 B | POST_BEFORE_REAL_CQB |
| Raw cleanup | Existing retained endpoint RC_MUT2 gates actual retirement on health bad | Case4 real health fault after all actual requests; real result and drains still arrive | RAW_CLEANUP_HEALTH_VETO |

Cases10..13 are explicitly negative private-interface metadata corruption. Their events come only from the real scheduler/source certificate event; allocation, HC, rank requests, credits and terminal result stay genuine. Source gold remains submitted descriptor/known engine environment, never DUT mirror/latest grant. Original join must detect the malformed key; the corresponding weakened equality must fail that detection assertion. These are bounded component predicate controls, not a production fault injection/health-coverage claim.

The latest-pending control deliberately misjoins a real old event to a real next UNBOUND step. It never invents a next native allocation while POST blocks admission. If the selected source does not actually create that overlap, report NOT_CAUGHT and retain the trace. Case14 must independently pass before a rank-mask mutant qualifies. It records endpoint result credit separately from actual accepted transport return and engine credit; the held packet remains valid and byte-stable until real ready. No drain/credit predicate is merged. The pipeline cleanup bound6 component edges is conservative against actual endpoint input/result/seen/retire captures; validate baseline4 first and preserve any failure.

Duplicate clientTAG/busy and bad-op descriptors plus active-owner failure are a separate required runtime case7; they retain independent descriptor owner_gen2 accounting. Reset/PLL source reachability, full primitive health, production H/calendar, actual phase/CDC and physical SRAM/PG remain open.
