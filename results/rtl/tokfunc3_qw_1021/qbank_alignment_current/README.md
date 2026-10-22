Current qbank alignment finding

Selected QB_ALIGN 0 / QB_LOCAL32 0 fails an independent consecutive Q-slot scoreboard. All 512 Q elements enter as 64 permuted eight-lane words; all 32 rows are then requested in consecutive core edges. The first divergence is cycle 107, output beat 0 lane 0: row 0x22f79b17 (element 16), expected 0x3f800007 (element 0). Thus the visible row is one beat ahead of its valid/beat metadata.

Causal controls: the same exact QB_ALIGN 0 binary passes with one idle edge between slots; opt-in QB_ALIGN 1 passes both consecutive and separated slots. The test never inserts idle edges into the selected production programme and never adopts the opt-in parameter.

Fleet EP7 unit 2766168-1792644114, client 1913772, Verilator 5.050. The first setup attempt lacked the macro model and failed to build; no simulation result was counted. The successful diagnostic used actual 28cb06f38 qbank and exact historical 95781db13 SRAM model. Qdie then explicitly adopted that identical model into 1373ff861 and published its functional source binding; both current input files match exactly. This closes the functional dependency identity for the successor. No physical macro timing or LEF qualification transfers.

Production applicability remains open until the die owner supplies the exact selected compiled q_slot event identity and cadence. This is a conditional current component failure, not a complete current programme failure. The source itself documents the legacy extra valid/beat edge.
