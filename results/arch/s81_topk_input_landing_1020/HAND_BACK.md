CLAUDE IS BACK at04:49 PT; no further work launched.

Opt-in OT_S81PH_HQ_INPUT_RAW, source cad3c2f0e plus preserved CLI correction/receipts. Default source path remains unchanged. RAW captures eight kept raw four-bit type copies at the existing first edge, then decodes at the existing payload-capture edge. Target: remove the pre-first-flop decode seen at HQ3 u_in.g_f[50].r/D during CTS setup repair. Saves21 selector FF bits, theoretical type-input fanout<=11, zero extra edges.

Completed proof2 on fleet Verilator5.050: default and RAW each23992 comparisons over all621 input-module output bits; all16 type encodings1500cases each and periodic reset. Wrong-type and extra-type-edge mutants both produce IN_LAND FAIL witnesses. All four archived source manifests match the preserved gold/DUT/testbench bytes. Full production quarter bench and native synthesis/census were NOT run; no gate or adoption is authorized by this proof alone.

Initial proof failed before compilation due invalid Verilator -j4 flag; preserved under failed_cli and input_landing_suite.log. Corrected only to -j4 written as separate arguments(-j 4), successful proof2 ran after load-spill ep7->ep5 and was copied back ep7.

Native component synthesis was planned but NOT launched when STOP arrived. Current full-quarter HQ3 gate remains live on original a86fd4882. Do not edit its active source worktree. Input structural candidate is independent of the real-bank MODELONLY fallback46e59d924 and the qualified actual histogram leaf packet0bcc49d96.
