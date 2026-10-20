# SM9 +2 compute / spatial gather packet — pre-gate MODEL

Source364f635c3 adds default-OFF OT_SMH_G1_MASKPIPE, only in the existing
OT_SMH_G1_CAPTURE opt-in. G1 now captures both producers and eight select copies,
registers both masked branches, then ORs them. All254FF are compute state;
there is no appended pure result FF padding. Prior +1/gout+4 behavior remains
unchanged when the new define is absent. +3/gout+6 was not implemented.

Four north gather100b registers are genuinely spatial reach relays, including
the existing input capture. Total400b pass state (+100b vs prior+1); all added
state254G1FF/leaf (+98) and north100b relay totals+296FF vs prior +1. There is
no indexed store or new >2kb array. They must remain physically distributed:
co-locating the four registers would violate the storage rule. Exact590/320/140
station centres use40x8um boxes, with20um+ macro clearance in the two low bands.
The supplied hook groups100FF/station and fails mismatched counts; it is NOT
bound to a gate kit yet. The existing io_flop_at_pins hook anchors first capture.

Actual immutable closed-master geometry, including orientation and required
MX Y phase, is native_master_phase.json. Every base anchor is43.2*k. MX legality is BLOCKED: none of these immutable LEFs declares SYMMETRY.
orientation_legality.json includes exact SHA and headers. Track transforms
do not prove that MX is allowed. The conditional phase exception is NOT
admitted until legal orientation evidence or premirrored native views close.
The ONLY
physical offsets are +0.024um Y on MX XS/row/beat masters whose immutable LEFs
have off-track pins at the base and zero off-track after offset. TCL/TCT/BDC
remain unshifted. All master SHA256 and old/new native track counts are included;
all_master_pins.tsv gives every SIGNAL/POWER/GROUND rectangle in actual global
coordinates. No LEF or pin relocation, rounding, or at_exact camouflage occurs.

The north PNG is personally inspected and explicitly a PLAN, not placement.
It includes the OLD302.4-wide XS child, which cannot be a final release binding.
The real XS475.2-wide lattice successor is being physically measured separately;
its eventual closure requires SM frame re-plan before a release gate/adoption.

SAFE-DESIGN checklist:
1 Pins PASS source: same registered producer/pin interfaces, two-stage parent
reset landing, raw reset1direct/1firstFF. II1, tag/valid/fault and reset preserved.
2 Reach PASS for north gather planning only: every corner-pair Manhattan bound
383.36/368/228/257.6um (<405). Boxes vs exact actual macro rectangles:0overlap.
The XS blocks a straight stage2->3 wire:100 planned tracks x347..366.008 in
the real E corridor require<=380.016um worst routed Manhattan dogleg. Stage3->4 similarly detours in TCL centre gap x305..324.008,
max338um, and final hop goes E of TCT x414..433.008, max257.6um. Complete
leaf/internal/south/parent linked-pin and placed wire reach are STILL OWED.
3 Fanout PASS actual native mapped: north13830FF/9macros, south8042FF/7macros,
all non-clock drivers<=32 INCLUDINGRESET, findings/refuse empty, no waivers.
JSONs ../g1_mask/{north,south}_census32.json; this is counts-only, no faulty
read_liberty sequential behavioral model proof is used.
4 Depth PASS actual mapped:50ps both halves. Three real G1 compute stages;
no new arithmetic long cone. Keep hook preserves eight source select copies.
5 Storage PASS MODEL:254FF G1 compute,400b physical distributed GN relays;
no new indexed runtime arrays. All state/capacity counted above. Placement
must enforce the spatial hook rather than temporal padding.
6 Geometry BLOCKED: absent immutable SYMMETRY prevents legalMX admission;
current closed-master stand-in transformed pin phase is explicit/proven,
macro channels and relay boxes shown. Full release XS child/frame geometry,
pin-face reach and PG/cell access still owed; this packet grants NO gateGO.
7 Clock PARTIAL: original single root/regional clock contract unchanged,
no phase/interface change. Actual TT/FF spread/insertion/PG unmeasured.
8 Schedule PASS source: full original independent legacy RTL +5 age proves
12796 comparisons after800 warm; 4000cycles, Verilator5.050. Primitive4093
checks includes invalid junk/collisions/reset reassert; early-valid mutant
FAIL1564, lost-fault mutantFAIL1379. Direct RTL only. II1/edge counts uniform
all gout lanes, no compiler binding changed. Measured +2 price DS1095records
+722cycles=0.125038% loss; Qwen5records+290cycles=0.0228453%.

Proof receipts are ../g1_mask/. No physical gate, REVIEW.json, submission,
compiler age change or shared arithmetic source adoption accompanies this packet.
