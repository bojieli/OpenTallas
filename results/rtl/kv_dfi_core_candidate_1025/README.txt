Candidate K pacing for owner decision14; NOT a release-image qualification.
OT_KV_RD_SHAPE_K=8,3 selects the 8-on/3-off RD shape. Default remains 8,2 so historical images reproduce.
OT_KV_RD_SHAPE_V allows an explicit candidate V shape; both are checked against the real compressed Run field widths.
Full legacy 1024 ps controller compile with kv44 bound ages PASS: 128 PC images,512 RD + 4 commands per PC, K/V shape 0.7272727.
Same compile at 833.334 ps FAILS existing put-law representability at V sector 192 (267 actual vs 264 law).
Independent exact controller encoding test: 256 sector events preserved, 8/2 negative rate control fails 0.73 budget; 2 tests PASS.
No RTL arithmetic change, default schedule or claim of synchronous-domain closure.
Reproduction: source kv44 img44/asbuilt_rtl6/kv_flags.env and select matching pair image; run boot_v36/hbm_duty.py --ages img44/prep/die_ages_bound_padded.json --rs img44/prep/relay_stages_bound.json --rd-shape-k 8,3 [--hbm-ps 833.334] --out result.json.
