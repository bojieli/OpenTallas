# aHub RECIP routed child and hold ECO review

Intel2 private route 3812111, exact kit 11200a12e7ec789a, completed detailed routing with zero DRC and antenna violations. The final audit matched all 69 signal terminals and the placed PG pin audit matched the selected legacy view. TT setup is +189.77 ps. Golden-SDC FF hold is −7.54 ps across a true internal register pair. The separate −9.35 ps reported at the raw reset port is an overlay removal check.

I viewed the original route's `final_worst_path.webp` and `final_congestion.webp` under `intel2:/srv/opentallas-scratch2/claude/fable-fix-kv-hub/r4/selected_child_place/recip/ot_qkh_recip_leaf__216x216_ahubrecover/run/reports/asap7/hc_ot_qkh_recip_leaf__216x216_ahubrecover/base`. The worst-path neighborhood is inset in the south-west quadrant. The routed arithmetic chain is concentrated on its diagonal, with open regions on either side. The internal hold problem involves 28 reported register-to-register endpoints and warrants local data delay using the existing M6 signal ceiling and unchanged clock/PG pin geometry.

Review verdict PASS for a private bounded hold ECO from this exact routed checkpoint. The routed predecessor remains NOT SIGNED. The successor retains the original timing constraints and requires fresh routed pin, DRC, FF hold and TT setup checks before child view selection.
