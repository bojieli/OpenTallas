# HEAD signed-unversioned archive check, Nov 22 14:5x PST

Checked the exact four allowlist rows in `autopilot/OWNERS.tsv` against current HEAD event `head_rp21z20NF15f_r17b`, plan `18f3c0c7c0c1`. Both RTX and AGIdock indexed the historical final ODB, DEF, netlist, SPEF, SDC and standard sign-off below. The original E9 host-e, E8 host-w and E10 SerDes worker paths are gone. Mesh still has its E9 kit and final route.

| Type | Historical archive under `s81_head/` | Exact reason it cannot credit current r17b |
|---|---|---|
| `hd_host_e` | `hd_host_e__he12h_drc2`, ODB `27077f92a77f`, TT −24.28, internal FF 0, DRC 0 | All 2,180 archived signal pins match their r17b sites. The current form adds `strap_rst_ph`. The historical archive has no all-shown final routed LEC. |
| `hd_host_w` | `hd_host_w__hw4e2_hei3_1116`, ODB `3605dde7658c`, TT −29.73, internal FF 0, DRC 0 | r17b adds 26 expected signal pins and moves 40 shared pins. The historical archive has no all-shown final routed LEC. Its real paired receiver still showed the reported FF hold miss in the earlier parent study. |
| `hd_mesh` | `hd_mesh__eco_mesh_pa2_r5_1119`, ODB `5cb12bb9c033`, TT −27.39, internal FF 0, DRC 0 | All 2,315 signal pin sites match. The archived r3 wrapper has six `ot_dp_head_raw_export_pair` cells where r17b uses the relays and explicit start-raw aliases. The historical E9 `lec_async.log` explicitly records preplace LEC dropped. The final netlist and ODB remain in the archived kit, with no all-shown final LEC receipt. |
| `hd_serdes` | `hd_serdes__sd9he_pw_1118`, ODB `e70a832e6bff`, TT −27.16, internal FF 0, DRC 0 | Even excluding native PMA inputs/outputs, r17b adds 16 planned pins and moves 22 shared clock pins. The historical archive has no all-shown final routed LEC. |

All four records retain their original local R-MINIMAL outcomes and report `release_qualified=false`. The archives with the above identities are under RTX `/home/ubuntu/signed-export-1114` and AGIdock `/archive/opentallas-signed-1114`; the original-worker mirror was checked under `/archive/opentallas-signed-1106`. No versioned resign, route, tag, export pointer or parent receipt was added.
