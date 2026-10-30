# HH per-bit plan allocation, unchanged 18/21 cycles

This is an **unadopted plan candidate**, based on the seam-aware plan in
`../hh_seams`. Its six new slots retain their exact widths and station counts.
The candidate lives on intel1 at
`/srv/opentallas-scratch2/claude/codex-hbm-1030/hh_firm/resample_plan.json`.

The allocator reserves all existing explicit FT footprints and all hardcore
bodies plus their 4.32 um halos. It adds 80,712 internal (`k-1`) FF sites,
including every epoch bit, with the established 1.404 x 0.27 um envelope. These
sites do not overlap one another or existing explicit sites. Stage zero retains
the existing input-pin convention; this is **not** an actual native all-stage
FIRM placement. The new sites are at least 481.707 um from existing internal
station group centres (922.413 um in root); those groups have no nearby homes.

Equal arclength sampling of the shifted station paths clears the unchanged
405 um plan rule: the six maximum per-bit hops are 302.94, 293.49, 316.98,
313.47, 401.76 and 379.35 um. The full FF-to-pin-to-pin-to-FF scan covers all
22,284 bits of the eight physical seams, using actual pin tables, bit indices
and instance orientations: max 399.577 um, zero over 405, zero pin mismatch
apart from numerical roundoff. The 401.76 um maximum leaves only 3.24 um of
plan reach margin. No physical timing closure is claimed.

The `bad_hops` field in the allocator diagnostics counts the deliberately
conservative 364.5 um target, **not** the formal 405 um rule. It therefore still
reports 682 bits in two east-bank slots. No rule or threshold changed.

Failed alternatives are preserved. Simply shifting centre paths gives maxima
up to 526.049 um. Forcing every bit into the outer-corner corridor crowds
shared row neighbourhoods, producing 747 allocation misses and maxima over
405 um. These are failures of those constructions, not infeasibility proofs.

Replay `allocate_hh.py ROOT BASE_PLAN OUT_PLAN OUT_REPORT resample` using a full
checkout. `seam_bits.py ROOT OUT_PLAN OUT_SEAM_REPORT` checks the new seams.
The same allocator's default and `corridor` modes reproduce the failed controls.
Jobs used ot-run on intel1, 8 GB/one thread, units 900206, 926542, 945690,
994539 and 1018085; all are terminal.

LOOK: `results/geom_review/codex_hbm_hh_perbit.png`. The clouds stay in the
root street and the bank outer/bottom corridors, clear of the pictured macro
halos. PASS-COND for this plan geometry only. Full native FF names/masters,
all-stage placement via the shared `ft_full_stage_placement_file` facility,
actual FIRM legality, clock/reset/START, PG and capacity, G1, routed TT/FF and
all remaining die gates are still required before release. No P&R was launched.
