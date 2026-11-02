# Original upper L730 window with a SU00 west gutter

PASS-COND for FT geometry in both SU00 types. Full plan remains BLOCKED by clock regeneration, selected native source/view joins, and internal relay bank placement. No adoption, P&R or STA.

The alternative retains B113 E and SU00 W paired windows at647.648..924.8147um. Move lanes_plain0_3 and pretree each +17.28um X, on the8.64um lattice, preserving both outlines and counts. This opens a25.92um west gutter. Allocate the same1663-bit L730 bus at the existing8 stages using seven actual internal FF banks along the west gutter and bottom street. All other FT banks remain reserved and unchanged.

Viewed upper_gutter_review.png. The banks form a clear registered west-to-south path around the canonical16 obstacles, without changing logical pin order. The two moved cuts stay separated. Red markers show four nominal internal relay homes moved into the new inter-cut gap; those markers are not actual placed FF-bank proof. Wide-bus layers, clock, reset, PDN and timing remain unqualified.

The real normal ot-run allocation passed both types in26.70s with484260KB RSS and no whole-bit fallback. Each type has32823 allocated internal FT cells overall, including11641 newly allocated L730 cells. Canonical FT macro-body gate has zero findings. Every FT body, row, frame and mutual overlap check passes. All native constructor internal hops are≤397.170um. All19 neighbor ports /16207 bits per type have zero mismatches or hops>405um; max383.053um. Canonical seams use the full source-pin + seam + peer-capture sum.

Moving the cuts requires translating12 internal relay capture endpoints per type. It newly covers four old nominal homes atx453.6; these are re-sited atx475.2 within the new17.28um inter-cut gap, preserving counts. Updated nominal relay hop maximum is401.76um. Seven pre-existing nominal homes lie inside u_sfu_Q0 and remain explicitly held. No selected actual internal relay FF-bank packet exists here, so nominal target checks cannot qualify those physical cells. Declared early clock entries attached to the two moved cuts are translated geometrically by17.28um, with native entry/profile validation held.

The lower-window clock profile is incompatible: actual explicit_taps rejected empty clk_t30 in BOTH types after bank relocation. Regenerate density and native clock/reset source joins; no tap-cap/radius waiver was used. The FT-only pass must not be routed with this old clock dictionary.

Current L730/L730m downstream natural latency remains45cycles; no additional FT cycle or FF is introduced relative to the lower-window candidate. The separate B113 source frontier remains FAIL / native view join HELD. Under the declared fixed cuts, the restored upper window needs at least2 additional aligned upstream cycles, versus at least3 for the lower window. Thus minimum total would be47 versus48cycles, saving one cycle /833ps and1663FF per B113 type. These are lower bounds, not an adopted programme, source change or physical closure.

Full retained candidate: /srv/opentallas-scratch/claude/codex-hbm-su00-upper-gutter-2310/collected/candidate_refined.json. Typed source-only objects and B113 bus delta are in this packet. Native source/view mapping, real internal relay banks, clock/reset and parent coherent R8/model joins remain required.
