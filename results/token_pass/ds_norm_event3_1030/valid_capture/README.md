Valid-time partial capture correction

The original producer checked all80 partials correctly at p_v, but printed pd
240edges after the command. That invalid-time diagnostic can drift and is not
an output handoff. Historical producer/composition.json mislabeled those late
words as actual partial data; retain it only as history,not a numerical input.
producer/composition_valid_capture.json is the corrected current record.

The same oneVP/VN source component now captures ACTUAL_VALID_PARTIAL on p_v.
Intel1 ot-run2838908-1793375981 PASS80/0errors833ps; payload control changes
actual leaf0 and fails as expected. Canonical actual_partials80.hex SHA0fd94acb
is byte-identical to the earlier equality-validated80-word scoreboard file used
by XF/collector. Their numericalinputs/results remain unchanged. The source
handoff generator now reads only actual valid-time capture,never the late
print or scoreboard. No consumer RTL rerun is needed for identical input bytes.

This distinction is explicit in receipt.json. Existing logs/verdicts remain;
no production RTL/plan/globaldate admission or source-profile adoption occurred.
