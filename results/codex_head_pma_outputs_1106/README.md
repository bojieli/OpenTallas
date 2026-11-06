# Explicit PHY output-data clock association

Optional clock.pad_clock.pins[].data_outputs mirrors data_inputs: exact existing output pad name, max_ps, min_ps and evidence, accepted only on an output clock already rooted at an actual source_clock_port. No plan activation, RTL or cycle changes.

The emitter removes only selected TX pads from generic vclk output-delay collections using the existing explicit generator-side selectors, including the landing-helper form. Existing output loads remain on every data pad. New native output delays retain declared budgets and use the actual generated export clock. Full current-policy setup/hold uncertainty is explicit on that clock. Lint permits a generated clock to time only its declared data-output pads; other generated-clock path use remains forbidden.

43 targeted tests pass, including previous pad-clock tests, wrong clock/budget, lost uncertainty, unrelated ports, direction/duplicate/nonfinite/evidence refusal, empty seam collection and landing-preprocessed collection.

Actual OpenROAD/OpenSTA26Q3 read: six real ASAP7 sequential/buffer cells, four real TX output ports, actual clk→BUFx2→pma_tck connection, unchanged max166.6/min0, actual setup andhold paths. Native output hold shows25ps uncertainty, tiny setup625.201ps andhold15.211ps. The reviewed topology is output_probe_review.png. This is a software clock-role/syntax probe, not physical SerDes qualification or signoff. Physical clock attachment and native export phase remain the physical owner responsibility.

Harness setup failures were retained in scratch: installed SEQ library is220123 (not guessed211120), the netlist reader requires explicit scalar assigns and OpenROAD needs tech/cell LEF before link. An initial test-fixture TX flop also drove all ordinary outputs and overloaded its unrelated load; ordinary ports now use separate input passthroughs. No production constraint was changed to address those fixture defects.

Reproduce generation: python3 results/codex_head_pma_outputs_1106/make_probe.py REPO_ROOT SCRATCH_OUT. Run probe.tcl with SCRATCH_OUT mounted at/work in the pinned openroad/orfs:asap7lock image through ot-run.
