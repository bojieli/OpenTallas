# GEN5 shared-tool projection for ROOT review

Base: main `1b69058edc36e5a6ac77292f53b67ae629891944`. Donor source: `d502ea9ae502aaf2ab800c412bb0f1b4cbdb6b25` and its safe/SPT ancestors. This packet contains the dependencies needed by the GEN5 clock caller, rather than the donor ancestry. No deployment or production GEN adoption has occurred.

Dependencies included:

- `tools/die_clock/regtree.py` + `build.py`: opt-in safe routing/leaf reach and shortest-path forwarded spine; legacy DME/safe-off is retained. The safe tree reports violations and the reach checker refuses them.
- `qwen_regional_spec.py` + `qwen_compute_dieclk.sh`: explicit safe/feed/SPT/dissolve controls. SAFE and FEED default **off**, matching main's legacy caller, instead of the donor's implicit enable. A GEN5 deployment must explicitly set `DC_SAFE_TREE=1 DC_FEED=1 DC_SPINE_TOPO=spt DC_DISSOLVE_RX=1 DC_SPINE_SOURCE=ckb_core/pll_ck[0] DC_FEED_ROOT=ckb_rom/pll_ck[0]`, preserve grid/neighbour controls, and supply its actual emitted receiver RTL. Existing live jobs are unchanged.
- `receiver_guard.py`: before disconnection, require one actual scalar bump output source, one explicitly proved MODEL_PASS_THROUGH_R0 receiver input, and only clock outputs belonging to the selected stream spine. Refuse source/BTerm multiple drivers, output BTerms, reset/data/unknown receiver ports and foreign loads. Recheck both ITerms and BTerms after rewiring. The exact qwen_clkrx_ports repaired master and scalar `[0]` spelling are supported. Receiver qualification always remains false/MODEL_ONLY.
- `qwen_compute_dieclk_prep.py`, `die_clock_check.py`, and the narrow regional-verdict qualification hunk: explicit identity proof and false eligibility propagate into reports. The donor's L5 drift-window rule change is deliberately excluded; main's T/2 verdict is unchanged.
- `extra_clock_roots.py` + `tools/qwen_tp8/die_sta_libs.py`: actual declared scalar output directions for qfd_ckdiv6.blk_o and UCIe lclk; root discovery refuses ambiguous drivers. STA refuses unknown/multiple drivers on source-contracted sink roots. Existing measured-reference names and policies from main remain intact.
- `rtl/qwen_split/qfd_ckdiv6.sv`, matching minimal bench and committed PASS/div5-negative logs: true /6 registered source and two-stage reset landing, copied byte-for-byte from the pinned donor. No new local simulation was run; new paired fleet validation follows ROOT review.
- `physical/qwen_missing_phy/nface_tall_g5_lclk_1020`: explicit opt-in PHY variant only. Existing `nface_tall_1017` files and default ABI are untouched. New output lclk requires named connections. The free-running 1 GHz model is a cycle-model boundary, not a licensed/native physical clock proof. Donor metadata had stale hashes for all six changed views; the isolated variant records donor artifact provenance, names that failure, and has corrected views hashes. Physical eligibility is false/MODEL_ONLY.

Source GEN hook `g5_clocking.py`, center-feed geometry, full die source and physical adoption are not imported here. The running GEN5 source still references its donor view; it must remain diagnostic until source/ABI selection and physical proofs are reviewed. No release gate, receiver waiver, frequency rule, mutable storage rule or timing exception is added.

ROOT reach-review follow-up: every checked parent net now requires finite coordinates for its driver and every child. Incomplete, nonfinite or all-empty graphs fail. Admission compares unrounded Manhattan reach to 405 um with 1e-6 um numerical tolerance; rounding is display only. Native centre-feed pin coordinates are retained explicitly as source_xy, and tree root coordinates retain ODB precision. Missing-child/driver, NaN/Inf, all-empty and 405.04 um causal regressions are included.

Validation:

- Receiver/safe/SPT/target/qualification and STA source suites: local focused checks; final test log in this directory.
- `default_tree_comparison.json`: complete buffers/nets/parent/model outputs exactly match main for legacy safe-off DME in both empty and blocked geometries. Defaults are additionally explicit in the shell caller.
- Inherited divider PASS and div5 fail witnesses are source-pinned to d502ea9ae; actual macro/root timing, reset epoch/first use, and any new physical clock output remain unqualified.

Next: ROOT review this concrete packet; then run paired affected fleet tests (native ODB receiver/BTerm guard, legacy/new tree build and actual clock/STA root exports). No current job should be restarted to consume the packet.
