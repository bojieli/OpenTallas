# fj u3: critical review packet, no lane submission

Actual source355bf2204 on codex/collfj-u3-regate-1020; current branch head adds evidence only. Exact fresh snapshots fj3=20261020-042441 and fj2=20261020-042442 on ot-epyc5. All8 canonical ROOT paths.json files plus native_pg_binding.tcl and clk_net_protect.tcl SHA-match main68b9cad6c in both source snapshots (10/10). Both actual callers leaf_inhold.tcl/leaf_iohold.tcl include the bind-before-protect birth fix. The first takeover regates omitted those two caller transplants; their protected PG failures are retained and superseded, not presented as evidence against ROOT fix.

| Actual check | fj3 r128u3 | fj2 r128u3 |
|---|---:|---:|
| CTS gate failures/warnings | 0/0 PASS | 0/0 PASS |
| TT setup ps (pathfinding) | +163.5 | +129.7 |
| TT gate hold estimate ps (placement RC) | +49.8 | +50.1 |
| TT/FF pin-flop spread ps | 11.4/10.5 | 18.6/17.1 |
| TT/FF maximum insertion ps | 160.9/129.9 | 169.1/137.7 |
| GRT overflow | 0 | 0 |
| Actual post-GRT native roots | 8,808 | 8,841 |
| Actual post-GRT max dynamic loads/errors/violations | 32/0/0 | 32/0/0 |
| Buffer-transparent sequential reach max um / count>405 | 140.420/0 | 141.250/0 |
| Original unbound PG terminals | 6,788 ordinary | 6,962 ordinary |
| Original protected-unbound PG terminals | 0 | 0 |
| In-memory existing-rule global-connect unbound PG | 0 | 0 |
| Unreached capture pins classified from literal drivers | 607 TIEHIGH+81 TIELOW | 614 TIEHIGH+81 TIELOW |

Original GRT ODBs are mounted read-only; no audit writes or unprotects either ODB. Original ordinary PG omissions remain recorded, and diagnostic existing-rule global-connect resolves all of them. No protected omissions remain in actual fresh ODBs. Gate PG state is distinct from final-route signoff; final closure must bind/check ordinary terms normally.

Safe-design checklist:1 PASS actual registered ports and two-stage reset landing; RC32 reset copies retained (u2 cap-only no-op is not reused).2 PASS complete FF/SRAM/BLOCK/port source-to-capture reach through all combinational cells and buffers, exact maxima above; outline103.68x71.28 independently bounds any Manhattan displacement174.96um.3 PASS mandatory mapped native32 plus actual5_1GRT ITerm/BTerm native32 max32, reset included, actual Liberty roles.4 PASS no depth/census/placement failures or warnings; TT gate is pathfinding only and final TT setup>=0/FF hold>=0/DRC0 under current uncertainties plus final native PG/source audits remain required; SS is sensitivity only.5 PASS one real128x64 SRAM; no new storage.6 PASS literal macro origin43.2,43.2, size37.8x23.784; full bottom cell band; W/E pin-face channels43.2/22.68um, busy-face115/23.784=4.835pins/um. Top4.296um clearance is a pinless macro face, not a pin channel. Outline aspect1.455; measured total fill33.9% is documented pin-bound (492/499 total pins, full S face <=6pins/um).7 PASS clock at S centerx50 beside bottom register mass; spreads above; io_hold_margin0.03, no exception for clock insertion.8 PASS identical edges/latency vs u3, no new schedule cost.

Behavioral evidence is the existing committed u3 parent EQ on Verilator5.050 (q3/q2 144578/100576 comparisons plus3 causal mutants each). RTL is unchanged in these helper-only regates. All job.json source.branch and spec.job.branch fields point codex/collfj-u3-regate-1020. Coordinator /root/hbm_coord personally reviewed all4PNGs and explicitly APPROVED these exact two fresh gates; scoped REVIEW.json receipts now record that approval. No submit had been attempted when this packet was prepared. The +49.8/+50.1ps gate hold values were verified in path_classes.tcl: TT Liberty and placement RC, not FF signoff. Final routed acceptance is TTsetup>=0/FFhold>=0/DRC0/current uncertainties plus final native PG/source audit; SS sensitivity only.

Fresh PNGs inspected (floorplan and density):
- physical/ref_tile/hcoll_fj3_r128u3/gate_layout/floorplan.png
- physical/ref_tile/hcoll_fj3_r128u3/gate_layout/density.png
- physical/ref_tile/hcoll_fj2_r128u3/gate_layout/floorplan.png
- physical/ref_tile/hcoll_fj2_r128u3/gate_layout/density.png

Audits in birth_fixed/*.json and fj{3,2}_birth_gate_root_paths.json are authoritative. Coordinator may review these gates for submit_exact; no routed CLOSED/view-bind claim is made here.
