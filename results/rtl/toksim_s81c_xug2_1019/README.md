# TOKSIM-S81C/XUG2: XDIE job u (MU 1) on the fluid guard-2 deadline model (2026-10-19 23:11 PT)
- Stage ot-epyc5:/srv/opentallas-scratch/claude/xdie-s81-mu/stage (MU release die RTL mu3 ceaed19c4, Verilator 5.050).
- Script: tools/xdie_s81_2/gate_mu_u_g2.sh out_u5. Goldens: goldens_g2/{ar46r,ar46d,mtp10r,mtp10d}, generated in-job with
  gen_golden.py --gap 100 --dl-model fluid --fluid-guard 2 and the original mu args. The args were proven first: at guard 1
  they reproduce goldens/<g> byte-identically (GEN_ARGS_OK x4 in xdie_u5.otrun.start.log).
  - ar46r: --mu-users 46 --mu-mode real --mu-cal cal_ar_q4.json (last issue 972966 -> 972967)
  - ar46d: --mu-users 46 --mu-mode dense (104079 -> 104125)
  - mtp10r: --mu-users 10 --mu-mode real --mu-cal cal_mtp_q4.json (1134570 -> 1134571)
  - mtp10d: --mu-users 10 --mu-mode dense (31899 -> 31909)
  - su: existing goldens_g2/su (S81-TOK4).
- Build bU: fresh, MU 1, same defines as gate_mu.sh u. Runs u_su, u_ar46r, u_ar46d, u_ar46d_err (+ERRP=7), u_mtp10r and
  u_mtp10d, each followed by mu_check --win 3.
- Job: ot-run unit oth-ubuntu-554994-1792476654 on ot-epyc5, --mem 200. Runs in parallel with the guard-1 out_u4 on ot-epyc7.
- Expected: bench PASS, WIN_PASS (win 3) and INV_PASS on every u_* run. Results: ot-epyc5:/srv/opentallas-scratch/claude/xdie-s81-mu/stage/out_u5/{u_*.txt,u_*.chk.json,DONE_u_g2}.
