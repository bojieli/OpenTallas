VMS known-legal write-enable route restoration — bounded candidate

ClockC baseline was DRC0, TT+60.88/FF-6.70, slew33/32. Its targeted i1
improved slew to10/10 but finished TT+51.89/FF-12.99(399ends),DRC1.
Periodic45/50/final reports show oneM4 spacing marker between bankA OBS and
net22261, with y103.788/103.308/103.980. Auto i2 remains the reference run.

Read-only comparison showed the completed i1 pre-DRT GRT checkpoint carries
EXACTLY the baseline DRC0 DEF route for net22261, same two endpoints,
masters and placements. Thus the DRT optimizer drifts an unchanged healthy
bystander toward bankA OBS. BaselineM4 via atx47.352 is safely west of the
macro edge47.616/OBS47.688; the bad markers sit atx47.663..47.688.
Image vms_net22261_review.png was viewed before the bounded candidate.

Source is latest i1 final, preserving its electrical progress. The Tcl restores
only that exact legal reference DATA route, locks the healthy wire22262
BUFx16f driver at its unchanged position/master, and marks that one data wire
FIXED. Canonical physical tokens (excluding stale RCX metadata) must equal
the exact reference. Both endpoints/master/position/type are guarded. No
clock net, endpoint phase, RTL, pin or cycle change. No gate exemption.

Candidate root /srv/opentallas-scratch2/claude/codex-vms-last1-1106 is staged
on Intel2 dedicated and E5 dedicated. Its kit/6_final.odb contains the change;
original current i1 failure remains on E5 and before_wce_restore snapshot.
Known reference source.odb is retained on Intel2 = completed i1 GRT; defparts/probe.json document
identity with baseline. Construction PASS unit2973539-1793978189.

The ordinary ECO uses existing OT_ECO_FROM=final (filler removal), selected
slew300ps/maxwire80,holdmargin0,--maxiter2,--keep,--lec. Maxwire80 follows
measured residual newly inserted wire236xx slew up to502ps after100 policy.
All clock geometry checks, actual TT setup0/FFhold25 uncertainty, full
DRV/DRC/PG/antenna/clock and actual routedLEC remain mandatory.
Only after physical PASS can it be adopted; original auto i2 stays untouched.
