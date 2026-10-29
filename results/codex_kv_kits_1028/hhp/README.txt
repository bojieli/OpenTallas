Current HHP fMY source successor (2026-10-29)

Host intel1, lane root /srv/opentallas-scratch2/claude/codex-kv-kits-1028.
Actual bind7 snapshot: sysc/bind7. Physical plan: sysc/plan_abi_pg.json (the HHP slot/pins are unchanged canonical event23).
Actual type closure: hhp/kit_rtl/kv3_pc__cl474a9ce2, 58files/no unbound/narrow/spare.
Raw source extraction: hhp/raw_core3/qkd_kvs_pc_h_head_p/qkd_kvs_pc_h_head_p_core.json.
This is a fresh cut of the actual bound leaf; it is not a historical kit clone.

The physical fMY pins already contain the published face recut. To generate the raw source once, hhp/raw_source_ports.json inventories the actual full pre-face logical leaf ports: ck first, unused hck second, raw HBM data clocks, full pc__ki/pc__land_er; no FT infrastructure ports or already split face aliases. It has no physical coordinates and is used ONLY by the source extractor. Exact result:22ports/3278bits,0 added/0 stale, lint0, both current instances structurally/boundary identical. Final physical generation uses original canonical fMY plan pins, not this logical inventory.

Published source flags applied once: --kvspc-face-ports --kvspc-private-ports --kvspc-core-clock --cts-setup-only --two-mode-grt --trial --view-tag _fMY --util0.6 --sigmaxM5.
Fresh final kit: hhp/kits3/qkd_kvs_pc_h_head_p__397.44x362.88_fMY, hash6ffe1cea88e2bebc,2987functional+4FT pins,0added functional pins,ck only,macros0. Exact plan_pins snapshot bundled. Synth/preflight+LEC only via intel2 ot-run32GB8threads/no-spill; wrapper log hhp_synth3.otrun.log, actual unit oth-ubuntu-1367987-1793263385.

Failed kit2 is retained: ordering hck before ck made the extractor select hck as primary; face recut removed it and SELRANGE caught .ck(hck[0]) before synthesis. Corrected ck-first raw3 source is separately generated. No physical pin/RTL ABI/latency change was used to hide the failure. Placement/STA/P&R not authorized until actual source preflight/census and geometry review.

Shared helper fixes offered separately: c9a04a399 (existing7c10ac93b9 CORE_CLOCK duplicate declaration/forwarding fix),52d07c64d (native multiline port parsing and exact bound_module names),4b41d7b4f/f6344dea7 (immutable plan pin snapshot packaging). Only narrow approved fixes should be merged, not this aggregate branch.
