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
6.4GiB calibration and39.0GiB measured predecessor route envelopes remain.
Actual SDC verification, fresh CTS TT/FF measurement and route handle are
pending; no routed closure claimed. Original work remains at remote
routes/bfk_recut_hs4_sm15_c674dadfd_tc_cx_cal.attempt1_R7_preserved.
