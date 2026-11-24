# KV-HG-CAP handoff (lane started 11-23 20:46 PST by COORD; one job = hg family cell cap + centre hotspot)
## Census (rc127 kit epyc8 .../KV-D29/kv3_hg_v1p5_1123174917, posted 9fae72e)
- 496,651 placed = BUF 156k, TAPCELL 107k, INV 81k, DFF 79k, logic ~57k. Synth 269,952: g_ex_0 u_ex SOFT 77,471 (u_exp 72,843).
- Root cause: plan soft_clones keeps g_ex_0 soft (no slot: col0 ex slot held by ns ft3 landing ring cl_ft3_i). Hot window x553-657 y580-950 = 108k insts.
- smells 1.385 flag = east core-edge bin artifact, not centre.
## Row r1 (plan e7f98ec5cd1d from A3f fb580e08d47c, asbuilt_allfix_A3f e9d82a711970)
- script epyc11 /srv/opentallas-scratch2/claude/KV-HG-CAP/hgcap_delta.py; plan tmp/plan_hgcap_r1.json; report tmp/hgcap_r1_report.json
- 12 hg types: ring ns -> signed ew (kv3_hgi cl_ft6_i precedent) at W margin x8.64; g_ex_0 hard 4th qkd_astk_ex_s at col0 slot (73.44, ey) R0; ex_1 -> x349.92; ft3 stations even hops 319.7 (kv3_hg ft2 kept); taps moved/added; cells -77,471.
- channel stays 103.7 between head columns (no-growth); mouth 103.7 -> 129.6. >=200 needs X growth (die re-floor) -> variant r2 only if r1 re-place still lumps.
- gate: unit kv-hg-cap-gate-r1 (epyc11 user unit) -> gate_r1.out, gate_r1/ ; tree = fork of kv-allfix/grow/tree, launch_35681 (rt 356816a53858)
## Item d: GRT resume of rc127 kit: script epyc8 /srv/opentallas-scratch2/claude/KV-HG-CAP/grt_resume.sh (asked KV-D29 20:53, deadline 21:10)
## Next: gate result -> ROW-REBASED <sha> <result> to KV-ALLFIX + FABLE-RC-KV; private place probe of v1p5 on r1 for density render + count vs 400k.
