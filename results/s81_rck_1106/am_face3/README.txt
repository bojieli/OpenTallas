S81-RCK-1 AM face cut: SOURCE READY, DEFAULT OFF; no physical profile activated.

Enable only the joint native LP/u_syn option OT_S81_KP4_AM_FACE3. Three pop4
counts of (raw native PMA header XOR 12'hA5C) register on the EXISTING face edge,
next to the existing544-bit payload and valid capture. The existing u_syn AM
register sums these9 bits and tests <=2. Nine extra FF, zero full cycles,
unchanged payload/valid/reset/FSM/calendar. No arithmetic or clock contract waiver.
The LP generator preserves this option; changing the face clock/depth/bindings
fails closed. Old full source preprocessing with the flag OFF is token-identical.

Literal mechanism proof uses actual ot_pl_pad and ot_s81_kp4_rst, the source
u_syn AM/FSM/x0-x2/xs prefix and the actual new metadata module.20,000 cycles,
4096 exhaustive headers,49 native lock acquisitions,42 reset edges,1717 state
bits compared. Six mutants fail with state_x=0: wrong group/xor/threshold,
valid epoch, payload pipeline and reset bypass. Syndrome/BM arithmetic is
unchanged and outside this smallest mechanism proof.

The mapped prefix retains the actual hard ot_s81_pma_rxm and its captured
Liberty arcs, all544 payload FFs, valid, old/new AM check and9 new metadata FFs.
Same selected RVT TT libraries, abc_speed, DONT_USE and captured FA techmap as
retained t4a8. Cells-only STA, no estimated long wire; TT setup0, FF hold25,
833ps,20ps clock transition,1fF output load, same local clock group.
Old post-face TT slack313.91ps; new native PMA->pop4 TT590.50ps and partial
sum->AM TT568.90ps. New FF hold67.97ps/31.88ps respectively. Post-face cell
delay improves about255ps. Actual clock skew and transport wire must still
fit; these are not routed signoff or expanded-child clock-coverage claims.

Placement conclusion: the data capture band is useful, but the complete
header arithmetic/transport must be designed. Moving a FF without its QN
inverter gives a false long load. Relocation plus normal wire repair removes
that artifact; source AM cut and registered transport are still needed.
No P&R launched. Original native PMA external CDC contract stays unchanged;
no HEAD data-delay envelope is imported.

Runtime input capsule and raw geometry estimates are on intel2 dedicated
/srv/opentallas-scratch2/claude/codex-s81-rck-1106. Source cohort2c7054fd3cda3f76c35bb1e4b04f8d9ddd06711e;
retained E5 codex-wave-1105/runs/s81/kit-wave/s81/bf1e2233ce05/items/serdes__t4/attempt_8/gen/serdes__t4.
Original kit is read-only. No live kit mutation, no model activation, no signed count.
