# S81-LEPFLF-HOLD handoff (Opus 5.5; updated 11-24 01:03 PST). One job: lepe_mu_LP t2 f_lf[2] hold -11.86 (from S81-OPEN-DEMAND).
## Measured
- Kit FAM-S81-LEPE-4 _1122050440 (epyc7) GRT FF hold -11.86: launch hard core u_u_lnl1 k_st[1] (ck_k = clk_c4, rising flop
  in ot_pl_land_local_r), zero logic, pins ~6 um apart (5_1_grt.odb), capture clk_t34. Net and insts NOT dont_touch. All 3
  repair chunks hit the 200-buffer cap (RSZ-0060). Why this endpoint was skipped: NOT established.
- My STA (E7 s81-lepflf-hold/dt, no SPEF/derate) does NOT reproduce: FF +5.3, TT -64.1, setup +720/+780. Uncalibrated.
## Candidate LEPFLF-LFNEG-1 (NOT ROW-REBASED)
- RTL OT_SL81SL_LEP_LFNEG neg pre-stage: main f9681588a5 + comment fix 6eed04f985. Tree copy v2 E9 row/ot_s81sl_slice_lep_v2.sv
  (a2282728); ops E9 row/ops_lepflf_lfneg_v2.json.
- LEC: extracted 4-bit block only, rising-launch assumed: k-induction SUCCESS, mutant FAIL. Bench hab P_PROD 0/1 PASS, f_lf
  trace identical (3 values only = weak). INERT pass.
- PRE introduces 0 (147=147, c7a base). Elab rc 0. Scoped strict rc 1 on inherited dn_s_3N_L3 fixed_cycles (not my row).
- Define scope: KIT, only mu_LP t2 requests; hunk under HOST_EN!=0 -> only s_7N hab_tp. RIP: kit 3; bind 0 by macro (unconfirmed).
## Next
Re-run scoped strict once INT fixes dn_s_3N_L3; read c8 mu_LP t2 probe (if f_lf[2] >= 0 -> report + stop); real-flow STA of LFNEG needs a kit.
