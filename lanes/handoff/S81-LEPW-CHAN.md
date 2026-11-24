# S81-LEPW-CHAN handoff (Opus 5.5, fresh lane 11-24 08:2x PST). Row LEPW-MUC-CAPXR -> S81-ALLFIX-INT. (SLICE dead, no draft existed.)
Job: dsdv_slice_lepw_mu_C__t1 CBC route-demand pinch; row on c9 048fa468f0a2; PRE + scoped strict; ROW-REBASED; private rep kit to sign-off.
## Measured
- CBC-ROUTE-DEMAND-1124 12.80 was on J8 plan_h2_2249 (outline 1442.88, u_cap|u_xr channel 17.28). c9 type: outline 1512, channel 69.12 (u_cap x..371.52, u_xr 440.64..) -> peak already 4.39 (1025 hot). Type is IDENTICAL in c8 9b25d6714339 and c9.
- Cause left on c9: 5 wide lane chains (leafdn_o0/o1 597b, leafup_i0/i1/i2 668b) all sited in one x~376-396 column y 30-1180.
- Row: re-site regs_um of those 5 into separate lanes (channel lane -> west column lane x 245..455 -> staggered east turn y 950-1110), same count, 0 cycles, max hop 390.1 (was 382), no reg in core+4.32 halo. est peak 4.39 -> 2.96 (614 hot), in passing range.
- Ops: intel2 /srv/opentallas-scratch2/claude/s81-lepw-chan/row/LEPW-MUC-CAPXR-ops.json 744777435579 (10 replace ops, old values); copy epyc9 s81-lepw-chan/in/. Tools: lanes.py (search), mkops.py, rd.py (estimator w/ station_bits fill as KITROW-GAPS).
## Running
- epyc9 s81-lepw-chan/row.sh (compose -> relay/LLR/fill tail -> anchor/PRE/PRE-base/G0/census, rt 515889f6ef75), log row.otrun.log, out/ ; was load-capped waiting at 08:5x.
## Next
- PRE pass -> ROW-REBASED to INT. Scoped strict: no c9 elab yet; plan = c8 elab allfix_c8_out (7.4G copy into my dir after c8 strict ends ~11:00) + c8+row plan, bind --strict --all-gaps --types dsdv_slice_lepw_mu_C__t1; same bind out feeds the private kit (kit_wave private-spec --bind-out, goal route).
