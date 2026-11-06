# KV PHYv1 existing reset relay placement

The only plan changes are two relay_sites entries in kv3_phy_v1. Existing ot_dp_rsync W=1,S=2 RTL is unchanged. Actual current native-part Yosys proc/flatten/techmap/rename-wire identifies u_rs_ri_core_rst_n.b[0].r[0] and .r[1]. The first keeps the input position842.4,768.96; the second goes to701.514,515.16. Macro endpoint is306.72,515.064. Planned routed hops394.686/394.890um, under405;1384 current macro/landing/reset/clock/relay reservations checked. No new flops or boot/data cycles.

Canonical kit_istations.relay_sites_only_tcl contains both exact cell keys; full plan schema validation returns no errors. Replay checks current parent geometry and asserts the JSON difference is exactly those two sites. Viewed forms_review.png: both sites are clear in the eastern corridor; macro shape/pins and all other groups remain unchanged. PASS-COND for actual mapped placement and TT/FF STA. No route or sign-off has run for this event.
