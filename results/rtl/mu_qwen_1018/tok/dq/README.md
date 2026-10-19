# MU-DQ-TOK (10-19): token-pass slices on the Qwen MU release dies (label: PRE-0kg dies)

The dies are dv2f18mu (compute, src 41b5e3b16) and kvs14r-bce531645-mu (KV). COORD 0kg (10-19) moved the release compute die to
dv2f18 (claude/mu-die-qw2-1019), so these results are pre-0kg plumbing, to be re-run on dv2f18dh.

1. XT1 column slice on dv2f18mu (`xt1mu/`). The vehicle is qfd_dv_slice2 (dvs_W5) plus the near cluster c16_W5_1, with the ROM
   bound ONLY from the GEN's die_rom_bind (full-die audit PASS: 768 tiles, 7,680 macros, rank-0 masks, 64 hashed). It uses the
   real TP8 rank-0 L0 code ROMs and the QW-REALSTG fixtures, on Verilator 5.050 (ot-epyc5, 26.5 min build, 35.9 GB RSS).
   - MU_NU 1 and MU_NU 4: PASS 64/64 bit-exact at lead 8 / gap 4 and at lead 4 / gap 2. The logs are byte-identical between
     MU_NU 1 and MU_NU 4, so user 0 is identical on the MU build.
   - NOBIND mutant: FAILS at cycle 0 (`ot_qwen_tile_romleaf: invalid ROMleaf binding`).
   - Measured edges from hr go: column go 16, first rs 181 (dv2f16 XT1rb: 142; +39 from the dv2f18 cluster: regional resets
     and c_land). Final words: qkv 237..244, o 189..228 (period 16), gu 429..436, down 221..324 (period 48).
   - STAND-INS: hr / x stream driven at the slice pins (no tt_ctlm, no die relays); one of 48 clusters; rs_i idle; single
     user. 4-user operands are not possible yet (no MU lowering of ME x/o regions, no per-user goldens).
2. D2D pair: results/rtl/xdie_qwen_1018/pair_mu_r1 (RUN.txt there). It PASSES, 62 exposed/layer, but both TXDPs the GEN binds
   FAIL.
3. 4-user D2D: `d2d_overlap.json` (tools/qwen_static_schedule/mu_d2d_overlap.py). 968 of 1,655 adjacent user exchanges
   overlap. With the one-playhead ot_qwen_d2d_cal, the frame drops to 9,834 tok/s (-28%; users 2 and 3 run at 298 tok/s).
