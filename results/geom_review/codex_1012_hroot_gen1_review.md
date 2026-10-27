# Hroot gen1 corrected native/reset trial — FAIL structural

Exact epyc2 and intel2:/srv/opentallas-scratch2/claude/codex-kv-physical-prep-1027/gen1/kv3_hroot/run/results/asap7/dp_kv3_hroot/base/3_place.odb, source4ce8ecabf6. Read-only review, no route/STA/P&R launched.

Full connected all-timed DFF input graph including synchronous reset/SET/enable:9115FF,10949timedinputs,15819pairs,max1407.672um,2544pairs>405um,0loops. All32152COREstandardcells have compatible rowrails.4320nonPGpins,0missing. Pin-density alsoFAIL: S111/10um=11.1 atx877.536..887.520 (ft2_o family), E63/10um=6.3 aty261.672..271.656 (ft2_i family).

Personally viewed exact actual placement render codex_1012_hroot_gen1.png. No macros; centre remains open and FT stage bands are explicit, but ordinary sidecar/control paths cross fromE toS without localized stages. Worst idsrc_Q_y/q[1] at(1895.832,440.505) to idhr_Q_y/q[1] at(923.670,4.995)1407.672um. Fault aggregation fch_pc_Q_N_q/eq at(873.342,4.455) to u_u_efault.fault at(1813.104,383.535)1318.842um. Ordinary u_rly.g_c[73] ->g[73]1223.802um and many relay siblings also fail. Native binding/local reset fixes do not solve these data/control reach paths.

Root coverage/QK owners notified immediately. Keep old and new hroot route rows held. Coherent plan/interface/placement repair must cover ordinary sidecars, fault aggregation, relay capture pairs and FT pin demand, not just station-chain hops or reset-grid reach. Existing source/LEC/reset accomplishments remain separate; no blanket rollback proposed. Exact alltimed result and pin receipt accompany image. No new probe requested.
