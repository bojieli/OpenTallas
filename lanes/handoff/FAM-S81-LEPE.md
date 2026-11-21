# FAM-S81-LEPE handoff (11-21 ~02:00 PST)
Representative dsdv_slice_lepe_mu_LP__t2. Owns lepe family (took over from S81-DIE-R5). Rows: FABLE-FIX-S81-LEPE-RIP1-rows.json, -P8.json.
## Proofs (epyc9 /srv/opentallas-scratch2/claude/fable-lepe)
- opus-p7-r2 (ot-run oth-ubuntu-2673280-1795239086): post-CTS TT -274.56, pre-GRT FF hold -197.98, in hold repair.
- opus-p8-local/r4 = proof7b P8 form (oth-ubuntu-2964461-1795239748): placed-hop gate PASS, post-CTS TT -245.46, FF -227.50, in hold repair. GRT result pending.
- Background waiter: local task running ot-wait on both units (lane FAM-S81-LEPE). Post-GRT: read setup/hold, post.
## STA classes on 7b (fam-sta7b/setup3000.json, 1295 neg ends)
rop->roq 1104-bit face hop -184; rx_mem rd_out->f_host/rid/ml_wd -166; lnl k_li_d->rx dq (424) -116; rid->ri -112; lpad_coll->lnl n_st -245 (4); reset relay -133 (fixed).
## NEXT (proof8 on r4): stations rop->roq; registered rx_mem read; D1 on k_li_d; run tb_s81sl_lep with extra cycles first. Then carry to lepe_nh_mus_LP t1, lepw_mu_LP t2, lepw_mus_LP t2, lepw_mu_C.
