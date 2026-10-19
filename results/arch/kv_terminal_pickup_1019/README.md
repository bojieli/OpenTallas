# KV terminal pickup, 2026-10-19 10:25 PT

ATTN ba4 original run is terminal; exact frozen execution recovered without physical rerun. Gate WARN does not qualify release. No REVIEW.json, submission, routing, source modification, or edits in original gate worktrees.

Source: 805aa57cb778d24e6a300873f9997ab272485c8d; original ot-epyc8 /srv/opentallas-scratch/claude/ref_gate/qkd_kvs_attn_ba4-20261019-093014; script /tmp/ref_gate_qkd_kvs_attn_ba4_20261019-093014.sh. Original snapshot manifest ae2573eabea607d7a81b5ad0ed344ffd027e88b2db706ac7403c220efc041c21. Original SCRIPT_RC=0 / GATE_DONE. Frozen helper recovery verifies executed source bytes and committed helpers. Compressed full gate receipt retains source identity, not inferred HEAD.

Critical review checklist, PNGs viewed:

- Pins: full faces, 3284 actual signal/clock pins passed geometry/track checks; rendered all-pin counts S548/N1080/W1110/E768 across 302.4um, maximum3.70/um. Outputs registered; RX status_nonzero input has4logic levels before register. Reset external landing2stages/max2loads PASS, internal source reset limit32 NOT demonstrated; kit still requests split256.
- Reach: original textbook placement estimate118.8um/0violations under legacy500um threshold. No complete actual native <=405um path census obtained.
- Fanout FAIL owner32: original mapped source textbook collapsed-buffer census fin[0]Q1038loads, codec.tx_expected_kind529, i_ctl[34]Q436, cal.v9Q259/v8Q257. Original permissive hfmax3000/hfrefuse50000 explains WARN with no refusal. Unconditional548TXcapture alone does not repair these source drivers. Exact internal reset32 census remains owed.
- Depth:518.4ps/14logic levels worst internal stage; boundary status4levels remains warned. No combinational input-output paths.
- Storage: no macros;5840mapped FF. This pickup changes no storage or schedule.
- Floorplan:302.4square, macro lattice N/A, no islands. Actual std fill3.1% before CTS/6.2% after; observed mass chiefly west edge with sparse interior, not one dense full-width band. Pin-bound perimeter does not itself prove approved measured band capacity/occupancy.
- Clock: center south pin; observed west-side mass distant.5840sourceclock FF/6205CTS sinks; TT boundary439.0..489.8(mean459.4), FF353.7..401.4(mean372.4); spreads50.8/47.7PASS80. Absolute native launch<=220/capture<=190 audit and parent matching are outstanding.
- Timing: original TT placement-RC diagnostic setup-1.430ps/hold-16.707ps. This is not signoff TTsetup/FFhold evidence. Trial GRT0overflow; worstlayerM2 11.45%/total7.07%; original GRT156s. No qualified FF data hold result.
- Schedule: source ba4 retains valid-only same-edge TX behavior and codec2 contract; source tests belong to original805aa57cb. Parent full-face S/W coordinate/reach/calendar regrant remains required.

Preserve progressing original jobs, no duplicate:

- CTLmu4safe e00f75155 original ot-epyc5 run080131: bash1403939, OpenROAD1561078;10:23repair24110, WNS-91.052ps/TNS-1523.451ps, o_hroot_WS[1109]D. Original local client gone; remote writer LIVE.
- GRP sq1 cf5150d12 original ot-epyc8 run080306: bash2052101/docker2168717/OpenROAD3099868 LIVE,10:24repair390/WNS-74.905/TNS-3442.554ps,y__tep[0].
- GRP_H sq1 same source/run: bash2051890/docker2163765/OpenROAD3012657 LIVE,10:24repair670/WNS-74.905/TNS-2621.568ps,y__tep[12].

No current closure/adoption claim. Structural source fanout repair and actual native/FF timing evidence are required before any successor gate approval.
