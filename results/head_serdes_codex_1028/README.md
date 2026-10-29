# HEAD SerDes natural hardening

Source-only implementation replaces no arithmetic and adds0 cycles. The real source has one512-bit KP4 codeword link. COORD approved hardening the existing `u_phy.u_link.u_dec.u_chn` child rather than cloning six digital links from the physical-lane note.

- Smallest Chien lockstep/mutant PASS:732 comparisons,64frames,64 real omitted-Forney-division mutant divergences (`exact1.log`).
- Candidate-plan safety tests:6PASS, including retained SRAM/pad/source bindings, overlap/MUT/M9 rejection and portable pin-table paths.
- Actual child synthesis:190,283cells,21,598.185um2 in216x194.4um (51.4%fill), under400k/run. Cell count is a local measurement, not independently checked.
- Typed internal endpoint census PASS943/943;159 unused internal standard-cell outputs inventoried (`endpoint_census.json`). All actual endpoints remain timed; parent hd_serdes still owns its R2 boundary.
- KIT_PREFLIGHT --contract PASS0 issues (`preflight.json`). Viewed pin/clock layout PASS-COND for trial placement; actual placement/clock/timing remains pending.

Failures retained and diagnosed: gen1 sparse setup omitted `physical/common_flow`, fixed by adding that tracked directory. Gen3's driver postprocessor assumed a legacy `plan_pins.json`; typed source-profile generators instead retain the original pin table, now handled by materializing actual IO pin centres. The original strict face gate FAIL943checked/545ok (`strict_face_failure.json`): GF transforms precede existing input registers, k_v fans out, and apply outputs alias the same sequential value. The canonical typed INTERNAL_CORE census correctly checks this existing internal timed cut, with no added face shell or timing waiver.

Jobs on intel2 under `/srv/opentallas-scratch2/claude/codex-head-serdes`: exact1 and gen4 COMPLETE; original kits2 strict gate FAIL retained. Successor kits4/ot_s81_kp4_dchn_head reuses the identical4RTL files/config/SDC/IO/tracks/PDN and completed synthesis. Canonical place flow is live on epyc2 (ot-run spill, unit oth-ubuntu-2780044-1793257634, container hbmcore-ot_s81_kp4_dchn_head_-2780097), checking typed endpoints+LEC before placement. `place2.otrun.log` on intel2 collects the job.

No real physical child views or SIGNED claim yet. Next: collect LEC/place, view actual layout, then enqueue the reviewed core through autopilot; integrate only actual supplied views into hk4 via `head_serdes_core_delta.py`, re-synthesize the parent to establish its actual build cap and re-run parent/die timing.
