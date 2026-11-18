# KV-D23-COMPOSE handoff (helper of KV-HG-OPUS; started 2026-11-18 06:0x PST)

Work dir epyc7 /srv/opentallas-scratch2/claude/kv-d23-compose (lane clone wt/ = sparse main worktree). Hub logs intel2 ~/tmp/kvd23c.

## Candidates (all built from the live D22 tree, manifest d988db9486e2, plan 23c87c42a4e9; tools/common_flow + rtl/lib/ot_dp_efault.sv from main eefb7e36eb6)
- D23  kw45/src_kv_pin_eb1e73448bd0_hg8_add04d1e_teefb7e3_d23  plan add04d1e8a2d asbuilt da56e1cd818c; gate d23gate/
  = tail split types kv3_pv.* (only under-matching ^-string in plan+asbuilt) + KV-D23-PC composer re-run on D22 (pc/ : 68/72/72 taps,
    fclk edge splits, reset/collector re-solve, sidecar 9704beb258d4) + efault EQ_PIPE_V 10 rows (plan_cell_conns_v36) + hub_Wo 11 cores.
- D23b kw45/src_kv_pin_eb1e73448bd0_hg8_2cc1cff4_teefb7e3_d23b plan 2cc1cff49074; gate d23bgate/ = D23 + 59 PV raw-stage band rows
  (band/band_rows.py, flags 3/3 KV-HG6 literal-local-reset CLAND failures; D22 left v4 TNQN_b stage 2 at y 1516.32).
- D23c = D23b + KV-D23-REACH rows (rows_proof.json: reset_replicate rsync on 36 types, reset sink_stages, tail split pipes:true);
  needs the reach code on main (my squash of claude/kv-core-reach-1118, conflicts with BIN-COPY resolved by hand; ot-push-main).
## Scripts
build_d23.py MAIN TAG (in/plan_TAG.json, in/asbuilt_extra_TAG.json), gate_d23.sh TREE OUT, seal_d23.py TAG, seal_rep_d23.sh TAG,
mk_candidate.py (from the KV-D22 candidate); intel2 ~/tmp/kvd23c/{guard_d23.py, launch_gate_when_staged.sh}.
Apply: python3 -I rt/current/tools/autopilot/publish_apply.py apply --candidate C --expect-source LIVE --expect-event EV --lane KV-D23-COMPOSE
## D24 (next): hub_C split (KV-D23-HUBC), die clock node re-site, pvfin stations, hub_Wi host rows (KV-HUBWI-HOST-rows-d23.json,
writer main 04df4c77f065), pc core RTL for qkd_kvs_pcc/pcf(+_h_head_p) (portbind/LEC gap; bind + kits not affected), light ring key.
## Status 15:15Z
D23 + D23b strict binds running on epyc7 (ot-run plan bind). ot-push-main of reach squash (wt branch kvd23-reach 440bf7477b6) running tests (push3.log).
D23c staged inputs: in/plan_d23c.json (band + reach + ring2 lite/narrow keys on hub C/Wi/Wo/Ei/Eo), in/asbuilt_extra_d23c.json.
Apply order (KV-HG-OPUS): D23 when green -> D23b -> D23c. Rider rows (kv-pv-rider) not yet in any candidate.
## Status 16:45Z (after D23/D23b FAIL)
BASE FOR MIRRORS (live, applied): /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg7_23c87c42_t5144e08_d22
  manifest d988db9486e2, plan 23c87c42a4e9, asbuilt efad37e95d45, r8 57bb66595819 (event KV-D22). Updated here when D23e/f/g applies.
D23/D23b FAIL: 1 EMIT kv3_hub_Wo raw Q rst_rl_214 (hub_Wo cores change the solved reset tree; lane KV-HUBWO-RESET).
In flight (epyc7, no hub_Wo, NO_WO=1 build_d23.py): D23e (D23 minus hub_Wo, tools eefb7e3), D23f (band + rider), D23g (band + rider + reach + ring2 keys, main e8731b01bcf).
D24 prep on main: 05f7de74d0c (hard RSTREP rings keep reach reader START), db1854527ce (clksite_resite.py; hub_C S 68.31 um).
hub_C pre-proof gate: epyc7 kv-d23-compose/hubc/gate_c (rows4 = KV-D23-HUBC rows3 + resite, D22 mirror, tools main e8731b01bcf).
