# R7 actual same-job recovery

Confirmed review-0400 R7 authorized correction immediately. Fleet archived
all attempt1 work, scripts and logs, then retired only the named worker and
its matching container. Native source c674dadfd unchanged. Attempt1 exit143
is operator retirement, NOT a natural terminal timing failure. Floorplan had
advanced to final metrics immediately before retirement; complete log kept.
Twelve gates resized by iteration14; later iterations had no additional
moves. Earlier "zero moves" shorthand means this later stagnation, not a
zero cumulative resize count.

Same job bfk_recut_hs4_sm15-c674dadfd-tc-cx attempt2 actually launched on
EPYC1 at04:11:26PT: launcher3677814/driver3677872. Actual MANIFEST and
argv in attempt2_launch.log prove both --ins-ss and --ins-ff are
701.5540326188421ps. Only calibration command seed changed. No buffer-
removal switch, new RTL, clock, uncertainty or route I/O relaxation applied.
The standard installed REMOVE_ABC_BUFFERS knob changes netlist topology;
it was inspected and not used. All6688 explicit HB2 masters are present in
the original full native mapped netlist with keep/dont_touch attributes.

Clock730ps, headline833.333ps,60/25ps uncertainty, CG0/SEATS4/SM15,
The predecessor calibration estimate was 6.4 GiB; actual attempt 2 global
placement peaked at 7,659,984 KiB, with sampled whole-job RSS 7.40 GiB.
Fleet was notified to account for this measured growth without restarting
the run. The measured predecessor route envelope remains 39.0 GiB.
Fresh CTS TT/FF calibration completed successfully; a route handle remains
pending and no routed closure is claimed. Original work remains at remote
routes/bfk_recut_hs4_sm15_c674dadfd_tc_cx_cal.attempt1_R7_preserved.

Actual generated a2 1_synth.sdc now verified: clock730/setup60/hold25ps,
inputmin701.6/max951.6ps, outputmin-751.6/max-451.6ps. SHA256
 dceb877326b53453e5144be76f0ef2c89b7b7cc481005a227373a31ea1ebd85f.
The tiny rounding follows the unchanged native io() serializer policy.
The floorplan, macro placement, tapcell, PDN and global placement stages
completed naturally. The final floorplan WNS was -416.905 ps under the
provisional insertion constraints; this is not a routed verdict. Their raw
logs, JSON metrics and remote output hashes are retained in the attempt2
subdirectories. The same driver advanced to resize-stage metrics.

The admitted read-only HB2 audit passed against the immutable completed
3_3_place_gp.odb: all 6,688 original instance names retain the exact
HB2xp67_ASAP7_75t_R master and OpenDB isDoNotTouch protection. Mapped
keep/dont_touch attributes are present for all 6,688; missing, extra,
master-change and protection-change counts are zero. The completed ODB
SHA256 is bc2aad38908ac3e254235c74081682d8f4ee0134245cb1c1113a5b4b799c111b.
Input hashes matched before and after the audit. Full inventories and raw
receipts are in attempt2_hb2_audit. The E1 audit wait never admitted and was
retired with its receipt preserved; the single audit ran on EPYC3 through
its 8 GiB guard, exit 0, peak 872,920 KiB, elapsed 12.65 seconds.
Calibration attempt 2 completed with exit 0. The immutable final wrapper
script, log, exit and environment are in attempt2_final_calibration. Raw
placement-estimated CTS boundary insertion (mean/min/max) is TT
805.7/792.8/817.5 ps and FF 663.4/651.9/673.5 ps; the route environment
rounds these to TT 806/793/818 and FF 663/652/674 ps. The route reference
is actual TT. SS 1032/1017/1047 ps is sensitivity evidence only. These
calibration values are not a routed timing verdict.

CTS completed in 10:07.93 with peak 6,459,452 KiB. Its completed database
SHA256 is 24591526639237dfab044a90eeb187142b8d9ca953acae16c6a9987a563fcb92;
4_cts.sdc SHA256 is e4a92eaf3982450e86a60e7de728469d4933e9e1c0af9f3d2690a070de007fe0.
Later placement and CTS raw logs and metrics are preserved in
attempt2_completed_place and attempt2_cts. The authoritative job state
now carries owner-approved conservative accounting of 9 GiB calibration
and 44 GiB route, distinct from measured peaks and not process caps.
EPYC1 is below its existing disk admission floor. Before a planned route
transfer, the daemon relocated the job to EPYC4 and repeated calibration
attempt 2. The completed EPYC1 calibration remained intact. Root authorized
retiring only that redundant calibration after verifying equivalent
source, constraints, libraries, tool image and no active route worker.
All 58 selected source/driver/macro/LEF files, generated config, SDC and
hooks matched byte for byte; the recipe differed only in HOST and run-root
relocation. Original and normalized verification receipts are retained in
attempt2_duplicate_equivalence.

Fleet performed the conditional recovery under the named lock, preserving
the EPYC4 attempt/work/logs and retiring only the matching launcher,
driver and container after process-start checks. The completed EPYC1 env
and JSON were copied and hash-verified. The same job is now READY at route
stage 1 on EPYC4 with the approved 44 GiB admission allowance. The operator
receipt is in attempt2_verified_cal_reuse. No manual route launcher or
daemon code edit was used.

The daemon launched the approved same-job route attempt 2 on EPYC4 at
06:37 PT: launcher/PG 2082039, driver 2082088, container bf39027a4b20.
Actual script, process identity, MANIFEST, generated config and SDC are in
attempt2_route_launch. Source remains c674dadfd, CG0/SEATS4/SM15,
route period 730 ps, headline 833.333 ps and uncertainties 60/25 ps.
The provisional route arguments are ins-ss=806 and ins-ff=806, as required
by the existing single-SDC route policy. They are not the final FF timing
reference. The launched MM configuration reads dynamic signoff_ref.sdc
in the FF/BC scene and then the copied routed-reference IO helper; it
queries actual PINREG clock arrivals and applies the unchanged H1 IO
policy. Effective WC setup uses TC libraries/TT macro; BC uses FF
libraries/FF macro. Copied scripts, hashes and trace are in
attempt2_route_launch/dynamic_signoff. No launch mismatch, constraint
change or restart is needed. Route timing and DRC qualification remain
pending; actual route launch does not claim physical closure.
