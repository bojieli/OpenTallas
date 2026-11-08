# TX atomic-chain clock reform candidate

Private form, not built or counted. Existing TX CH_STAGE1 adds one output PIN cycle; that cost remains unbound. This clock form adds no logical cycle. Old TX eco_dh80 third pass remains stopped.

Measured routed TX vC: TT +86.32 ps, FF -19.44 ps/359 endpoints, TT24 slew pins. A fresh read-only full FF census found 115 input-port starts plus244 actual register starts. The earlier `other244` was the non-port class; `.reg1` is an existence probe limited to one path, not the internal endpoint count. Worst internal d4[438] ->d5[438] has48.287 ps data delay, launch CK346.571 vs capture378.180 ps; +31.609 ps clock skew plus uncertainty/hold exceeds that direct path. Existing F4 already ran:1435 pairs moved,4717 too far. Re-enabling that switch cannot solve the measured class.

The new opt-in `--clock-atomic-groups JSON` uses the existing **core_density_taps** PRE_CTS machinery: native clk -> existing balanced trunk -> real BUFx24 tap -> local CTS. Each declared complete chain is excluded from generic density splitting, kept intact through assignment/F4, and receives one branch. It fails on missing members, overlap, bad native clock pins, excessive group size or physical radius. Its post-CTS receipt requires one actual leaf for every member, fanout within16 (hard limit64), radius<=20um, and noninverting buffer ancestry back to the exact native clk input. A shared upstream tap with subsequently split leaves fails. No margin, input delay, false path, or signoff condition changes.

Planned exact membership from the current source's placed.csv:

| Family | Branches | FF per branch | FF total |
| --- | ---: | ---: | ---: |
| encoder d0..d8, same bit |512|9|4608|
| encoder p_d + three adapter l stages, same bit |544|4|2176|
| total atomic |1056|max9|6784|

Other10258 FF retain the normal density partition. Existing `--reg-guide-boxes` is the supported placement API:1056 non-overlapping compact guides, 4.32x2.16um encoder and3.24x1.62um adapter; planned fill28%/22%, each below80%. Full observed old groups do NOT meet radius and must not simply be routed again. `clock_plan.png` is a reviewed **planned** diagram, not an actual PLACE. Its landing regions may affect setup to parity/data consumers; inspect the new actual native graph before CTS. Port hold115 and slew24 are still open; this candidate has not closed either.

Proof:7 lightweight Python/Tcl tests pass, including missing/overlap/cap/radius controls and actual-leaf receipt controls for split leaf, inversion, far leaf, wrong native root, overcap and missing member. A plain ot-run8GB read-only real3_place.odb fixture reproduced the default-off baseline's exact assignment/medoids for17042 sinks, then correctly rejected the old geometry with `ATOMIC_CLOCK group enc_0 outside reviewed radius`. It launches no P&R and mutates no DB. See `clock_fixture_1209.log`.

Next: fresh exact self-contained CORE kit using the matching current core runner/helpers, new helper source, `--clock-taps density --single-root-taps off --clock-atomic-groups clock_groups.json --reg-guide-boxes reg_guides.json`; one PLACE only after parent review, then actual graph/images and LEC before CTS. The existing TXvC kit stays intact. Candidate groups are exact OpenDB names, so a different synthesis requires regenerating membership. No merge/tag/POR change.
