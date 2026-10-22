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

Paired fleet validation is now complete; see the sealed receipt below. ROOT reviews the final diff before publication. No current die job should be restarted to consume the packet.

Qualification-chain follow-up: the existing source contract already says qualification=false. STA views now preserve that flag, prep carries it into targets, and manifest/final clock reports keep MODEL_ONLY even when no modeled receiver master remains. The actual source-to-STA-to-prep-to-report chain is covered by a focused regression; legacy artifacts without explicit false qualification remain byte-unchanged.


## Sealed paired fleet receipt

Baseline is current main `6586b0856e98d05b893e5a46d13a90a84ea12ee5`; final projected source is `c9b5e9d1296b0e7d4baffe2d01c0657f20f43f78`. Archive receipts and reproducible coupon scripts are under `fleet/`. Final ep6 unit `oth-ubuntu-3193582-1792508671` exited 0; `fleet/results7/summary.json` reports PASS on all nine mechanism checks.

- Baseline focused suite: 9 PASS. Projected initial suite: 68 PASS. Qualification transport and full-float sink affected suite: 32 PASS. Earlier completed suites are retained, rather than rerun after unrelated harness corrections.
- Complete default tree output bytes and original PHY view bytes match. Tree output SHA256 is `bb2ac849b495d1a388fccc9d27768a0e503286639f3ed54ecdc191e4514aa68a`.
- Frozen actual g5 die SHA256 `771ed19400e3e7fba0320409ee305cff9018b005c150eaa6b265c281e7a76ca2`: baseline STA misses `n_clk_coll_blk` and `n_clk_ucie` (1083/1085). Projected source-aware STA exports all 1085/1085; the source contract's false qualification remains false/MODEL_ONLY in STA. Isolated PHY source/Lib output identity PASS.
- Actual native OpenDB receiver nominal preflight/disconnect/postcheck PASS using the emitted g5 glue identity. Expected refusals: receiver output BTerm, data output, reset output, multiple source drivers, foreign output load, and source BTerm. A boundary load added after disconnect is refused by the final recheck. Native source-to-sink reach 405.0005 um and conflicting duplicate coordinates are refused.
- Fleet Icarus true-/6 bench PASS; div5 mutant causes the expected FAIL. No full die, new route, native receiver/PHY timing or release qualification is claimed. Existing g5/g5b jobs keep their original source/tools.

Retained infrastructure failure IDs: `3150733-1792507798` (host pytest/ensurepip absent), `3153749-1792507876` (portable pytest py module omitted), `3172382-1792507940` (archive lacked source_pin_plan dependency), `3176792-1792508070` (native dbTechLayer API needs layer type), `3186836-1792508471` (native dbChip API needs tech), `3190772-1792508577` (coupon pin-coordinate lookup used wrong object). These failures happened in coupon setup/harness; the final actual native and source checks passed. Logs and successive harnesses are retained. No product failure was hidden or relabeled. ODB witnesses stay on ep6 at `/srv/opentallas-scratch/claude/codex-qw-gen5-tools-coupons-1020/results7/native`; committed `fleet/native_odb_sha256.json` pins them.
