DIE-QC-97 TAP-PAIR CHAINS (11-11): clock.tap_pair_affinity.chains (OT_TAP_PAIR_CHAINS=1), default off.

Why: tap_chain_affinity-owned delay-pad chain flops (u_pd<D>_ / u_d<D>_ / u_lpad_ / u_r8b_strap_) are left out of the short-pair
graph, so the hop chain terminal -> consumer (QC slw_fe_v2: u_pd9_x_fw_p2_i_N / u_pd10_x_fw_p1_i_N -> u_core.cmd_o, 60 paths,
2.2 um apart, worst -68.99 ps TT GRT hold in pilot 1 and 2) keeps the tap boundary of the chain join.  With chains on the chain
flops are nodes of the pair graph plus a bond between consecutive stages, so chain + producer + consumer form one component
that the merge phase puts on one tap; stages that already shared a tap stay indivisible (coherent-pair rule); tap_pair_affinity.tcl
fails closed if a chain that shared one tap before the plan does not after it.  Clock pins only: no data / reset / cell change.

Measured (the kit's own clock_taps.tcl run on pilot 1's pre-CTS 3_place.odb, in memory only, epyc4; the 173 cross-tap reg->reg
GRT hold pairs of pilot 1; pairs on one tap):
                          kit as built   pair affinity   pair affinity + chains
  all 173 pairs                  0            109              169
  60 pd chain -> core.cmd_o      0              0               60
  106 pairable (no chain)        0            106              106
  7 other (2 reset relays, 3 depth-3, 2 > 60 um)  0   3          3
Clock pins moved: pair 279, pair + chains 643 (332 chain-owned); chains: 2160 chain groups single-tap before 2160 after, 0 broken;
no coherent-pair cut; every tap within its capacity.

Identity with the key absent (anchored head 08a1c69f4431, 123 types): tap_pair_affinity_exports identical to main for every type
with the key absent and with tap_pair_affinity {}; schema.validate output identical; clock_taps.tcl with pair affinity on and
chains off: 0 of 59354 flop clock pins differ between this branch and main.
