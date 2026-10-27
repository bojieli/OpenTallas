# Native S81 PHY source and resource sizing

Actual selected source is `ot_pdie_serdes_col`, with a native landed KP4 decoder,
KP4 encoder and two-clock rate matcher. It contains two analog PMA models. The
whole PHY/controller has **not** been replaced with an abstract.

Full source hierarchy lint PASS with missing modules/pins fatal. The current
canonical and PD7d manifests omitted the instantiated landed decoder; TOK-DS
candidate `1d5d9adef` adds its real source. The initial isolated lint also needed
the two SRAM behavioral models already present in those manifests.

The synthesis trial retains six actual routed digital views and two analog-only
models. Native landed/reset/TXL glue maps to 12,115 FFs. It returns exit0, with
OpenROAD placement area823,107um2 (legacy macro outlines816,983.8848um2 plus
~6,123um2 glue) inside the adopted3318x1013um lot by area alone (24.49%). Yosys
internal cell area678,136.23608um2 includes the digital views' cell area rather
than their reserved outlines. Independent number review is outstanding.

No P&R or current sign-off is claimed. Two blockers remain:

- The existing analog-only model is129.6x2246.4um and declares XY symmetry, so
  it cannot fit the1013um-high lot in a declared orientation. The synthesis
  trial's561.6x518.4um alternative preserves its area exactly on the43.2um
  lattice, but is an UNQUALIFIED planning shape. A90-degree rotation is also
  undeclared. Root/S81 must decide which modeled shape/orientation can be used;
  neither is a qualified physical IP view. OWNER? is recorded in CODEX-LOG.
- The five KP4 digital hard views add physical data input/output registers
  (one each), while the current native LP source instantiates bare functional
  leaves. Rate-match explicitly disables extra pin registers. Reuse therefore
  needs an explicit physical profile and exact latency accounting: expected
  encoder +2TX, decoder q +6RX, lock/relock +2, counters +4. A minimal real-stream
  miter is running before any adoption; these increments are not yet accepted.

Run data: intel1:/srv/opentallas-scratch2/claude/codex-s81-phy-digital-1027
`trial/synth.log` and `trial/run/results/asap7/ot_pdie_serdes_col/base/1_synth.odb`.
Use `tools/s81_link/phy_native_parent_trial.py` only as a synthesis-sizing
preparation tool; it defaults to the original analog shape and labels both
choices unqualified. It does not modify a die plan or released RTL.
