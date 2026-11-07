# Independent geometry reviews, Codex12:09 takeover

Actual existing PLACE images viewed2026-11-07; no new physical probe or route was launched for these reviews. Figures are from each existing auto_geom.json, not fresh STA. The queued routes remain governed by existing stop rules.

## QC cbf_q01 attempt10

Image qc_cbf_q01_a10.png, E5 kw26-wave-1106/runs/qwen_compute/kit-wave/qwen_compute/efdb36e864/items/cbf_q01/attempt_10/geom/auto_geom.png. Four NK macros occupy67.57% of1235.52×2540.16um. Logic runs through narrow perimeter/central channels, with dense clock entries near channel intersections. Low3.23% standard-cell fill alone does not justify shrinking a macro-dominated type.

GEOMETRY: actual report finds4145 captures beyond405um, worst2833.33um u_bound.u_rrl_41/q→u_bound.u_cland_reset_rst_n_t27/q. START input boundary capture1262.88um;1407 collapsed relay chains. Channel-demand1.05H/1.83V are estimates, not measured congestion; GRT not complete in this receipt. PreCTS1959.55um own-clock-driver distance is a structural warning, not measured clock insertion. No std cells on macros; pin layer counts alone do not violate6/um.

SMELLS:3,4,6,7,10. CLASS: RESET/START reach and channel crossings. VERDICT: redesign before any new route release. REDESIGN: local phase-coherent START/reset relay origins beside actual destination banks, preserved coherent stage/epoch pricing; restore staged relay locality through available macro channels. Review latest native collector/START source form before duplicating it. QC lead owns next action; existing enqueued route was not stopped.

## KV kv3_sys_SD_v1 attempt12

Image kv_sys_SD_v1_a12.png, I1 kw25-wave-1106/runs/qwen_kvsys/kit-wave/qwen_kvsys/event28w_c/items/kv3_sys_SD_v1/attempt_12/geom/auto_geom.png. One PHY macro occupies91.19% of1900.8×1036.8um; soft logic lies along bottom/east edges. This is not empty free area available for a generic compact resize.

GEOMETRY: actual report finds1639 captures beyond405um, worst1754.62um u_bound.u_cland_origin/s1→u_bound.u_cland_fstart_o_serdes_E_tx_up/q. START input capture1170.43um. SW root→east destination preCTSclock leg2551.97um needs local distribution, not inference about final CTS. Nearest-entry201.39um does not describe the actual assigned driver. ExistingGRTprobe has0overflow, so estimated1.795H/1.156Vchannel ratios are not reported as routing congestion failures. Zero collapsed relays and zero std cells on macro.

SMELLS:3,4,6,7,10. CLASS: control/START reach around PHY macro. VERDICT: redesign before any new route release. REDESIGN: coherent staged START/reset along bottom/east channels, local destination origins and clocks, with native PMA clock/reset contract retained. No pin inventory waiver, invented timing guarantee or PHY interior placement. KV lead owns next action; existing queued route untouched.

## HBM F512 vCF1d routed placement (5_route)
Actual local /tmp/codex-hbm-1209/f512_route_logic.png viewed independently. CORRECTION: the producer found inherited hview.sh selects ls|head, so this image is 5_route placement, not the claimed 6_final. Observations below apply to that stage. A fresh explicitly selected 6_final image is owned by HBM; no STA/proof rerun is needed. Three central macros, dense southface and west/east logic clusters, sparse north. Logic-onlydensitymax.794/p99.679 fromproducer, image has20bins>.7; no pin-to-flopflight>100um. Congestion is explicitly NOTloaded, finalDRC0; no overflow claim. CLASS data-depth/driver-wire+regionalclockalignment. Reported actualinternal wq_d278→s1w_m7 includes AO22x1 215.77ps plusBUFx10wire210.26ps, so a further input-registercyclealone does not split that internalcone. REDESIGN recommendation to HBMowner: localize/pipeline preselect/writecone with coherentcontrol/read-writepricing, clockfollowingthoseactualregions. NOECO/newrouteclearance.
