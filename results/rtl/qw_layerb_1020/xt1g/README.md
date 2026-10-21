# XT1g: near+far matvec on the dv2f20g5r2b GEN die netlist (TOK.QW.LAYER.2, QW-LAYERB 10-20)

Vehicle: tools/qwen_layerbench/die_carve.py carve of g5r2b out/case/die.v (sha256 in die_inputs.sha256): dvs_W5
(qfd_dv_slice2_w, MU_NU 4 from die.v.params.json) + near c16_W5_2 + far c16_W5_3 + the 11 qfd_landh0 n=1 landings
between them, instance lines byte-for-byte; relay RTL from gen_relay_rtl.py; 32 ROM_TILE lines from the GEN rom_bind.vh;
real TP8 rank-0 L0 masks (XT1n prep). Source = g5r2b run snapshot cfc5a82ac. Verilator 5.050, ot-epyc6, build 47.7 min,
70 GB RSS. RS/RSO sampled at the slice pins AFTER the die landings.

| run | near | far |
|---|---|---|
| nominal lead 8 gap 4 | PASS 64/64 | PASS 64/64 |
| nominal lead 4 gap 2 | PASS 64/64 | PASS 64/64 |
| romswap (mutant)     | 64/64 | FAIL 0/64 (witness log_romswap_fail_witness.txt.gz) |
| nobind (mutant, empty ROMs) | pending (second build) | |

Measured edges from the hr go at the slice pin (lead 8 / gap 4), vs XT1n (same events, no die landings, dv2f16 src):
- near: first rs 187 (XT1n 181, +6); last final qkv 250 / o 234 / gu 442 / down 330 (all +6)
- far:  first rs 248 (XT1n 236, +12); last final qkv 311 / o 295 / gu 503 / down 391 (all +12)
Each landing crossing = +3 edges, exactly the ledger's per-crossing price (23314a50c die_edges q3h/rs: n1/E2, +3).
The far cluster path crosses TWO landings each way (slice->near col + near->far bco; far rs->near rs_i + near rs_o->slice),
and far is the tail of every matvec, so a matvec costs +12 on the die, while the ledger prices +3 broadcast + +3 reduce
= +6 per matvec phase. Ledger correction: q3h x2 and rs x2 -> 2 crossings each per priced phase = +12 cycles/layer
(2 bcast phases + 2 reduce phases x +3), = 432 cycles/token (+0.17% on 261,667): price impact negligible, record it.
No datapath / ROM / tag change between XT1n and the release netlist: exact on the real ROM through the real landings.
Scope: one column piece (N side of dvs_W5); the other 47 cluster pairs are the same masters/landing classes.
