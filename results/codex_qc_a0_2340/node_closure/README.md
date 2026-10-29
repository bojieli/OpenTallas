# Native-CTS node closure

Exact physical kit: epyc2:/srv/opentallas-scratch2/claude/codex-qc-a0-2340/node_finalff.
Actual final ODB/SPEF signoff.py verdict SIGNED, all 12 checks PASS; routed native LEC
14420/14420 points PROVED, no different/undecided, superset all_shown true.
Independent NUMBER confirms standard-kit-frame TT setup +52.36 ps / FF hold +5.52 ps,
related pair worst TT33.08 / FF29.50 ps across133298 pairs/corner, DRC0/ANT0/DRV0,
PG317072 bound /0open. Raw FF SDC hold −34.43 is retained in the receipt; standard hold
uses the existing IO overlay in_min0/out_min−25 and measured pin-FF clock mean202.098481.
833ps /60–25 unchanged. Actual source/config/pins were unchanged through DRT continuation.

Original in-memory GRT FF−5.58581 FAIL remains preserved. Root cause was shared
RC calibration restoration overriding selected RC. Canonical fix a615f444b was staged;
fresh selected-RC GRT independently confirmed TT39.089066/FF9.732632 with no physical
repair and identical56548 clock guide rectangles, followed by the explicit DRT continuation.

Signed view: `../views/ot_qwen_tile_node` (export complete true, problems empty).
Routed LEC actual directory `lec_routed_autopilot_1793263816826000331`.
Initial export diagnosed lowercase bc filename fallback against actual ORFS uppercaseBC
scene. Exact actual final tc/BC ETMs were copied unchanged to canonical kit/views names;
normal exporter then completed. No timing model was rebuilt or fabricated.
Flow tag collection belongs to FLOW/root. TT<70 droop0.665INFO followthrough belongs to QC
owner and does not block use of the signed view.
