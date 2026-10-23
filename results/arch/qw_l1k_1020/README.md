# QW-L1K 10-20: KV seam on the canonical KV table + reset release into foreign clocks

## 1. Q.MU.L1K: KV seam source binding (l1k_compile/)
- Canonical KV production table = KV die d22bu (`kvs14r-ccc9418ac-gen9d22bu`, ep5) `relay_stages_netlist.json.gz`
  (netlist export of the strict-bound die: STRICT PORT BIND v2 PASS 69 masters / 46061 inst), sha256 af4547b0...7d407e.
  This replaces the diagnostic `tablec4c3` export and the stale kvs14c table that g5r2b phase2 compiled against.
- Compute side = g5r2b (`mu-die-qw/dv2f20g5r2b/p2`: netlist relay table 643 buses / 1063 relays, die.v, params, lanes; GEN src
  cfc5a82ac).  Job oth-ubuntu-3782693-1792564702 (ep6), script `l1k_compile.sh` (OT_GIT_SHOW_CACHE with the
  ccc9418ac + cfc5a82ac files).
- RESULT: layer_compile rc 0; RELAY_CHECK compute PASS (643 buses) and KV PASS (53903 buses); TXDP C [8,3,1,10] = the
  bound compute TXDP 0x0a010308 (no TXDP C finding); the stale-table torn K bundles (K.rx_record / tx_slot / tx_record) are
  gone.  Open, both outside the compute source binding:
  - TXDP K: the d22bu plan needs K [24,4,3,3] (KS_RXV/RXP 13, SK 11) while the pair contract is K22 (0x03030416).  KV-side
    fix = OT_KV_SEAM_PIN (KV-D2D3, d24pb SEAM_PIN PASS 11/9/9) -> K.* tree.
  - the g5r2b GEN source cfc5a82ac still carries the OLD pair image d2d_cal_image(_mu).svh TXDP_K 0x03030415 [21] and
    the old C_RX_IMG; main (6c8b3c908) and the KV die bind K22 0x03030416.  The next compute GEN must take main's pair
    images (and the sys_face successor n32ob on ca3ab89c1 already includes 6c8b3c908); otherwise the pair faults at the
    first token.
- Re-run when the KV strict chain with SEAM_PIN binds: same script, swap the KV table; pass = no TXDP K finding.

## 2. Q.STA.GEN.7: reset release into foreign clocks (reset_release/, tool tools/die_safety/reset_release_check.py)
- Rule: COORD 10-20 21:29 (c) + owner CLOCK RULE 08:55 -- reset crossings between regions land in each region's own
  clock.  The tool judges (a) STRUCTURE from die.v (every reset-tree hop driver->load; FOREIGN = driver clock region not
  among the load's regions and the load is neither a landing ring nor a synchroniser async input; regions = die-level
  clock nets, one per regional tree) and (b) die STA (TT setup / FF hold summary reports): failing paths launched by
  reset-tree flops into another region = RESET_XREG.  Both must be 0.
- g5 (terminal, diagnostic): static FOREIGN 3980 (cross-checks qwen_landed_pairs RESET_ROOT 3940); STA TT RESET_XREG
  571 paths, worst -9036.3 ps (= the die WNS; rstt_rst_d2d -> rly_lnk_fwd_epoch en); FF hold RESET_XREG 1618, worst
  -7350.6 ps.  Families: rstt_rst_field -> qfd_rst_rep/_p8 (n_clk_r97 -> n_clk_r691 type hops, -7772 ps), -> qfd_c_b16_dv,
  -> qfd_landh0_* en; rst_seq_ctlm; rst_io -> SerDes/UCIe PHY rst_n.
- g5r2b (current release die, pre-STA): static FOREIGN 3520 (rst_field 2994 + 449 into qfd_c_b16_dv, rst_seq_ctlm 24,
  rst_io 7, rs_bump 1), LANDED 820, INTRA 11431.  The chain's STA will show the same class: GEN defect.
- Gap: qwen_landed_pairs counts RESET_ROOT but QCLK_REGIONAL does not owe it, and gen_check C1 has no reset class, so
  the die chain does not fail on it today.
- GEN fix (QW-G5RELAUNCH call): either (S) the generator re-clocks each foreign-region tree hop onto the receiving
  region and declares the qfd_rst_rep d pin a synchroniser input (reset_sync_contract path that already exists for
  foreign PHY clocks; the tree level is held >= tree depth, and consumers anchor on boot_done / epoch, never on the reset
  edge; +-1 edge per crossing must stay inside the reset_calendar_audit release windows), or (R) per-region landing:
  a forwarded reset lane (qfd_rlyr stations) landed once per region (qfd_rlyrl) feeding an intra-region tree.
