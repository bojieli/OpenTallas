HBM-MU-QUAD-3 task 5: planU2 SU UPPER loss decomposition (model only; written $(date) by QUAD-3 fork)
Model: combine.py upper = lane delta + cc_price "upper" = per op family the LONGEST directed module-pair path, summing per-leg
register deltas (len(regs)+serial_k-1 vs t_banks baseline, max over replica copies, edges unioned over NW+NE hubs). mid = lane + cc lower (max single leg).
whatif_cc.py asis reproduces U2_cc.json ops exactly (CHECKED).
marginal_U2.json (marginal.py): ds_ar upper 7.882; flipping ONE op upper->lower on top of all-upper:
  SM.*|ATT.* cc 12->42 adds 3.791 pp (1095 SM.MATVEC + 80 ATT); upper with SM at lower = 4.631 % (PASS). SU.* 8->15 +1.014, COLL +0.493, DMA 12->34 +0.295.
SM path (paths_U2.json, q_hub_nw): aqhi->xq_p0_bd->aqlo->xq_p1_bd->p1_eg->p1_bfq2->xl_ctl->xq_p0_bfq1->p0_eg->p0_bfq0 = +42
  (serial_k k-1 = 15, register growth = 27; biggest xl_ctl.c_mhi->xq_p0_bfq1 1->12 regs 605->3825 um, xq_p1_bfq2.c_d->xl_ctl 4->12 regs 1230->3919 um).
Geometry cause: quad packing moved the replicated VM services (xl_ctl, hb_dbk, hb_vms, calendar ... __q0/__q1) to the quad service column at hub y~846,
  their non-bank partners (xq_*, wbk, vmks, ctl_p0x) sit above the 2644-um quad at y~3480-4090 -> every service<->partner leg crosses the quad
  (dbk.wd->wbk 1156 b 657->4326 um 1->13; vmks_Q1->ctl_p04 854->4365 um 2->14 k3). In-quad bank legs also stretch (vms->vmb_Q6 496->2881 um 1->9).
What-ifs (price_*.json, ds_ar lower/mid/upper %):  coloc (all legs grown >1000 um back to base+k-1, ideal) 0.592/0.424/3.161
  noserial (all serial_k dropped) 2.012/2.239/5.013;  xlctl only 2.388/2.668/6.823;  partners (svc<->non-bank + vmks<->ctl) 2.334/2.614/5.738
  partners + xq/xl legs k=1 (NOSER=u_x[lq]_Q)  2.334/2.614/4.737 = 1982.2 tok/s  -> PASS 5 % + 1973 (UNCHECKED model what-if, CHECKED arithmetic).
