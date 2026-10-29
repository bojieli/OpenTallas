KV-KITS-21 ASK-C (DIE-KV-27 event27, KV-007, COORD ruled YES): qkd_ahub ck[2:0] -> ck[6:0], same clock, 0 added cycles.
clock_split7.py REPO OUT -> ck7/{qkd_ahub.sv, qkd_ahub_static_dw.sv, core.json} from main rtl/hdc/nearhbm/qkd_ahub_static_dw.sv +
Codex ck3 source wrapper (codex_qkd_ahub.sv / codex_core_source.json from origin/codex/kv-kits-1028 results/codex_kv_kits_1028/ahub).
Entries (pin census of event27/qkd_ahub_pins_r27.json):
  ck[0] centre: u_rr, u_core (not am), zh relays, zh_err_q, recip loop     ck[1]/ck[2] S/N zh pairs (unchanged from Codex ck3)
  ck[3] S-W (150,50):  ap_q[94:0] (ap0, ap1, ap2[8:0]) 95 FF + u_core.am[143:0] 144 FF
  ck[4] S-E (450,50):  ap_q[171:95] (ap2[42:9], ap3) 77 FF + u_io (hs_* pin flops, start/epoch/T, hf fault) whole module
  ck[5] E-S (580,110): u_rw_s fr_epoch[15:0] + fr_rz[55:0] relay (W=72 x WF_RLY stages)
  ck[6] E-N (580,330): u_rw_n fr_rz[127:56] + fr_valid relay (W=73 x WF_RLY stages)
Proof: (1) every substitution reverses byte-for-byte to the main module text (only clock tokens / split always + instances);
(2) bench_ck7.sh (tb_qkd_ahub_static_dw, Verilator 5.050, intel2): all entries tied -> PASS; each entry stopped (CKMUT 1..4) and
north zh pair stopped (CKMUT 5) -> FAIL; MUT=1 control -> FAIL.  bench/*.out.  [CHECKED-own]
Note: an inverted-clock (half-cycle) mutant on E-S and on the zh pair PASSED in a first run (bench is cycle-level), so the
mutants were changed to stopped clocks; edge-polarity is a timing matter for the kit STA, not this bench.
