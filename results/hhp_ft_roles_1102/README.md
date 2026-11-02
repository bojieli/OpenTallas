# HHP BASE FT parent source roles — PREP only

Recovered source authority is the existing12.2a1 pushdown contract, CLOCK-KV-R25 and the prior root-approved exact five-port diagnostic mesh extrusion. The earlier OWNER request for the canonical graph was resolved: committed d25 sites plus full m25c graph are present here, not regenerated. This packet does not upgrade diagnostic approval to canonical source adoption.

Both r27 FT arcs are real mesh drivers, each two parallel BUFx24. These are die-owned combinational clock pass-throughs. They are separate from functional forwarded fclk rings and PC fault/idle ring payloads. Core ck is downstream of the mesh and is not a substitute for the pre-mesh source.

The actual graph join checks all16 arcs/32 ports across EN/WN; every selected BASE cell centre matches CURRENT c7abb4874 core sites, orientations and track offsets exactly. For three BASEs there are six arcs/twelve proposed port additions per parent instance. The per-instance input net names differ across EN/WN, so a type-only fixed-net projection is invalid.

| Parent | BASE | Arc | Actual input net | Actual output |
| --- | --- | --- | --- | --- |
| pc_EN_0 | kvpc1 | 0 | `ckm_w_ckm_n10_h1111111101` | `ck_mesh` |
| pc_EN_0 | kvpc1 | 1 | `ckm_w_ckm_n10_h1111111100` | `ck_mesh` |
| pc_EN_0 | kvpc2 | 0 | `ckm_w_ckm_n10_h1111111001` | `ck_mesh` |
| pc_EN_0 | kvpc2 | 1 | `ckm_w_ckm_n10_h1111111000` | `ck_mesh` |
| pc_EN_0 | kvpc3 | 0 | `ckm_w_ckm_n10_h1111111001` | `ck_mesh` |
| pc_EN_0 | kvpc3 | 1 | `ckm_w_ckm_n10_h1111111000` | `ck_mesh` |
| pc_WN_0 | kvpc1 | 0 | `ckm_w_ckm_n10_h1101010111` | `ck_mesh` |
| pc_WN_0 | kvpc1 | 1 | `ckm_w_ckm_n10_h1101010110` | `ck_mesh` |
| pc_WN_0 | kvpc2 | 0 | `ckm_w_ckm_n10_h1101010011` | `ck_mesh` |
| pc_WN_0 | kvpc2 | 1 | `ckm_w_ckm_n10_h1101010010` | `ck_mesh` |
| pc_WN_0 | kvpc3 | 0 | `ckm_w_ckm_n10_h1101010011` | `ck_mesh` |
| pc_WN_0 | kvpc3 | 1 | `ckm_w_ckm_n10_h1101010010` | `ck_mesh` |

FT_ROLE_PREP.json supplies exact proposed scalar M.pdecl, bit-keyed M.part_conn and M.pin_class additions. Directions are input/output and classes in/out: they are not independent core register-clock roots. Connections name the actual source nets and use no new aliases, ties, FF or cycles. No source/model is modified. Normal raw emit and wrapper-only projection ordering from adcf4e3b6 remains unchanged; these proposed fields belong only on the final copied physical split model.

The raw current bound source lacks all four required pre-mesh input nets and the shared ck_mesh output. Applying only the M additions would create undeclared/dangling nets. A future source-closed copied parent+wrapper must expose the exact per-instance approved infrastructure cut and connect it to the current die clock graph while preserving real multidriver mesh semantics; the diagnostic extrusion alone is not a canonical source contract. Parent tap clk/clk_tN names remain downstream and unchanged.

The genuine soft HEAD is deliberately excluded. Its two driver arcs (four real cells) remain required by the whole die mesh but are not supplied by the three BASEs. A soft native HEAD module currently has no FT cells; do not silently drop those arcs, fabricate a base view, tie outputs, add invented cells or reuse a base model. Head physical/source closure remains HOLD, as do full programme/token source adoption and native clock/PG/routing/timing gates.

Six lightweight controls pass: actual fixture and rejection of wrong pre-mesh net, wrong role, changed site, missing BASE and substituted output. This is source-only PREP; no GEN/CAD/simulation/proof/default/adoption occurs. No new OWNER question is needed to recover the old mapping: its earlier missing-graph question is already resolved. Canonical use remains a parent programme/source approval hold, not inferred from this packet.
