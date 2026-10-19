D2D source-safe structural prototype: review packet, adoption=false

This freezes the clean copied-ODB prototype on source b30f8454c6db1309ee4ec7a154943f6c737b43f2, qfd_d2d_static_ovl PR1/MUT0/TXDP167838472 and unchanged external FF ages, BTerms, pin grants, macros, SDC/reserves. It does not promote the DRAFT safe4 kit or authorize a gate. Original failed safe3 and all intermediate prototypes remain preserved. Remote DBs are in ot-epyc8:/srv/opentallas-scratch/claude/codex-qw-d2d-clockdiag; SHA256SUMS pins this packet and native_final_remote_sha256.txt pins actual DBs.

Actual final native results, ps:

| Corner | setup | hold | boundary spread | slew/cap/fanout violations |
| --- | ---: | ---: | ---: | ---: |
| TT | 14.422463 | 36.961711 | 72.171570 | 0 |
| FF | 202.401929 | 30.010466 | 63.954742 | 0 |

TT/FF setup and hold signoff requirements are >=0; 30ps FF construction margin was retained. SS is sensitivity only. Actual source-owned boundary population3858: N1673/S1165/E280/W740, no shared-face roots. Ownership is independently derived from ordinary BTerm faces and actual first/last sequential data endpoints, including real copies; asynchronous reset inputs are excluded. No clock-cell name or FF location selects face ownership. Native timing paths include E/other/port classes; full expanded paths and actual extrema are in the corner logs. The final admissible uniform E insertion changes are TT[-42.313515,+7.828430]ps and FF[-9.575508,+15.101089]ps at setup0/hold30. These are measurements of this prototype, not a source-guaranteed contract.

RC basis: ALL native graph RC was freshly recomputed with ASAP7 setRC.tcl and estimate_parasitics -placement after legal placement, including unchanged old nets, copied control nets, recursive reset loads, new clock branches and local SRAM clocks. No old GRT wire parasitics are retained as the electrical basis. No new route, GRT, extracted SPEF, route-overflow or DRC closure is claimed. Thus TT14/FF30 is a placement-estimated prototype result. Old safe3 GRT0overflow and access-only macro PA evidence cannot qualify this new graph. Cell Liberty is the actual TT/FF loaded by the committed scripts; the saved source-specific signoff SDC is replayed unchanged after placement RC.

Structural changes and exact costs:

- 1758 source-master/all-input state or logic copies:1155 FFs and603 combinational cells. Added FF masters:423 DFFASRHQNx1,309 DFFHQNx1,287 DFFHQNx2,136 DFFHQNx3. All use original ASAP7_75t_R masters. General limit16 real transparent-collapsed terminals; calendar ev_port FF and same-calendar ev_v/ev_port AND3 decode have source-defined limit8. Recursive upstream reset/D/control loads are included, rather than stopping at a332FF projection.
- 4953 transparent path copies accompany the1758 drivers (6711 total clone-manifest entries). Pruning removes1197 unused BUF/INV/HB cells only after no observable output/BTerm or signal load remains. Of those,1184 existed in the pre-control baseline and13 are new paths; no sequential/hard cell is removed. Final independent all-driver max20,0sources>32; five actual primary inputs have17..20 loads; every soft control driver satisfies its bound.0open PG pins.
- Actual clock leaf partition adds73 same-parent/master/polarity/level real drivers, maximum20 direct clock loads, with recursive real FF load accounted. Four SRAMs each get one real local BUFx24 stage at their actual physical home; original clock root and each original parent remain unchanged. Original shared SRAM drivers each saw50.55 cap(20.75pin+29.80estimated wire); no dummy load is added.
- The E prototype retains15 original-master/polarity cloned branch cells plus3 real BUFx24 prefix stages after the last common root, preserving all FF cycle edges. This explicit E path has3 more buffer levels; local SRAM clocks each have1 extra level. Original full clock graph and failed detour are preserved separately. The current measured E construction still derives from the preserved prototype; the source-owned face extractor is proven, but a generic source-owned E branch implementation is NOT promoted into the DRAFT kit.
- Final native FF hold repair adds224+6=230 real data hold buffers; the earlier E-only baseline already contains34 real hold buffers. No clock dummy loads or SDC delay masks. The architecture must preserve polarity and real graph ownership if promoted.

Actual LEF master-area census (not synthesis estimates), original safe3 CTS -> final:

| Class | original count / um2 | final count / um2 |
| --- | ---: | ---: |
| FF |10967 /3265.322220|12122 /3647.274480|
| combinational/physical |32431 /2645.905500|33034 /2704.138020|
| BUF/INV/HB |29481 /2461.351860|33596 /2930.900760|
| SRAM |4 /53293.863168|4 /53293.863168|

Total standard-cell area8372.579580 ->9282.313260um2, delta909.733680um2. Added1155FF/381.952260um2,603comb/58.232520um2,5299BUF/INV/HB/590.475420um2; removed1184BUF/INV/HB/120.926520um2. No same-name master change. Control-baseline-to-final counts additionally isolate the earlier E-stage+34hold52cell/11.343240um2 baseline delta. Exact per-master added/removed inventories and actual location/status are committed, with all three complete censuses compressed. Classification includes CKINVDC as inverters. The actual density PNG was inspected: central channel contains concentrated occupancy; it provides placement evidence only and does not show routed accessibility.

Equivalence/reset/initialization contract:

Independent source equation congruence PASS checks43402 original nontransparent masters,81291 original input equations,3670ports and1175output equations unchanged;1758 new nontransparent copies have exact source master and4820 input equations. BUF/INV/HB paths are collapsed with polarity, and new state aliases resolve recursively to their actual original source. The wrong-source mutant FAIL receipt is included. Reset and clock inputs are part of the checked equations, not ignored loads. All423 added asynchronous-set/reset FFs retain the exact original SETN/RESETN source, polarity and master behavior; reset output/state replication adds no reset cycle. All1155 FFs retain source clock root/polarity, and no new functional FF edge is inserted.

Induction is CONDITIONAL on corresponding initial state. The732 added non-reset FFs must receive the same program/cold initialization as their originals before observation; exact master/input congruence alone cannot establish their unrelated power-up states. The packet does NOT claim this initialization join has been proved for every shadow copy. Source-pinned reset/cold-init trace or formal proof for those732 states remains required before promotion/adoption. Existing RTL transport proof is unchanged and cannot substitute for that physical-copy initialization obligation.

Review checklist:

| Item | Status |
| --- | --- |
| Frozen source/ports/master/input equations and wrong-source mutant | PASS, conditional initial correspondence as above |
| Actual root/face ownership incl copies | PASS extraction, generic E implementation pending |
| Recursive control fanout, native TT/FF slew/cap, PG | PASS placement-estimated |
| Native TT setup/FF hold/spread | PASS prototype only |
| Actual legal placement | PASS existing native DPL/check_placement logs; density/floorplan PNG attached |
| Exact area/master/copy inventory | PASS |
| Raw dense SRAM pin density | literal FAIL(~10.2pins/um); no waiver |
| New graph GRT/DRC/pin escape after power/vias | UNPROVED, new route required |
| Cold/program initialization correspondence for732 unreset copies | UNPROVED |
| Fully integrated source-safe4 E clock implementation | DRAFT |
| Gate/adoption | false; ROOT review first |
