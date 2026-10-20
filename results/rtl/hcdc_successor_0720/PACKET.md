# CDC successor source-bound geometry packet, 07:20 takeover

No full gate/P&R admission. Four ea5df092f future-gate clients are SIGSTOP before any remote child/submission. Broad central-region kits in that commit are proposals only. Shared helpers and runtime were not changed. ROOT owns all main/tool merges.

Private sr9 R8 was terminated during compilation (exit143), no actual initial-state audit result; preserved R7 positives still FAIL. PC6 normal native32 synthesis supersedes the private route.

Frozen evidence scopes:

- PC1j source/ODB: exact failed pre-CTS serialized ODB SHA2fd3a136e4a8228a180ea138555b7833edbea78e30172454bb4bf5e4e2fd478e. Original DPL run reports3943 alignment/3271 overlaps. Independent check_placement readback reports360 REGION failures; rebuilding SAME13636-member region with SAME geometric union as3 disjoint rectangles removes these360 without moving cells. This is a causal region witness, not a repaired gate.
- PC1j actual anchors: all7565 pre-DPL FIRM pin/hold cells on actual row/site grid and in proposed boundary corridors (3844W/3718E/3N). Actual origin2.16um, pitch0.054um, rowheight0.27um. Source-copy split buffers were movable/off-grid, not fixed anchors.
- Direct-WIRE graph is distinct:43036 direct net driver/sink pairs,55>405/max497.211;7770 clock-wire pairs separate. It does not establish complete combinational stages.
- Complete Liberty-function STAGE graph: pc/stage_identity_summary.json + pc/stage_identity.json.gz, source stage_identity_cdc.py. Actual ITerm getAvgXY for standard cells AND macro terminals; explicit registered-read/single/dual-clock behavioral source proof; all clock pins actualLiberty; fail unknown cell/pin/function, combinational cycles, undriven cones, unclassified memory. Includes input/output ports, every sequential nonclock input (including async clear/preset), SRAM data/control and static constant-to-sequential paths separately. PC7764FF+4SRAM/17445stagepairs/0roleerrors,336>405/max475.855. HOST5338FF+5SRAM/25099stagepairs/0roleerrors,0>405/max401.943.
- HOST source scope is h1g3_place ODB SHA87cf21a5d0eb2cfd19dfe130cd66446723f32d642c3089aa306782313dce1214. Initial placement finished; failure was LATER CTS repair DPL. No CTS/GRT closure follows from this pre-CTS graph.

PC constructive model:

Restore source-identified2161 direct port-stage FFs to their actual pre-DPL anchors and project the pin span to230um (full1187/1151 demand <=5.17/5.01 perum). Source-wide data families wq_data,od_q,bypass_data,id_q,o_d are assigned explicit core/phy regional grids; each family is checked against its ACTUAL clock source, refusal on mismatch. Write/input families: txcore/rxphy; read/output families: txphy/rxcore. Distinct row slots per bank preserve packing space; no retiming or cycle change. Other interior FF targets stay at frozen coordinates clamped to the horizontal band. Macro terminal coordinates remain actual and fixed. See project_stage.py and pc/endpoint_target_boxes.json.

All17445 actual stage pairs evaluate to0>405, pointmax382.334um. If the COMPLETE cell bbox is confined to its recorded4.32x4.32 target box, every stage pair is bounded by388.752um (0conditional failures). FF-only peak bin area is65.625%. These are CONDITIONAL model facts, not a legal placement: combinational/hold/clock buffer space, exact row packing, and source/name binding of the candidate image remain owed. Earlier clamp/random projections had0reach failures but >100% local FF capacity; they were rejected and are not gate admission.

Clock model: actual PC clock sources4371core/3399phy sinks, roots on E/W at y275; N reset landing creates geometric root-to-sink L1 up to499/452um. No modeled80ps physical spread claim. Actual TT/FF coverage and insertion/spread are required after placement; clocks are not silently included in the data-stage metric.

Required implementation before a gate:

1. Build disjoint W/E/N ownership regions for pin FFs and ALL associated hold/inverter/buffer chains; reattach repair-created buffers before DPL. Leaving these cells ungrouped in free corridors permits opposite-face migration (the real497um wire/476um stage failures).
2. Enforce source-pinned endpoint target boxes, with a fail-closed retained-FF/memory/port bijection. Broad central boxes are insufficient because their possible L1 exceeds405. FF target groups and remaining combinational region must be disjoint; preserve exact macro read/write per-pin faces, not inferred master-side labels.
3. Prove actual per-bin FF packing and remaining combinational capacity using all standard cells and macro halos; FF-only65.6% is not total utilization. Source input first-use/reset-copy/CDC semantics must remain unchanged and previously proved; no generic unresolved-stage/free-to-move declaration.
4. HOST should retain inherited190..360 pin profile (already <=6/um); the proposed230um spread is not admitted. Any118.8um shrink needs its own complete stage projection. Its401.943um worst case has only3.057um reach margin, so exact tight endpoint regions/row lattice matter.
5. Rebind complete stage graph to candidate canonical source/tool snapshot (ROOTREADY6586 or later), then bounded placement-only proof of legality, complete all-stage+wire L1, literal pin/flop density and clock-domain ownership. Only then resume full CTS gates.

No receiving-Claude-WT git/edit, no shared helper edit, no main merge, no submit, no default RTL change. Actual source proof/pin/body source bytes in proposals match inherited c2f7d117c; fresh generated CDC lint receipts PASS.
