# Exact r128u post-gate review packet — PG HOLD

Candidate source a7a7a0ffb on codex/collfj-reason-1020. This receipt is outside frozen consumed kit inputs. No REVIEW.json or submission. Coordinator approved exact pre-gate geometry 01:31 PT. Both actual floorplan and post-place density PNGs personally viewed at01:42 PT.

| check | q3 | q2 |
|---|---|---|
| Gate | PASS0fail0warn | PASS0fail0warn |
| Exact actual mapped SHA256 |63f5cabd014b24a0f377578aedcbbfb4c30b3eec5cf78646ca7dd0f3973d7289|a83a8cd33a516760b2feb43b9f62a69e1d654387f835aac0985a11e7b2207d74|
| Current main actual-Liberty structural census |8787roots,max32,0roleerrors,0violations|8804roots,max32,0roleerrors,0violations|
| Setup/hold WNS ps |+125.6/+50.3|+174.1/+49.0|
| TT/FF boundary spread ps |11.8/11.0|16.3/14.7|
| TT/FF all-root spread ps |20.5/20.5|24.4/23.9|
| TT/FF insertion max ps |160.7/129.7|164.6/133.1|
| GRT totaloverflow |0|0|
| actual placed instances |16147|16204|
| Actual placed fullbbox |2.16,2.16..101.52,69.12|same|
| allcell bbox pair Manhattan upperbound |166.32um<405|same|
| Actual PDN VDD/VSS metal continuity |PSM0040 allshapesconnected bothnets|same|
| Macro native PG terminals |VDD→VDD,VSS→VSS|same|
| Protected newborn PG HOLD |612instances/1224iterms|620instances/1240iterms|

Eight-item checklist:
1. Literal macro: stock ot_sram_1rw_128x64_m2_r2c2_p192_mir, LEF SHA dac7ed66a330e605abcdf8f80c214dabb7fd79d4ee77557c90c194e39d957847, R0(43.2,43.2),37.8x23.784um. Original230signal M4 pinrects allontrack (macro_literal_track_audit.json); no translated LEF. Actual ODB confirms R0/43200,43200DBU.
2. Channel/PG geometry: W/E41.04/20.52um; bare N2.136um contains unchanged stock2um PG halo, no tileN or macroN pins. Actual2_4PDN check_power_grid-floorplanning VDD/VSS PASS verifies metalconnectivity, distinct from terminal binding.
3. Standard band: fullwidth S x2.16..101.52,y2.16..41.04; actual density PNG shows GPLbody in Sband with face anchors retained; band released for DPL. Pin/lattice-bound outline103.68x71.28 remains approved. Actualsynth std~1584um2/3863um2band≈41.0%; gate core totalfill37.3%, distinction from renderer die-area initialfill33.8%. No fullrow or genericgrid waiver.
4. Clock/reset/pin registration: sourceclk sole declared clock, native3005/3012FF+oneSRAMclockpin; actualclock_receipts include allroot+476/483boundarysinks and SRAMclock. Allinputcapture depth0, reg→outlevels0, combinationalin→outbits0 in actual textbook.json. rst_n goesfirsttooneDFF and two-edge landing; no rawresetfanout exemption. No input/output edge changed by sourcee6846a038; directRTL956173randomcycles and parent q3/q2 144578/100576comparisons+causalmutants in sibling sourcepacket; no mapped imported-cell functional proof claimed.
5. Reach: actual5_1GRT instbboxallinside; any two actual cell-footprint points distance<=166.32um, even including wholecore corners. Ports lieinside103.68x71.28frame so cell/pin endpoint upperbound174.96um<405. Actual pin geometry dumps have0outside,0missing,0inaccessible trackchecked signal/clockpins454(q3)/461(q2). Depth351.7/268.4ps.
6. Storage: one actual1024-byte128x64 SRAM, no >2048bit flopstore; table nowSRAM, assembly usefulheldpayload1536bits, loaded128bits, boundedmetadata. No padding/resetfunctionalwarmmask.
7. Mandatory current actualLib census nowrun on EXACT gate1_2_yosys.v (full .lib and.lib.gz). Zero errors/violations, max32 includingreset/macro data pins. Function/registeredpin/storage roles explicitly remain independentlyaudited. Initial diagnostic libraryglob omittedplainSEQ.lib and refused; complete rerun authoritative, priorfailedlogs preserved in artifacts.
8. PG HOLD: initial5_1GRT nativeaudit rawunbound10136/10254iterms. Read-onlyordinaryglobal_connect in-memory clears normalnewborns but leavesprotected612/620instances; q3 HB2xp67 448+BUFx24 164, q2 HB455+BUFx24 165, allPLACED/newborn, noneoriginal. Protection/placementstatusdictionary unchanged. No clearDoNotTouch, ODBsave or kitrepair. Before/after originalODB SHA files identical. Closureinfra owns classification. FINAL6_final closedODB PG proof owed; no finalPG inferred from currentGRTphase.

Exact snapshots: ot-epyc5:/srv/opentallas-scratch/claude/ref_gate/hcoll_fj{3,2}_r128u-20261020-013704. Source binding capture2026-10-20T01:37:35-0700, daemon85fcc1f96. Frozen native_pg_binding SHAecc2257f9b66cb0f6087712304151411efd1c51a7bf3c0635979c6878af13fb8 (daemon overlay), bootstrap8c90454027999d4620c85e269f1be7486d417338d7d581b1974614f6099ec9d7. Full source manifest immutable in each kit/gate_result.json.

Actual images: physical/ref_tile/hcoll_fj{3,2}_r128u/gate_layout/{floorplan,density}.png. Gate JSON in eachkit/gate_result.json. This is a review packet with an explicit PG HOLD, not permission to submit.
