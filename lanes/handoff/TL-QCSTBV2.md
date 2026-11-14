# TL-QCSTBV2 (11-14 04:45 PST)
Cause: sle_st_b_v2__cl14c98df5 FAIL @kit_rtl = per-instance P_u_r4..r7_HI_PAD 28 vs 29 in one plan type (not flow). Already fixed by DIE-QC-103 event s29q103S via param_class_split: types ...__pv41c959f3 and ...__pvcd986c42, launched 03:17, bind/kit_rtl/gen/lint PASS, now in place (epyc8, GPL overflow 0.22, routability OK, healthy CPU). No relaunch needed (same inputs would be blind retry).
Shared cause for TL-QCSTAV2/BV1 (sle_st_b_v1__pvc5a85fd4 etc): same param split; check they are pv-split in s29q103S.
Other variant clfde1249e: INFRA count frame files feed_s29.json/regions_s29.json missing (02:xx s29q102B0); superseded by s29q103S, check its status.
Next: wait for place->route->sta result, then AUTOPILOT auto_resign/AUTO-RESIGN row.
