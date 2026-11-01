# Independent HEAD l48z review, takeover 11:31 PST

All seven actual AUTO-GEOM images were LOOKED and all JSON parsed. Source evidence is intel2:/srv/opentallas-scratch2/claude/die-head-48/dh53/l48z/geom_l48z/<type>/auto_geom.{json,png}. Original automatic FAIL results remain unchanged. No P&R job was launched by this review.

Three builds are PASS-COND for the existing slot-shape and low-fill exceptions: hd_st_n3_turn, hd_st_n3_transit, hd_spn_wshim_tx. GRT overflow is zero throughout; their maximum register reach is379.62/381.29/349.81um, with zero over405 captures and zero relay collapse. The old turn ready/reset structural failure and transit501um class are fixed in these actual outputs. The turn's diagonal station chains span the N→E turn with intermediate homes; transit has evenly spaced W→E station columns; wshim_tx has three vertical columns and short pin landings. Sparse area follows the adopted parent slots. There are no macros or macro walls. Clock taps follow the columns; tiny root/tap branches are cleanup information. Their0clock-cell pre-CTS clock-reach estimates do not replace the actual CTS leaf/related-pair timing gate. This review permits the next normal physical stage, not a sign-off claim or CTS timing waiver.

The remaining four builds stay HELD for the HEAD owner's current source-fix scope:

|Type|Finding|Geometry implication|
|---|---|---|
|hd_mesh_e|pin_reg_p90=42.59,max119.24; worstcland_fstart_in_m_tx_ft_i and m_tx_ft_i group110–115|The old281um output failure improves substantially; remaining input landing pull is visible at the E edge. Owner is fixing the source class.|
|hd_spn_eshim_tx|p90=89.75,max90.60 on link_o|The output bank remains at the opposite side of the95.04um strip; the percentile represents the strip crossing. Owner is repairing the face landing.|
|hd_spn_eshim_rx|onlycland_fstart_in_link_i=179.15; next worst data pin29.5|One start-register pull remains; wide input/output data banks sit near their faces.|
|hd_spn_wshim_rx|same singlecland_fstart179.15,next29.5|Same start class across the wider slot; intermediate ft columns and taps are coherent.|

All four have GRT0, register reach≤404.41, zero over405 captures, zero collapse, no unregistered pins, and no blocked channels. The09:10 GEOM103/104 joint ruling allowed existing shim forms in parallel under closure-first policy; this report does not revoke that ruling or create a stricter threshold. It records the HEAD owner's explicit hold on these new l48z builds while their source fixes are made. No new waiver or blanket route release is issued here. HEAD owns the fixes and supplies the next actual images.

Metrics and preserved image copies are beside this report. No broad validation or rerouting was performed.
