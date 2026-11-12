# rd1 compiler images (HBM-HUB-RTL-1, 11-12)

Generated at branch HEAD b6d8aeea53 tools. VM_RT 4 = rd1 (hb_coll / hcollgi), VM_RT 3 = control (current die).

| image | command | rd1 (v4) sha256 of sha list | control (v3) | change |
|---|---|---|---|---|
| row_gather P6+P1 | tools/hbm_coll_static/row_gather_rows.py OUT --P 6 / --P 1 --vm-rt V | rg_v4.sha256 e3cdb5c165e5aed2 | b4e9d430e5edd819 | P6 halt 4224->4225, q3 rows 32->33; P1 halt 1109->1110 |
| argmax q3 P6 | tools/hbm_coll_static/argmax_rows.py OUT --P 6 --vm-rt V --rows 256 --npt 3 --start-reg --arg-pr-source | am_v4.sha256 c1954ce59f1283fb | e52fb3db0b4bff69 | rows 72->74 (64+2 VM_RT), halt 212->213 |
| coll replays L00+L14 | PYTHONPATH=tools python3 -m hbm_layer_vehicle.coll_images --fixtures results/rtl/hbm_ds_layer_tput_1018/fixtures/L.. --boundary results/rtl/hbm_ds_layer_tput_1018/slice_sw/boundary.json --contract contract_vmrtV.json | coll_v4.sha256 37b13bb33206c6f9 | f8f3b7ed59573b2a | 12+17 emitted (2+2 unpriced) both; all 32 files differ (inject/landing +1) |

rg_v4/ and am_v4/ are committed; coll replays (7.6 MB per VM_RT) stay at epyc9 /srv/opentallas-scratch2/claude/hbm-hub-rtl-1/rd1img/coll_v{3,4} (sha lists + manifests here).
tools/hbm_layer_vehicle/test_coll_images.py: TEST_COLL_IMAGES PASS.
coll_images reads VM_RT from a contract (hcollgi_SW); contract_vmrt4.json holds only that key; no coll_transport profile (GEN2 timing + VM_RT), as the unit test does.
fused_lane_pin_cycles_rd1.tsv: FUSED lane pin cycle rows (S1b RR 11 now; S3 RR 12 when HBM-CORES-B RTL lands).
