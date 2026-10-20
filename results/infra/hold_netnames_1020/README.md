The output hold helper used the original output-port name for an internal source net after reconnecting its BTerm to a new hold-stage net. OpenROAD write_verilog then aliased the two native nets. MC3's unchanged mandatory main 042aa171b census refused the export with 615 multiple-driver errors.

Source fixes 52ef34c5d and 5a3a675c5 rename an internal net only when its exact native name matches an actual BTerm. Existing unrelated internal names remain stable. Source, pad and intermediate net names are checked against both native net and BTerm namespaces. Shared output nets retain their object identity through later hold insertion.

Actual MC3 proof uses source-pinned 833.333 ps synthesis (RTL 272b37645), 1,229 ports, 42,194 post-hold cells and 44,257 signal hyperedges. Complete native BTerm/ITerm edges, raw cell hierarchy names, masters, PG/signal types, net/cell dont_touch, placement status, location and orientation match before/after the fix, ignoring only net names. The fixed ordinary write_verilog export reads back to exactly the same native graph. The unchanged current mandatory native census passes with max32, zero role errors and zero violations. No custom exporter or parser exemption is used for this passing result.

Actual route clock.sdc binds 613 delayed inputs, 615 delayed outputs and one clock. Port-binding names and serialized SDC text are identical before/after hold insertion. This SDC has no explicit get_nets reference. The regression coupon proves that an unrelated named internal net and its existing dont_touch property survive, plus shared-source outputs, indexed/escaped names and deliberate collisions in all three generated net families and the BTerm namespace. It passes with the fixed helper; the old helper fails ODB-0440 trying to connect to a null generated net.

Run the regression inside openroad/orfs:asap7lock with TEST_WORK set to a writable directory:

    python3 tools/ref_tile/tests/test_leaf_iohold_netnames.py

Full immutable actual run evidence remains at ot-agidock128:/srv/opentallas-scratch/claude/codex-hbm-mc3-v6-833-1020. The census summary records original full-report paths and hashes; verify_actual_mc3.py checks native graph/properties and round-trip identity. graph_comparison.json preserves original/fixed ODB hashes.

Scope: native connectivity/property and constraint binding proof only; no imported cell behavioral model or mapped functional equivalence claim. No GPL/CTS/route or physical gate was launched. The independent PG-before-protection helper change and current clock helper must be composed before any future gate.
