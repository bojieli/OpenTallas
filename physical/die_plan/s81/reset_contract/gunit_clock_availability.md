# S81 gunit parent: reset-time clock availability

Contract: [gunit_clock_availability.json](gunit_clock_availability.json). Status: **PUBLISHED_CONDITIONAL**.

The gunit soft parent (`s81p_gunit__t1`) is not in the 64-edge hard-core list of
[reset_contract.json](../reset_contract.json). This file does not borrow that list. It joins three links explicitly.

1. **Die clock source.** `plan_h2_2249.json` has `clock.source = @die.clk` and `reset.source = @die.rst_n`
   (wavefront, 2 sync stages). There is no PLL lock qualifier or reset pad. The landed top takes region clocks as
   die inputs (`clock_landings.py top_rtl`). The gunit clocks are `clk` = bg61,
   `fclk_in_flt_i0` = `bk_sel.clk` = bg70 and `fclk_in_xtier_i0` = `s_2N_x06.clk_t14` = bg51. None is a SerDes
   `pma_rck`. The gunit, bk_sel and s_2N_x06 clock/reset projection is equal at T48 b3e8508, cohort 5489 and
   origin/main 6defc3c.
2. **Measured T48 paths.** The paths from these three taps to the single `root` input of the T48 `ctree.v`
   (sha 3b1763c1) have 192, 208 (+1 BUFx24) and 176 CKINVDCx16 cells. Each path is all single-input, with even
   inversion and no gate, divider, state or enable. So every root edge reaches every gunit clock pin.
3. **Boot hold.** The die reset contract (OWNER 10-29) holds `rst_n` low for at least 64 clocks with the die clock
   running, which gives 66 known-low edges. gunit sits at wavefront release 84 (entry + depth 8, 284 plain relays,
   0 gated relays). Its 10 hard children release at 85, and the die maximum is 105. The deep bench
   ([receipt_deep.txt](gunit_1101/receipt_deep.txt)) gives 66 known-low edges at every depth 0..128, cold and warm.
   The HOLD 61 mutant is caught. A root clock stopped for 62 of the 64 hold periods gives only 4 edges, also
   caught.

Result: gunit's parent relays and its 10 hard-child `rst_n` pins see at least 66 known-low edges on their own clocks.
The parent needs 9 local edges; the hard children need 64.

## Conditions (not proven here)

- **C1, root activity.** The die `clk` toggles from rst_n assertion through release + 85 clocks. This is the owner's
  boot premise and the only basis in the repo. No artifact models the off-die oscillator.
- **C2, hop timing.** The wavefront hops and gunit relays must be timing-clean, as checked by the die STA gate.
  T48 real-view hold is BLOCKED(kits).
- **C3, tree form.** Any new production die clock tree must re-run `gunit_1101/trace_tree.py` on its `ctree.v`.

Excluded: recovered PMA clocks, which count only after lock (COORD Q1); mid-run short pulses; and the
post-release clock-landing SETTLE.

Optional, cheap next evidence: a native bench of the closed 50-file gunit source with its hard children
black-boxed. Drive three region clocks from one delayed root and the release-84 wavefront, then assert at least 64
known-low edges at every relay and core `rst_n`.
