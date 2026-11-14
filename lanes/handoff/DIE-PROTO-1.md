# DIE-PROTO-1 handoff (11-14 08:0x PST, Opus, round 2) -- RUNNING
## Scope
COORD 11-14 ~07:4x: die GRT + die STA prototype with the REAL REGIONAL clock, QC first (s3d = S3D2 bind plan, owner DIE-QC-103), then KV (kvgeom4, owner KV-102). ADVISORY, DO_NOT_COUNT. Round 1 (00:2x-04:3x, die-wide tree on all 4 dies) is in epyc10 /srv/opentallas-scratch2/claude/die-proto-1b (see git history of this file).
## Where (epyc9 B=/srv/opentallas-scratch2/claude/die-proto-1c)
- wtmain = my detached worktree of origin/main 35d2a30df8 (git dir wt/rxs-reflood-1) for die_sta_related (tap_offset_gate, --kit-offset-out) and region_form.py.
- maps/: QC region map regions_s3d.json (region_form regions on s3d = identical to qc-clkgate-1 regions_plain), feed_plain_fwd.json, c/su/early-other region lists, inv2_stage_cal_s28dme.json, edge_readout_patch.py, mk_combo_kv.py (both-edge, qc-clkgate-1). kv_regions_kvgeom4.json (= kv_land128 components).
- qc_chain.sh [tag]: qcreg3 recipe with tree3 tools (die-qc-103/tree3, read-only) for kit/GRT/arrivals/LPO/CA; main die_sta_related. Run qc/s3d/CHAIN.log.
- kv/kv_chain.sh [tag]: ot_clk kit kv/kv_g4.yaml (FABLE kv_a on kvgeom4) with src kw45/src_kv_kvgeom4_pgL; main die_sta_related. Run kv/g4/CHAIN.log.
- Launch from intel2: setsid nohup ot-run --crit --hosts epyc9 --mem 128 --threads 24 --dir $B --priority die -- bash $B/qc_chain.sh s3d (logs intel2 ~/dp1c/*.ot). Chains skip the kit if kit/grt/route.v exists (rerun GRT/STA only).
## Next
Read CHAIN.log lines (REG_GRT/GRT ovf, REG_STA/STA proof lines + TAP-OFFSET-GATE, CA_*, STA_*), per-region overflow from grt combo logs, classify failures (plan vs type-local vs view), post RESULT per die cc owner.
## 09:3x PST status
- KV DONE: RESULT 08:4x (g4: GRT 0 ov, intra +447.1 / seam +545.1, CA lo/hi +189.8/+193.3, kitoffs.json 5798 ports -> folded by KV-102 into plan_final). Replies to KV-102: K/start-tree fields; kvgeom5 recipe (no region_form for fishbone KV; count_align_plan --start-tree clock --start-clean width; table write = DIE-KV-5/6 --from-ocv --parts ocv path, not verified by me); correction (511 MC viol were my default start form; clock form = 0 viol); start-skew 68/161 = ambiguous sync_values-2 edges failed closed (no numeric excess).
- Files: epyc9 die-proto-1c/kv/g4/gate/{ca_W,bind_W,sta_W}; kv/kv_ca2.sh, kv/kv_staW.sh. Failed attempts at --table-out: bind_W2.log, bind_W_region.log.
- QC RUNNING: qc/s3d kit in region-DME clock-tree stage since 16:11 UTC (CPU busy). Next: GRT, STA + TAP-OFFSET-GATE, CA, RESULT cc DIE-QC-103.
