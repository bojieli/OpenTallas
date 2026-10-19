# COLL actual bank-latency and contact model pickup

Status: MODEL / BLOCKED; no build, source adoption, gate, or timing qualification. Owner LEAD-HBM. H.STA.BANKLAT.COLL waits H.STA.BLK.16.4 and INF.SRAM. Four b1b831894 gate failures remain immutable: n1k/n2k/n1e/n2e M4 overflow398/96/1267/270. Regional clock spread passed; n2e TT setup -92.741ps, depth647ps. Neither passing clock spread nor II1 functional proof closes this leaf.

## Exact source and calendar

source_hashes.json pins the three real safephys RTL files and all four specs from b1b831894. They select NPT1/SOLO0 or NPT2/SOLO1, VM_RT74, SAFE_DELAY1; the hardened physical wrapper disables extra generic pin registers. Earlier wrapper +1 issue edge is already the V6 boundary capture: inst/start/busy capture on issuer d3; do not charge another +1 solely for replacing delay pipes.

The 6325606c8/a3dafdb3d calibrated mechanism/production evidence remains useful functional evidence: 39,824 mechanism checks, each production1792 pairs, dense8192 pairs/2048 consecutive requests at II1, causal VM/lane/reset failures. It is not physical proof or a die binding receipt. Four independent rings are 140x83 VM valid+meta (meta gets a further one-edge capture), 24x74 early select followed by24x9 late select, 68x12 injection. At each edge they consume and produce respectively17.5/3/3/8.5 useful B on separate 1R1W ports. Physical widths256/256/128/128 mean32/32/16/16 B per read and write port per edge. II1 has no spare port bandwidth for another live stream.

The delay source has input capture, SRAM registered read, and local output capture. Its read address wp-(D-3) differs from write address wp by80/71/6/9 rows for the four rings, strictly nonzero modulo128/128/32/32. Steady state therefore does not depend on same-address OLD semantics. Warm masks hide uninitialized storage; power-up zero is not a silicon contract. Warm reset still needs exact assert/release-age proof after any landing change.

Current committed banklat budget is BANK_RT72 (share), VM_RT74 (COLL and gather), NW share40/QDQ RL45. Formula: VM_RT=BANK_RT-6+face_extra+client request/return lanes; face_extra0 for REG0 or2 for REG1, with paired lane budget8 or6. At the existing contract VM capture is P+10+74=P+84; injection remains P+12. Gather compiler injects IE+29+74=IE+103, every write and span +74. row_gather compiler q3 stream shifts max(0,VM_RT-2)=72, moving both capture and SU request consistently. ARGMAX compiler lead12+74=86, 212 rows, requiring actual ROWS256 issuer rather than default64. These are source formulas, not proof the latest die applies all parameters and request pads. Padding is on17-bit request lanes; response data must retain transaction identity and its original owner.

Current main parent body instantiates ctl_v5r_n1s0/n2s1 (and q2/q3), not safephys leaves, with VM_RT default0 and ROWS default64. A physical replacement requires explicit parameter/shape matching plus exact current die artifact binding. Do not silently equate standalone safephys leaf proof to current parent deployment. Native corrected contact timing and clock boundary may add delta edges; any delta must shift assembly/select/meta/valid together, compiler reads/injections/writes and downstream deadlines, with updated programme capacity and request-lane reservations. No arbitrary fixed74 guarantee survives a macro contract change.

## Corrected geometry finding

macro_faces.json is computed from the actual p192_mir/p192_rc source LEFs, not legacy XS dense macros. Large macro94.824x80.472um has410/409 W/E contacts, density5.095/5.083 perum, active spans78.528/78.336um. Small51.408x39.960um has199/198, density4.980/4.955, spans38.016/37.824um. All have genuine .192um pitch. Thus a >6 contacts/um rejection is incorrect for these exact COLL views. The observed M4 cap0 escape/OBS failure remains real and needs physical access redesign; widening an external halo did not fix it.

The exact abutted stack has y43.2,123.696,204.192,244.176: only the first is43.2-lattice aligned. The model successor must place each macro on the lattice, model actual M4 port/OBS escape to both independent register bands, and preserve a full-width legal cell band. A possible geometric starting inventory is y43.2/129.6/216/259.2, requiring at least345.6um height, but this is not an access-qualified placement or grant. Clock insertion must be matched against actual child references; the current gate flags macro_clk false, so all macro clock pins and registered read capture ages need explicit review.

## Complete native graph and honest refusal

Read-only unpinned fleet export from original n2e4_cts.odb produced43,798 cells,2715 top ports,38,352 nets,80 masters. ODB SHA136ca9b2ee1f6d7e4ea1b0c1ccf7434bcaedc1c366b1f1925aa8a6150262210c; raw graph SHAc13670ca968e3591cb865950a25d429dc8244074660887743483b08519fb8f8b. Every native ITerm, net, BTerm, and MTerm role is retained at ot-epyc8:/srv/opentallas-scratch/claude/hbm-coll-banklat-model-1019/out. The exact original gate is /srv/opentallas-scratch/claude/ref_gate/hcoll_v5r_ctl_n2s1_v74e-20261019-120958. Export used ORFS image16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29.

Unmodified strict_contract oracle with exact native TT libraries refuses unsupported bus in ot_sram_1r1w_128x256_m1_r2c2_p192_mir. strict_refusal.json records actual graph/library hashes. No SRAM cells or bus bits are omitted to obtain a SAFE result. Original ca18 direct TSV maximum32 is not independent BUF/INV-transparent all-driver proof. The first diagnostic attempt omitted macro libraries due to output directory permissions; its negative receipt is preserved separately and superseded by the fully populated exact-library refusal.

Source reset is nine kept copies of ONE asynchronous-assert/synchronous-release D1 flop, not the required two-stage face landing. All useful data/control/raw ports/upstream copies need complete transparent census and real pin-registration proof after structural redesign. No clock-name exclusions or merged-copy assumptions are accepted. All-native PG conductor/pin coverage remains OPEN.

## Bounded next work

1. INF.SRAM owner supplies current exact port/OBS/compiler/timing access model for these p192 roles; source pin counts already meet density.
2. LEAD-HBM models full two-stage face reset, retained useful-D/control ownership and explicit native macro bus roles; costs new FF/clock/area and any reset/runtime edges.
3. Whole leaf model includes multiply depth split, register-band/macrolattice/reach/clock and genuine II1 port schedule. ROOT reviews that model before any RTL prototype or new gate.
4. Re-derive actual compiled die request pads and producer/consumer calendar after measured delta. For R6 producer image5 completion1463.31 to start1479.31 leaves16 stream edges only; no per-sector visibility proof supports unpriced prefetch. Do not present the older banklat source budget as current token timing closure.
