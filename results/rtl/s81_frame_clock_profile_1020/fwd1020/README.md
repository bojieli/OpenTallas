# Frame clock profile after the relay ck->ck_o re-export (S81-FRAME5, 10-20)

Codex's auditor (codex/s81-clock-profile-1020 bdb6d78cb, tools/s81_dv/frame_clock_profile.py, unchanged) re-run
on its own source tree with ONLY the three dsfd_dvrly_276_NS Liberty files replaced by the re-extracted view
(this branch, 7ae5c05ef). Before: h9/h10 REFUSED (ck_o SELF arcs, no ck->ck_o). Now: PROFILE_ONLY, 0 errors,
0 source-lineage errors, roots=4, child clock pins 8/8. SDC emitted at 833.333 ps.

PROFILE_ONLY is not a qualification: parent TT/FF propagated clock at the 8 child clock pins (linked u_cf/u_xo
spread <= 80 ps) comes from the frame gates (claude/s81-frame5-rffwd-1020 f9d44ffae), and the K/reader-phase/
reset-first-edge certificate is the die compiler's.
