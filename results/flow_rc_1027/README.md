# FLOW-RC-1 (2026-10-27): GRT-estimate vs routed RCX, per net class

Views (routed 6_final.odb + 6_final.spef, GRT 5_1_grt.odb; data `<host>:/srv/opentallas-scratch2/claude/flow-rc-1027/<view>`):
hbm_collar_a4 (intel2, hbm-cores-r6/collar_a4, NOT SIGNED slew 32/25), hbm_collar_a5 (intel2, signed), qc_rst3_k0 (intel1, hold_b signed),
head_elemA_eco (intel1, head-core-r14/elemA_eco), s81_rr_h1_c (epyc2, s81-kits/c3 signoff_cur signed).
`<view>.json`: per-layer unit C/R fit of RCX net totals on routed per-layer length (fit_SIGNAL / fit_CLOCK) and per-net
est/RCX ratios (C, R; all nets >= 5 um and >= 50 um) for the shipped setRC_rcx_asap7.tcl and stock setRC.tcl.
`<view>_probes.txt`: slew/cap violation counts and WNS (est on 5_1_grt vs RCX), clock-sink arrival est-RCX (ck), slew-margin sweep (mg).
Probe scripts in probe/ (diagnostic, docker on fleet hosts, session-exact libraries).
