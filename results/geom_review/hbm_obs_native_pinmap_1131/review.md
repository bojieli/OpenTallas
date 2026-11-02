# OBS native-source actual pin map, takeover 1131

Result: 164 of 194 native source bits map to exact current S11 hard-core pins. The remaining 30 are physical source-pin gaps, owned by HBM source/kit integration; no proxy coordinates were assigned. Four unplanned xi boundary bits are separate from the 194-bit native census. This extends the parent’s 93 boundary-source mappings without replacing them.

The mapper uses authoritative `map_recovered.parts`, exact `out_s11/bind_names.json`, and declared compose member homes only when every member agrees. Each accepted row records the actual hard-core pin file, port/bit, local pin coordinates, orientation, origin, track offset and resulting partition-local coordinates. Only R0/MX/MY/R180 are accepted, matching the existing G0 transform. No center, name-normalization or split-master aliases are inferred.

Unresolved native source bits:

| Canonical leaf | Bits |
| --- | ---: |
| `epcal_NW` | 2 |
| `hb_quant_NW__program_leaf` | 1 |
| `hb_quant_NW__quant_NW_xp_ctl` | 2 |
| `hc_NW.u_q` | 3 |
| `vmfc_NW` | 2 |
| `vmm_NW0` | 2 |
| `vmm_NW1` | 2 |
| `vmm_NW2` | 2 |
| `vmm_NW3` | 2 |
| `vmm_NW4` | 2 |
| `vmm_NW5` | 2 |
| `vmm_NW6` | 2 |
| `vmm_NW7` | 2 |
| `xq_NW_p0_eg` | 2 |
| `xq_NW_p1_eg` | 2 |

Bind owner confirmed that these leaves are soft/reuse contents, uncut source leaves or missing explicit physical port maps. In particular, `hc_NW.u_q` remains a whole native leaf while the physical HC pieces are split; those pins cannot be aliased automatically. An explicit current per-port mapping or a source-real kit view is required.

OBS capture itself is current contents (`u_obs_Q`, `ot_hbm_obs_leaf__pv3`), not a hard-core pin view. Therefore all 194 sink coordinates remain unresolved too. This source-only map establishes neither endpoint-to-endpoint closure nor transport feasibility. It adds no stages, cycles, latency, source-correctness, CTS or route credit. Several source directions remain unknown in the inherited census; physical pin matching does not establish RTL direction.

Inputs: `intel1:/srv/opentallas-scratch2/claude/die-hbm-57/plan_s11/E/die_plan.json`; authoritative cores symlink resolves to `codex-hbm-stationclock-1101/s11/cores`. Aliases: `codex-hbm-bind-restore-1101/{map_recovered.json,out_s11/bind_names.json,compose.json}`. Parent native peers: `results/hbm_obs_relocation_1131/data_peer_map.json` on `codex/hbm-pstore-1131@af15480c0`; source census: `/home/ubuntu/coord/tmp/codex-signoff-1131/obs_endpoint_census_s11.json`.

Read-only run and full output retained at `intel1:/srv/opentallas-scratch2/claude/codex-geom-review-1131/obs_native/native_pin_map_r2.json`. The reusable helper is `tools/geom_review/hbm_obs_native_pinmap.py`. Small fixture checks passed for four orientations with a nonzero track offset, scalar/bus refusal, contents refusal and absent compose-home refusal. No EDA/P&R job or source/ODB edits were made.
