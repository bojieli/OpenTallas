HC-XRDU 2026-10-18 (RELEASE_TREE H.STA.WIRE.8): ot_hbm_hc_root_static with the LANDED root<->hub die links of the GEN2 land smoke
(d4g_hc_xr.py: XRD SW/SE/NW/NE 11/6/11/6, XRU 11/7/10/5 -> XRD 11 XRU 11 XRDQ 32'h060b060b XRUQ 32'h050a070b), rtl/test/run_hbm_hc_root_landed.sh,
Verilator 5.050, ot-epyc5/ot-epyc4 /srv/opentallas-scratch/claude/hc-xrdu.  Driver logs (fail_witness / pass evidence):
  hcxr_m0     root = die values: HC_ENG PASS, 24 mixes / 4 outs bit-exact, HC_MIX_CYCLES 1020 (= 998 + XRD + XRU)
  hcxr_unl    root XRD = XRU = 0 (unlanded kit) on the landed die, ding 2 RAW0 167: HC_ENG_FAULT qf=1010 (SE/NE quarters)
  hcxr_xruse  root XRUQ SE 6, die 7: HC_ENG_FAULT ps=1 (SE subtree sum late)
  hcxr_xrdne  root XRDQ NE 7, die 6: HC_ENG_FAULT qf=1000 (NE quarter: descriptor/ingest early)
  hcxr_mut2   MUT 2 (tail unit 0 eps dropped) on the landed configuration: outbad 16, HC_ENG FAIL
  hcroot_uring0_defaultparams  run_hbm_hc_root_uring.sh m0 on the new RTL/tb at default params: HC_ENG PASS HC_MIX_CYCLES 998 (unchanged)
