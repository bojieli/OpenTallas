HEAD-97 rp21x: HEAD die event (COORD rulings 11-13).
Plan: source_plan_rp21w.json.gz, sha256 4b7d7cada1576768 (gzip -dc) = rp21x 802d132f + hd_host_e u_epc east (he_epc_east.py) + per-port windows from the routed die clock gate on 802d132f (winfix21.py, WF_EXTRA=hd_spn; gates/kitwin_rp21x_it3.json). Sidecar: sidecar_rp21.json. Sink bins: ../sink_bins/hd_tile_rp21.json.
Contents of the event:
- F1b hd_tile form: W 8.64, E 25.92; tile 717.12; die 17712 x 17556.48.
- Every partition east of the array is shifted.
- Pin relays one per pin, within 4.32 um of the face.
- Reset taps moved out of the strips.
- F1c: reach_pairs x_q -> u_xo, fix --rules 2, XO_HOP=2 (RTL: origin claude/head-97-xohop-1113 @1bb0c4ec0f).
- Re-layouts: hd_host_e on the lattice; hd_host_w and hd_mesh centred/stacked lanes; hd_ctl at 43.2 streets.
Chain: scripts/build21.sh (tools: main + claude/reach-tool-3-1113 1a13fcec4a + head-97-xohop + train 61). Gate outputs (rp21j = rp21x minus the XO_HOP relay delta) are in gates/.
DO_NOT_COUNT until the proof builds and the die clock gate are posted.
