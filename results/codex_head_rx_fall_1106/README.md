# HEAD F1 falling first RX capture (inactive candidate)

The new HEAD-only capture helper replaces the existing four-bank port pipe only through a fresh, explicitly selected private RXQ overlay. `FIRST_FALL=0` is the original rising-edge behavior; `FIRST_FALL=1` changes only bank0 to falling recovered clock. Banks1–3 stay rising. The shared PMA implementation and canonical HEAD adapter are unchanged. The overlay tool appends `RX_FIRST_FALL=0`, checks the selected donor SHA, and refuses the canonical adapter. Its explicit `--first-fall 1` candidate includes the new helper in `overlay.f`; unchanged donor dependencies remain required.

The donor is the actual dh72 `hd_serdes_vB` RXQ source, SHA256 e173eb3a0db5866bb4e8b5294cf0f412a18844d7fe488b0e07ec09036913a94d (RXQ candidate c71c41ad34a, off main). TX and all decoder, FIFO, reset, and status code are unchanged by the two RXQ edits and one private adapter parameter binding.

## Exact capture result and cycle price

At full544-bit width/LAT4, six source publication phases −90, −1, 0(NBA), +1, +83.3, +166.6ps pass. Each has305 rising and304 falling checks, all544 bits exercised, six checks during reset synchronization. The original unreset capture behavior is preserved through the warm-reset intervals; the downstream decoder's acquisition/replay behavior is outside this cut.

Default0 matches the actual original `ot_s81_pma_bm`. The falling candidate is checked against independent source word labels, including every internal bank edge and whole-word output. Every one of three mutants (first bank rising, bank1 falling, lost top output bit) fails its actual assertion in each phase:18/18 caught. An initial nonvacuity harness failure came from overwriting32 random bits with a small monotonic counter (high counter bits never toggled); its failure remains in scratch. The corrected source-labelled pattern exercises every bit. No RTL correction was needed for that failure.

For a held/source-labelled word n published around source rise n, the qualified rising calendar first captures it at rise n+1 and presents it after rise n+4. F1 captures at fall n+0.5 and presents it after rise n+3. It advances the rising FEC-input cut by ONE recovered-clock edge: half an input-capture interval and half the first internal hop. Four registers does not mean unchanged latency. Unpadded old RTL with early arrivals can already capture a word early; that violates the intended baseline hold convention and is not authority to declare zero cycle change.

This is RX-front −1 recovered edge /0 local-core edges, TX0. RXQ's existing +2 recovered/+1 local-core stages remain separate. No fixed HOST/gearbox/CSR age is claimed: the adopted complete source cohort must be measured again.

## Resource and physical boundary

Actual544×4 cell mapping yields baseline2176 DFFHQNx1 and F1 544 DFFLQNx1 +1632 DFFHQNx1; both have2176 equal pre-ABC output inversions. FF area is634.5216um² in either form. Stage0 clock capacitance increases by3.285216fF total in the actual TT RVT library. No state bits are added.

The separate clock owner estimates actual TT/FF paths on the retained legal4CTS DB, using the real negative-cell timing. Its proposed150/280/410/540ps group arrivals and remaining-PMA700ps are estimates, not routed evidence. Remaining rising hops and the transition into the decoder still need quantified hold padding; no whole-type area/power or timing pass is claimed. No new full-type P&R was launched. Physical adoption requires that estimate, actual source/geometry review, modelled padding/clock costs, fresh exact source gates and native ingress measurement.

Runtime: intel2 `/srv/opentallas-scratch2/claude/codex-head-rx-fall-1106`, proof2 unit oth-ubuntu-1140353-1793974083 and mapping unit oth-ubuntu-1338277-1793974513 both terminal0. E6 proof waiter was NOTRUN and canceled before rehoming. The first mapping wrapper treated an uncompressed library as gzip and returned a misleading wrapper0; it is retained as infrastructure failure. The corrected run uses the actual uncompressed library and the explicit mapped-cell census below; no timing claim derives from wrapper status alone.
