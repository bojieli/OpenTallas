# Qwen finite 8-bank VM physical proposal

Status: root review required; no synthesis or route launched. Source candidate73be6d00 is functional macro-model evidence, not production core integration.

## Exact physical scope

32 masked512x128 1R1W predictive SRAMs: four128-bit slices per512-bit word bank,8banks,256KiB without replication. Bank=(word XOR word>>2)&7; row=word>>3. Macro dimensions174.096x29.700um, outline total165460.8384um2. Each macro uses unchanged LEF/Liberty, repair ports tied off, actual bit masks. Signal M4 pins need row/site/track intersection and fixed FFs must inherit roworientation, as proven by prior microblocks.

## Reviewable coordinates, not adopted area

Proposed exploratory outline1160x560um (0.6496mm2); core10,10–1150,550. Four bank columns and two bank rows. Each bank stacks four macros vertically at approximately48um pitch. Macro X starts64um with280um bank-column spacing; Y starts64um with280um bank-row spacing. Origins snap jointly to432nm X and2160nm Y lattice. Exact32coordinates, geometry and source hashes are in proposal.json; all macro bboxes are nonoverlapping.

This leaves about18um vertical macro channels and106um between adjacent macro edges in X; divide lateral space between pin escape, masks/write steering, read selection and shared routes. Reserve approximately74um central horizontal corridor between bank rows for request distribution and response gathering. Do not place free unrelated logic in these reserved channels. The outline is3.93x SRAM outline; it is a tested geometric reservation only, not area closure. Register/logic/clock/PDN density and pin escape still need mapped placement.

## Paths and existing register cuts

Candidate has combinational four-client write demux/mask merging and a shared conflict signal that suppresses all32macro requests. Reads leave synchronous macro outputs, then pass bank/lane selection to four32-bit outputs. There are only existing rb/rl/rv/fault registers in this wrapper. No per-bank read/write capture register may be silently inserted.

Actual matvec mq_x is the downstream capture edge (ot_hdc_matvec.sv295). The previous macro read edge and this capture edge must remain one cycle apart. The upstream producer/request registers must be identified by the execution owner, especially512-bit write data clients; independent I/O test registers cannot masquerade as those production registers. Place bank steering beside each bank, request/conflict detection centrally, and real mq_x capture at the actual consumer boundary. Repartitioning hierarchy may be done without changing combinational semantics; no added stage is approved.

At0.92ns with60ps reserve, illustrative measured macro tq415.2ps and priorcapture setup32ps leave412.8ps for output bank/lane mux plus wires and buffers. This budget must use actual mapped capture setup, not assume32ps universally. Input address/CE setup84.7ps leaves775.3ps for producer tCQ, decode/conflict and wire; actual producer arrival must be subtracted. These arithmetic ceilings are not allocated gate delays. Global conflict fanout and512-bit interbank write routes are concrete risks.

## Timing contract requiring root/producer-owner completion

All operational re/we/address/mask/data paths must be timed; no false_path_io. Require real producer arrival and load values or include actual producer/capture registers in the cut without adding cycle latency. Until those values and actual capture hierarchy are bound, no route launch. Do not choose a convenient zero input delay or unloaded output. Root's0.92ns remains an experiment; current qwen3_budget.json1098640000Hz corresponds0.910216ns, about1.06%faster. A0.92ns pass cannot validate the model clock.

After root approval: synthesize this complete32macro candidate, verify all macros/masks retained, constrain macro coordinates and actual register regions, check PG before DRT, then extracted setup/hold with60psreserve, fanout32 and real limits, DRC/antenna. Report every clock/buffer/cell/route-area cost. A failure returns the violated input/read steering path to root rather than inserting a stage independently.
