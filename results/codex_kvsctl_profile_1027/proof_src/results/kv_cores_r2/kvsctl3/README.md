# KV-KVSCTL-3 (10-27): qkd_kvs_ctl landing plan + reset fix + hub_C rebind (RULING KV kvs_ctl bb6d423642)
- (c) 37 u_lprg no-reset regs (w_data/w_zero/w_one -> SRAM wd_in -> rowa/rowb read-back -> p_* compares -> outputs) are
  OBSERVABLE, not dead -> async reset added (qkd_kv_ctl_nc32_face.sv). Isolated lprg round trip on the old RTL PROVED
  27030/27030, so the fp3/fp4 37-unproven is a whole-core proof effect; the kvsctl3 recut rerun (fp/) decides.
- (a) landing plan: 0-cycle retime of 166 bits to face registers (auth digest/epoch 80, layer/layer_e 6+6.. per json,
  i_hroot fault into 8 cfault nodes IN_LAND=1); +1 landing on 305 static sealed config + setup_ready (leaf l_* regs).
- lec_retime.sh: gold = kvsctl2 cut + declared changes (+1 landing regs, w_data reset); gate = kvsctl3 cut.
  91117/91117 PROVEN (lec_retime/). Without the blacklist of the 8 retimed cf2 internal OR nets: 40 unproven, exactly
  those nets (r1), showing the compare is live.
- bind: hub_C u_kvs_ctl rebound to the dead-drop pieces (kvsctl_rebind.py, per-bit same parent nets, 250 dead bits dropped,
  kg unconnected); yosys hierarchy -check rc=0 on kit_rtl.f; 65/65 ports, 1794 input bits all driven, 0 errors (bind/).
- core json + kit_rtl repo-relative (no /srv, /home).
- TOKEN: boot +1 cycle (setup_ready and sealed config land one cycle later); KV latency table unchanged.
