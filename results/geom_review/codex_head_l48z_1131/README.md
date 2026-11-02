# Independent HEAD l48z actual geometry review, takeover11:31 PST

All seven actual AUTO-GEOM images LOOKED; all JSON parsed. Source evidence intel2:/srv/opentallas-scratch2/claude/die-head-48/dh53/l48z/geom_l48z/<type>/auto_geom.{json,png}. Original automatic FAIL results remain unchanged. No physical job launched by this reviewer.

Six builds are PASS-COND for the next normal physical stage under existing authorization:

|Type|Actual reach|Existing basis|
|---|---:|---|
|hd_st_n3_turn|379.62um,0over405|Only adopted-slot shape and fill/empty exceptions; old1183um ready/reset class is fixed.|
|hd_st_n3_transit|381.29um,0over405|Same standing exceptions; old501um class is fixed.|
|hd_spn_wshim_tx|349.81um,0over405|Only fill/empty exceptions.|
|hd_spn_eshim_tx|363.69um,0over405|GEOM103/104 joint09:10 authorization explicitly permits existing native shim output bank90um across95um strip in parallel; source fix can supersede.|
|hd_spn_eshim_rx|375.95um,0over405|Same09:10 authorization for singleFSTART179um, next data pin29.5; no new waiver.|
|hd_spn_wshim_rx|369.63um,0over405|Same singleFSTART class and authorization.|

All seven have GRT0, zero relay collapse/unregistered pins/blocked channels, and no macros. Turn diagonal station chains follow the N→E dataflow; transit has evenly spaced W→E station columns; wshim_tx has three coherent columns and short landings. Sparse area follows adopted slots. Clock taps follow columns/load islands; small taps remain cleanup information. Zero-clock-cell pre-CTS clock estimates do not replace actual CTS leaf reach, related-pair skew or timing gates. None of this is a timing/sign-off claim.

hd_mesh_e remains HELD for its input landing-ring packing/setback: total pin_reg_p9042.59,max119.24, with a group of m_tx_ft_i inputs roughly100um from its E pins. Actual ring capture bbox[728.784,17.28,820.8,34.29] matches the declared band[727.92,17.28,820.8,43.28]. Example m_tx_ft_i[19] pin(837.984,16.224) captures stage0 at(737.748,17.955) and stage3 at(729.324,17.955), about102–110um. Data reach404.41 is within405, but HEAD owns this remaining source class; no new mesh route release.

The exact pin/capture trace uses canonical geom_rules.Design plus actual land_slots.json and face_guard.json. For BOTH shimRX forms, FSTART=(2.144,867.232)M7, contract band=[17.28,708.48,47.52,1008.512].2298declared captureFFs occupy actual bbox[17.28,709.02,23.76,1007.91]. Nearest ctl_lap[1] center(17.82,869.265) is17.709um away; farthest s_d[2][565] center(23.22,709.155) is179.153um. This is farthest declared-bank reach, not the first local FSTART flop. A uniform+34.56Y bank shift would worsen max to196.179; optimal Y-only shift+8.767 still170.386. Any future geometric repair must reshape the bank rather than add an unnecessary pipeline edge for this percentile proxy; current parallel route authorization remains exactly the09:10 ruling.

eshim_tx actual worst link_o[404] pin(94.944,793.848)M4 is driven by u_ft_link_s0/q[404], bbox[4.428,794.34,5.508,794.61], center(4.968,794.475),90.603um away. All566outputFFs occupy bbox[4.428,708.75,7.128,1008.18]. This native common bank also serves W inputs, so translating itE may merely move the pin cost toW; do not introduce a latency edge solely to satisfy the geometric percentile. HEAD confirmed the existing native-shim authorization after this exact diagnosis.

Preserved images, metrics and compressed full machine trace are beside this report. No broad validation, STA or rerouting was performed.
