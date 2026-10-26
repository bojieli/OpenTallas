R6 source/native PASS; storage redesign required before gate

Default-off lane successor retains PLAT4 and ADD_LAT7 with no additional edge. Exact mapped current-main census passes32 with no role errors and no constant output bits. The actual netlist and five FF Liberty hashes are in lane32_r6_summary.json and full compressed census.

Source arithmetic, whole-lane, independent-random-startup/reset tests pass; all five targeted mutants fail. Product exhaustive proof is reused from the identical R5 module, with exact module hash in r6_product_reuse.json. Warm256 random lane startup uses independently scoped VL_SCOPED_RAND_RESET initializations, confirmed in generated Verilator C++; warm0 run is separate. Reset comparison qualifies data by valid, compares valid every cycle, checks outputs immediately under offphase assertion, and checks copied control convergence.

Pure bypass-code FF pipelines and seven-edge valid metadata remain subject to the storage rule. This is source evidence, not gate admission or adoption. Next source revision replaces those delay lines with explicit rings at identical ages and repeats actual native census and semantic checks. No QKH gate was launched.
