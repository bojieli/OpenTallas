FT full-stage mechanism: read-only native OpenROAD check against S81 owner's
legalized IQF coupon. Source ODB:
intel2:/srv/opentallas-scratch2/claude/codex-s81types-1030/iqf_coupon_movable/legal.odb
Targets: same directory /iqf_ft0_targets_legal.json (all6726 FT0 cells).
Own diagnostic: intel2:/srv/opentallas-scratch2/claude/codex-flow-ft-endpoints-1030/probe/

Positive runtime check accepts all6726 exact cells, actual six-stage bit chains,
actual core rows/sites and fixed obstacle clearance. Owner's independent DPL
coupon:0 placement errors; FT0 maxhop402.570um, pinp9028.059um,
pinmax30.423um;0 addedcycles. Remaining four actual r2r failures are reset-only
and owned by S81. FT1 landingREAD reservation is separate; no FT1 normal override.

No physical job or route was launched by this source work. This mechanism and
coupon do not claim full G1 or timing closure. Probe writes no ODB and its
validate-only flag skips placement/log mutation. Runtime negative controls and
focused generator controls accompany the source.

Final native negative controls: WRONG_MASTER rejected before placement; swapping
actual names/masters/sizes across stages rejected as stale chain ft0/0/1;
placing stage0 bit0 at nearest legal-row tap site rejected specifically for
TAP_TAPCELL_ROW_1112_40772 overlap. Log probe_final.log. All probes read the same
ODB and run validate-only; no DB writes.

Focused source checks:50 tests plus6 subtests pass across full-stage, old bit-site,
abstract station-wire and G2 tests. One old standalone station helper initially
failed because it calls with Plan=None; optional reader now preserves that legacy
interface and the focused suite passes. Ordinary kits remain unchanged when the
new per-type field is absent.
