KDIE5-RTL2 10-22: KV static schedule + KV token (phase-launch) bench with ALL release structural flags, source codex/kvgen-2140-1022@128b91501.
Inputs: relm die ages/flags (kdie5-rtl lc_in: die_ages_fwd.json, kv_flags.env), OT_KV_RETIRE_LOGICAL=1 (LOGICAL_ONLY retire contract, NOT a release
contract), --no-mu (kv_frame_search fails on main for every setting = KV-PROG17 blocker 3, pre-existing).
Variants (compile_variant.sh): base | grp (GRP_R2 + GRP_R2_NATIVE32) | ctl (CTL_C32=2 + CTL_NC32) | full (grp + ctl + POR_LOCK=1).
Real cycles: groups age 68 -> 97 (+29), kgo_event 267 -> 238, ownership leave 249948 -> 249950 (ctl +2) / 249979 (grp +31) / 249981 (full +33);
token cycles 254386 and period 258048 UNCHANGED in every variant; 0 group calendar changes; phase launch outside window 0.
Phase-launch token bench (iverilog, actual qkd_static_kv_phase_launch, 3 tokens x 72 launches): base PASS, full PASS; launch table byte-identical;
negative controls unpadded / unaligned FAIL in both.
Not priced: ctl MAIN kit qkd_kvs_ctl_nc32m pin registers (+1 in / +1 out except o_hroot_*): kv_tile_views charges 0/0, so a nc32m view is
REFUSED at bind; the FB kit qkd_kvs_ctl_nc32f (0 edges) is the bindable ctl form. DSTG boot write +1 = host boot boundary (elastic), no static consumer.
