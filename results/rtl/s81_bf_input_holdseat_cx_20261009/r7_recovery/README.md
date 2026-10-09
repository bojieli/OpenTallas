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
Fresh CTS TT/FF measurement and a route handle remain pending; no routed
closure is claimed. Original work remains at remote
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
Fresh CTS measurement and actual route launch remain pending.
