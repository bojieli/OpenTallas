# QC token cost of the v7 CB16 phase candidate (TOK-QK-QCV7, 2026-10-25 23:41 PDT)

Source: claude/tok-qk-qcv7-1025@5832e6722 = main cfea7b3a1 + codex/qc-phase-2209@13f33606a (v7: strict PASS 377 parts / 79 types, 0 errors).

## Result (cycles per token, 1 user, 36 layers, composer toksim_compose.py at the QCL measured-age tree)
| case | cycles/token | tok/s | chained/layer | L0 cold |
|---|---|---|---|---|
| frozen plan 441d1401 base R8 (QCL measured ages, reproduced exactly) | 288,025 | 4,168.0 | 7,898 | 8,410 |
| v7 final bind (this qualification) | **289,321** | **4,149.3** | 7,934 | 8,446 |
| price of record (results/arch/token_path_1018) | 249,431 | 4,810.9 | | |

Delta v7 vs frozen 441: **+1,296 cycles/token (+0.45 %)** = +9 cycles per matvec pass x 4 matvecs x 36 layers.
- CB16 phase pads alone (v7 base -> v7 final): **+0** on the critical path (cluster roots +1 on 12 clusters, 6 -> 7, below the max 8).
- All +9 comes from the v7 physical pipeline stages (405-um hops) already in the v7 priced base: x broadcast bc/bcf lanes +4 (Max),
  hc cws/cwn x-in lanes +1..+4, tree a/b lanes, root->slice rs lanes +2. Max-path (x-in -> c16 root -> slice rs): 441 = 7, v7 base = 16, v7 final = 16.
- Other changed lane class: sl_*_su_l*__flt -8 (fault lane, not on the token path). No other lane of the 1918 differs.

## Method
1. cb16_path.json: roots.py (cb16_dag.baseline from codex/qc-phase-2209, per cluster root phase + rs lane added stages from bind_sinks)
   on the three binds, run via ot-run (units oth-ubuntu-1185339-1792996747 epyc1, -996795/-996792-1792996722 intel1). Reproduces Codex
   cluster_output_delta (base 8/6/-7, final 8/7/-7).
2. lane_delta.py on bus_groups_{ref441,v7base,v7}.json.gz (committed here): per-lane landed-stage deltas by class.
3. compose_edges.py = TOK-QK-QCL compose.py + one appended ledger die edge (edges_v7_vs_441.json: +9 at pre_qkv/pre_o/pre_gu/pre_down);
   run.sh via ot-run intel2 unit oth-ubuntu-4006188-1792996857: q_none.json (288025, identical to QCL measured.json) and q_v7_vs_441.json.

## Not qualified / scope
- The composer's own ledger die edges (g5r2b landings, slice2 536) are still the 10-20 PRICED list, not re-derived from the 441 or v7 bind;
  this receipt prices the bind-relative v7 delta only. No RTL stage rerun was needed: no slice/vec/stn stage-internal age changed (only die lanes).
- Bind inputs (runtime dirs) are named above; their bus_groups are committed here gz. The full bind_sinks (240-270 MB) are not committed.
- No whole-die RTL token run on the v7 bind; native hard views / G2 / clock-provider ownership remain open (Codex README).

# Re-derived die edges + lane ages on the 441 / v7 binds (TOK-QK-QCE, 2026-10-26)

The 10-20 ledger's die-scope edges and lane ages were priced on the old dv2f20g5r2b GEN die. Here they are re-derived from
the committed bus_groups of the two binds and REPLACE the 10-20 values (they are not appended).
`rederive_edges.py BUS_GROUPS TAG [--clamp]` writes `edges_<TAG>_rederived.json`, `lane_ages_<TAG>_rederived.json` and
`rederive_<TAG>.txt`, which holds the per-edge table with lane names and as-built -> landed stages.
`compose_edges.py ... --replace EDGES LANE_AGES|-` drops every scope 'die' ledger edge, adds the re-derived list, and
points the ledger's lane_ages at the replacement file. `run_qce.sh` runs all cases.

## Result (cycles per token, 1 user, 36 layers; ot-run intel2 unit oth-ubuntu-1040392-1793000384)
| case | 441 base R8 | v7 final | v7 - 441 |
|---|---|---|---|
| control: 10-20 ledger (= QCL / QCV7 q_none) | 288,025 (4,168.0 tok/s) | | |
| **re-derived (law)** | **295,045 (4,068.8 tok/s)** | **296,341 (4,051.0 tok/s)** | **+1,296 (+0.44 %)** |
| re-derived, clamped (no die edge < 0, no lane age below 10-20) | 297,709 (4,032.4) | 299,005 (4,014.9) | +1,296 |
| re-derived edges, 10-20 lane ages kept | 296,629 (4,047.1) | 297,925 (4,029.5) | +1,296 |

Per layer chained, law case: 441 = 8,093, v7 = 8,129 (control 7,898). Die edges per layer, counting each edge once per
boundary: 10-20 = 820, 441 = 1,059, v7 = 1,095 (plus 114 of successor edges in every case). The v7 cost over 441 is
unchanged at +9 per matvec pass. The absolute cost goes up about +7.0k cycles/token, mostly from the slice partition crossings.

## Laws
- **Lane age** R = landed register stages of the bind lane, pin to pin. This is the same quantity as g5r2b's E + 1:
  relay edges plus the landing o register, all flops between the same two pins.
- **Die edge** = cycles the bound die adds over the RTL the ages were measured on = landed - asbuilt
  (the bind.py / r8.py OFFSET).
  - The QCL ages ran on the as-built s8 slice row (tb_qfd_dv2 FACE 3, tools/qwen_tokfunc/s8die_srcs.py).
  - That row is the as-built netlist of these binds: bound_r8 replaces qfd_dv_slice2 with qfd_dv_s8_flat.

## Per edge (10-20 -> 441 / v7; evidence in rederive_{ref441,v7}.txt)
| 10-20 ledger item | 10-20 | 441 | v7 | v7 lanes / law |
|---|---|---|---|---|
| R_CMD / R_HR (tt_ctlm -> W5 cmd_i / hr_i) | 20 / 20 | 9 / 9 | 9 / 9 | tt_ctlm__cmd_cmd_wi, tt_ctlm__hr_hr_wi asbuilt 27 -> landed 9 |
| R_SS / R_AG (W5 -> tt_ctlm ss5 / ag5) | 17 / 18 | 5 / 5 | 5 / 5 | sl_W5_fw__ss_wo_ss5, __ag_wo_ag5: 25 -> 5 |
| R_ST (tt_ctlm.tl -> W5 st_up_i) | 13 | 5 | 5 | tt_ctlm__tl_st_wi: 23 -> 5 |
| R_DD / R_DR / R_CTX (not read by ctlm_image) | 20 / 21 / 7 | 5 / 5 / 10 | 5 / 5 / 10 | sl_W5_fw__dd_wo_dd_i 28->5, native59__dr_o_dr_wi 30->5, glue__ctx_x_ctx_x 5->10 |
| XPF_TRANSPORT_EDGES = 1 + R_HR | 21 | 10 | 10 | lane_ages_export.py rule |
| q3h x broadcast (+6 @qkv,gu) + rs reduction (+6 @qk,silu) | 24/layer | 7 x 4 = 28 | 16 x 4 = 64 | REPLACED by the CB16 path x-in -> c16 root -> slice rs (cb16_path.json max_root_plus_rs), on every matvec pass (qkv, o, gu, down); no double count |
| dv chain slice<->slice hops @pre_r2 | 33 | 0 | 0 | inter-slice fe->fw / fw->fe lanes (cmd/hr/dr/st/ag/...) as-built 2 -> landed 2 (W0->E0 3 -> 3) |
| native59 split service @pre_attn | 5 | 5 | 5 | inside the native59 partition, no die lane: 10-20 value kept |
| NEW tt_ctlm.native_cmd -> native59 @pre_attn | - | 3 | 3 | tt_ctlm__native_cmd_native_cmd 0 -> 3 (was a 0-stage connection) |
| NEW native59.native_ret -> tt_ctlm @pre_o | - | 2 | 2 | native59__native_ret_native_ret 0 -> 2 (priced serial, as the ctlm8 native_ret edge) |
| attention return dr (R_DR - dh2 20) @pre_o | 1 | -15 | -15 | native59__dr_o_dr_wi landed 5 (clamped: 0) |
| attention send dd (R_DD - dh2 20) @pre_attn | 0 | -15 | -15 | sl_W5_fw__dd_wo_dd_i landed 5 (10-20: unchanged = 0; clamped: 0) |
| slice2 landed-parent forwarded lanes + taps @pre_r2 | 536 (plan 327) | 796 | 796 | QW-SLICE5 law (b1a5accf4 slice5_partition.py) on the s8 partition crossings; see below |
| NEW qkv L9 pair word @pre_qk | - (listed +3, not summed) | 34 | 34 | st_a->fe l#_c +12, fe->fw l9 +14 (sl_E{1,3,5}_fe__l9_eo_l9_wi 2 -> 16), fw->st nb_d +8 |
| forwarded-lane class views | 0 | 0 | 0 | R8 replica_unequal 0 |
| XDIE pair link (X + STATUS tail 213) @pre_o | 221 (L0 -1) | 221 (L0 -1) | 221 (L0 -1) | TOK-QK-XD2 004bfaf96 qc_kv_link_v7_1025: X 8, L0_X -214, period 7056 (unchanged) |

The slice2 term is 796 = pass 600 + taps 196.
- **Pass.** 10 hops x (st 2 x 6 + ch 2 x 12 + sc 4 x 6). Per-slice pass costs:
  - st: through stm, fw->stm sw_i +2 plus stm->fe st_up_c +4 (down direction 4 + 2).
  - ch: fw->fe chr_c +12; fe->fw chu_q is +6, and the max of the two is taken.
  - sc: fw->sc +4 plus sc->fe +2.
- **Taps.** 2 x (x 21 + ar 31 + mv 24 + norm 19) + su 6.
  - x: su_l->stm vm_w +10, fw->stm +2, stm->ctl xt +2, ctl->hc a_d +7. The cw corridor is left out because it is in CB16.
  - ar: st_a->ctl r_d +12, ctl->fw own_ch +7, fw->ctl chd_q +12.
  - mv: in-slice rs continuation +6, station->ctl +12, ctl->su_c +6.
  - norm: su_c->sc red +7, fw->sc +4, sc->ctl->su_c w1 2+6.
  - su: ctl->su_c +6.
- The intra-slice lanes are identical on 441 and v7 (lane_delta_441_vs_v7.txt), so these terms cancel in the delta.

## Inputs, scope, open
- QCL ages, sha256:
  - slice_ages 2cf49539...dd982
  - vec_ages a157bc40...89edd
  - stn_ages 32cf9e3d...4b673
  - vflags dc8251bb...c4d24
- The engine tree is the same as QCV7: git archive 94cd97b7a plus the compose_edges.py overlay. run_qce.sh only records the run host paths.
- Not derived:
  - (a) The SU lane crossings su_c<->su_l* (+2 issue, +2/+10 return), which hit each SU command. The 10-20 law kept the
    lanes inside r_su (LOCAL 0), and the s8 ages are the SU8 re-measurement. If the bound top adds them per SU command,
    that term is owed to a bound-row bench.
  - (b) The per-slice cmd pass fw->fe cmd_q +12 is not on the 10-20 pass list, because commands are issued ahead by the static schedule.
  - (c) The ch pass is priced as one direction per AR (the 10-20 law), with the max of up and down.
  - (d) The attention round trip term (1827) is kept. TOK-QK-XD2 measured roundtrip 1933 (+46) but an unchanged period
    7056, X 8: the extra fits inside the layer slack.
- No whole-die RTL token run on the bound top. The R values assume full-cycle plan stages (405-um hops). Either choice
  for the negative dr/dd edges is bracketed by the clamped row.
