# FAM-S81-SLICE J7 package, c1x_C (11-21 ~02:30 PST)
## Sizing (measured, p1 = c1x_C t9 kit gen on epyc9 fable-fix-s81-slicec/p1; p1 run itself was cancelled by someone, no CTS yet)
- gen cell_census: pre-floorplan synth 335,915 (+pins -> place est 350k); place nontap 480,720 (+120,945 tap/endcap); cts nontap 491,829. Cap 400k -> OVER (120-123%). Other measured: t3 477k, t6 503k (CTS post-hook setup -1572).
- Placed-instance census t9 (old CTS DB, 496,913): 201k anonymous flat (_N_ / wireN / input/output/load_slew buffers), u_xg 39k named (34k flops), cland_xring_i1 32k, cland_leafup_i3/i4 34k, bout/bin_xring 31k, ft/xtier 30k, ist_leafdn 42k, bin/bout other 47k. Cells per 100um X-bin peak 105k/113k at x 300-500; 97k below y 100 (landing/station rows).
## Decision
Over cap but under largest-closed 517k: split is the J7 form only if p1 stalls; but p1 cannot run (timing classes A-D need R1-R4 first). Recommend: J7 carries (a) rows below, (b) split B as the second form built in parallel, first to GRT TT wins.
## Rows (to write against plan_j3b/J6 plan schema once C3 bind passes; none generated yet)
R-ST1 xg bus stations: N-face bus (x 80-150) -> register cloud (380-540,250-330): relay_depth +1..+3 stages on xg.xf_q/vo_d and pin bundles, one station per <=300 um (22.6k hops >300, max 1434 um). Source: FABLE-VISUAL-0030 s2.
R-SL1 memory-slit move: remove the 2,243 station flops from the 58 gaps <20um in the NW memory array (x 180-380, y 500-1100); place station row outside array (W of x 150 or S of y 480). Needs leafdn station re-site rows as in SLICEC p1 mkplan (every hop <= 356 um).
R-HF xr half-cycle: first leafdn station within 200-250 um of xr W/S face (class C, SLICEC-0045 R3).
R-TAP: span-300 taps, 171 for t9 (p1/t9_taps.json).
R-RD: relay_depth eg_v/eg_c -> D2 on t9, t10; cfg_d -> D2 iq_C t1 (functional).
## Split B (no growth, registered crossings)
Cut: array half = 24 memory cores + u_xg (u_s 24k, u_r 15k) + cland_leafup_i3/i4 + ist_leafdn on the N/W side; hub half = xr, eg, xf + finish row + xring/ft/xtier landings. Keep xr<->eg (class A direct 723-880um wires) in the SAME half. Crossing = xg outputs (xf_q, vo_d, g*) and N-face inputs: each crossing net gets a pipeline register on both sides (+1 cycle each way declared, cycles pre-approved). Target <= ~260k cells per half (pre-place 336k total). Core shapes unchanged, die/outline unchanged: two types share the same footprint, parent die plan carves the tile into two partition regions.
Missing before rows can be written: hierarchical cell census of the synthesized netlist (flat names hide 201k cells): run yosys hierarchy stat on the t9 kit RTL as a private ot-run job; and the xg<->xr/eg bus width list from bound rtl.
