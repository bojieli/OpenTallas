# Signed lane clock access at the P8 parent site

A historical attempt-22 routed log on epyc7 records DRT-0073 at u_bound.u_u_ln0/ck[0]. The sealed watchdog exit 137 was recorded separately. The a22 and P8 kits emit the same ln0 MX placement at (8.748, 648.036) µm, tracks, M5 pin geometry, and M2–M8 signal and clock routing limits. The two signed abstracts differ only in M6 above the buried clock pin. The a22 macro has a blanket obstruction. P8 opens a 2.048 × 2.528 µm window and retains five internal M6 obstructions.

The transformed M5 clock pin spans (156.672, 856.236)–(156.720, 856.764) µm. The reviewed image shows no uncovered M6 track intersections in the a22 abstract and eight geometrically open centers in P8. A one-net probe used the entire original signed abstract at its original site and orientation, in a die of the same size. OpenROAD pin_access returned DRT-0073 for a22 and produced six verified access points on ck[0] for P8. Their die coordinates are x = 156.696 µm, y = 856.288, 856.352, 856.416, 856.480, 856.544, and 856.608 µm. The fixture used the pinned project image with SHA256 starting 2d12164ad3f6.

This result measures the signed macro's intrinsic access. The fixture contains the macro and a parent port on the same net. Parent PDN, surrounding cells, other nets and their routing were outside the probe. The current P8 proof remains limited to placement. The saved e7 and p8 logs retain both results.

| Artifact | SHA256 |
|---|---|
| Attempt 22 signed macro LEF | 7dd372f620449413c670bf693fe160917de2f24f6d985ca14c7d21ebc409be63 |
| P8 signed macro LEF | ea957b8472c634a82ed62dc0a504296443393c9ba5ae0b459f6196b1925dd420 |
| Shared track Tcl | 7020f2b9fe3ebdb6a680f8cee3e4772db4c5c5372cde68414ba88dbfe520a341 |

The complete self-contained fixture, including both original LEFs and tracks, is on epyc10 under /srv/opentallas-scratch2/claude/fable-lepe/opus-p8-local/r3/clock_access_ab. The historical full-parent log is line 3467 of run_route.log in epyc7's 3fa87b84b18 LEPE t2 attempt 22. 
