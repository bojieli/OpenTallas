# XS4 n4 plan review, Codex takeover 2026-11-13

Candidate plan a4dab645c7d2; inspected the actual PNGs rendered by rtype.py:
- epyc7 /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/n4_png/c1x_C__t3.png
- epyc7 /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/n4_png/c1x_C__t8.png

The xf bank wall is broken 3+2, giving a full north-south corridor into the centre band. XS4 capture pins face the xring band. Cap, egg/egn/egn and xr sit in distinct bays. The t3 north-only ft0 follows the east boundary; t8 ft0 follows a perimeter and bottom-of-XS4 path. Long leaf lanes have declared station points. No outline change from m4. Clock taps are distributed in clear channels; PDN continuity is not established by this plan image.

Verdict: PASS-COND for private placement proof only. SMELLS requiring the placed proof: dense north-face buses; t8 ft0 corner/access at XS4 south edge; high signal demand around egg/egn and station landings. No detailed route authorization or sign-off claim. Core r2 was already running when taken over; view place density and congestion before any newly launched continuation.

The existing old-wave ft0_i pin_unreg proof is a reporting-depth issue: all 277 bits reach four actual u_cland_ft0_i/u_ring.s_d captures. Forty-one bits fail the generic six-cell cone traversal because buffered mux cones are 7-9 cells deep. This is not evidence that input capture flops are absent. Actual pin-to-capture distance remains to be measured on the new layout.
