# S81 core kit placement review

Image personally viewed: results/codex_s81_ce12_1029/core_plan_review.png.
VSW source-template image was also personally viewed; its newly discovered
0.024-um SRAM gap fails the physical channel gate, so VSW is held for revision.

PASS-COND for ONE placement only of rxsf, ve_m, ve_s, vn_a, vn_b and vs.
Their fresh ce12c kits have normal-generator reset64 staging, with preflight
PASS, zero issues. No CTS, GRT, route or sign-off is approved by this record.

The VN masters each have one SRAM with open logic channels on all sides.
The other four diagrams have no hard macro walls. Wide data buses occupy the
frozen parent-facing edges. RXsf is small enough for the NE clock entry to
reach its full outline. VE/VN outlines are near 2:1, so actual local paths and
clock delivery need inspection after placement. VS is square with all four
faces used. Pin density, stage reach, macro interface capture, reset, clock
balance and PDN continuity remain actual placement obligations before CTS.

Earlier diagnostic ce12b kits with manually staged reset records are not
submitted. Current ce12c uses the normal validated reset-contract staging
from f30b48c15, with the repository's exact receipt and module qualification.
