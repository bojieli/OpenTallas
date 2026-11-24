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
## 21:4x update
- r1c (A3f) gate: PRECHECK/PRE/G0 identical to A3f, scoped strict bind 0 -> ROW-REBASED posted cb01184e. A3f WITHDRAWN by KV-ALLFIX; base now A3g b258e3e34f22 (+asbuilt_allfix_A3f), rt 9b19260c1cde.
- r2 = A3g + 12 hg types (adds kv3_hg: kf station reg3 -> y466.56, ring y475.2; kv3_hg_v3: ft1 reg5 -> (64.8,660.96) + bit sites, ring y406.08). plan epyc11 tmp/plan_hgcap_r2.json sha 9f603b3ec3a1; remap_r2.json. Gate unit kv-hg-cap-gate-r2 (full-emit bind + LATCHECK) -> gate_r2.out.
- KV-ALLFIX folds the blocks in iteration 2 by sha: send it the final sha.
- GRT probe: epyc8 unit kv-hg-cap-rc127-grt, CTS running since ~21:15.
- next: private place probe of kv3_hg_v1p5 on r2 (kit_wave.py private-spec --tree epyc11 tree --bind-out gate_r2/bind --host epyc11), density render + count vs 400k.
