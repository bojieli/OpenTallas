# KV structural image review, November 25

The four exact plan images were viewed. The images live under intel2:/srv/opentallas-scratch2/claude/kv-allfix/a5t9/review_1125/.

| Scope | Image | Finding and disposition |
| --- | --- | --- |
| PHY v1 FCLK row e809c09f8fc4 | phy/kv3_phy_v1.png | The right-edge tap serves the native FCLK export through a 43.584 µm projected leg. Data chains show a 381 µm maximum projection and no hop over 405 µm. The corrected place-only probe is active. Review routed clock insertion, access and congestion at the export before any route dispatch. |
| HGI Return38 | hgi/kv3_hgi.png | The two compressed HGI FT routes retain their endpoints and central corridors. The other projected red face legs and local congestion remain visible. The native VPORT test demonstrated a short-side request fault. Keep the HGI programme and new affected routes held. |
| PV S0e Return38 FT0 | hgi/kv3_pve.png | The removed interior bank is on the horizontal upper strip. The replacement hop is 347.929 µm between centres and 353.16 µm across the 1,057 exact bank sites. The northeast and side congestion, other red chains and functional VPORT imbalance need separate closure. |
| Hub C c3 7bbb8a004a65 | hubc/kv3_hub_C.png | The re-seated paths follow the ahub perimeter. The upper edge and central collector corridors still carry dense bundles. Three exact mandatory endpoint hops and the missing signed per-root clock contract remain open. Keep route held. |

## VPORT hold

The full issue applies to the sixteen physical request receivers in the R6, R7 and Return38 variants. The tested odd-side ES2 request arrived 32 cycles before the shared tap expected it and faulted. The exact per-variant receiver and lane census is epyc12:/srv/opentallas-scratch2/claude/kv-allfix/a5t9/token_c1p_pair_1125/vport_side_eq_1125/vport_side_eq_route_scope.json. Place-only work may continue. New affected HGI, PV and PC routes and HGI adoption require a physically bound equalizer, placed pad-bank capacity and setup/hold evidence for all sixteen receivers, and a replay that preserves the previously selected maximum age. Healthy admitted jobs continue.
