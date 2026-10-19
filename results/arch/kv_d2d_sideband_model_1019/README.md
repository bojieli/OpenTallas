# KV D2D producer, storage and ATTN validation transport model

**MODEL HOLD before RTL or physical work.** The concrete candidate carries **17 real registered raw-zero predicates**, preserving the producer, all 11 payload relay edges and ATTN landing. It also replaces the unsafe payload relay boundary, rather than placing a companion beside the old unsafe 528-bit relay. The generic 32-bit transport remains the reference. This packet contains no new RTL, simulation, synthesis, layout, gate or qualification receipt.

| Candidate increment, producer through receiver | Exact 17 | Generic 32 |
|---|---:|---:|
| Plain FF, including all 11 relay hops |221|416|
| Producer OR4 / OR3 / OR2 cells |161 / 2 / 16|161 / 2 / 16|
| Receiver OR4 cells |10|10|
| Positive capture INV cells |221|416|
| Native master area with explicit polarity, um² |93.13704|158.52834|
| TT / FF clock input capacitance, fF |104.916656 / 115.364210|197.490176 / 217.156160|
| TT / FF FF data input capacitance, fF |123.499662 / 137.318350|232.469952 / 258.481600|
| TT / FF all added OR input capacitance, fF |406.815203 / 451.948068|406.815203 / 451.948068|
| TT / FF added INV input capacitance, fF |137.004088 / 151.101236|257.890048 / 284.425856|
| Additional reset/set sinks |0|0|
| Additional request, Q, fault or calendar edges |0|0|

These are conservative implementable library cell sums, not final synthesized area or total power. DFFHQNx1 has QN next_state=!D; one real INV per added FF is charged to implement positive capture. The earlier83.4705/140.3325um² figures omitted this polarity cost. No unproved NOR/parity absorption credit is taken. No old cells are deducted. Clock tree, wire capacitance, activity and actual placement remain open. `whole_price.json` prices the entire actual D2D source inventory and its modeled repair separately, including reset capacitance, rather than presenting this increment as a whole-producer qualification.

## Exact selected producer and transport seam

The selected 5f2 source `ot_qwen_d2d_dies.sv` SHA1214151a matches the earlier G7 source. PR defaults to 1: `q_rx_payload <= c_rx_payload` is unconditional and unreset. The internal decoded payload, not the ATTN input pin, supplies the reduction D cones. Header, CRC, expected kind/epoch/beat, receiver timing, immediate health, ready/accept and every original fault priority remain at their original observer edge.

The captured current GEN8 v4 `case_kv/die.v` has producer **qkd_d2ds**, a bundle schema mapped by `d2ds_binding()` to qkd_d2d_static, NTX3/TXDP0x03030416. Its `d2ds_view.json` says FRAME, bind null, missing CLOSED r7v; this is not the G7 direct hardened binding or a native source receipt. `current_path.json` retains the exact source hash and all 24 producer/consumer/relay lines. There are **10 route relays plus one pinfix**, all on n_clk_core_c. The separate planner10 count is not itself evidence of a calendar error. The candidate copies this actual 11-edge path; it does not change a boot age to match a counter. Final GEN8 binding and actual forwarded clock phase remain prerequisites.

Proposed distinct opt-in source family, defaults off, for ROOT review:

1. Add `rx_zero[16:0]` to a distinct producer master. At the same edge as q_rx_payload, set Z[0] to OR(c_rx_payload[31:19]), Z[1] to OR(c_rx_payload[31:5]), and Z[z+1] to OR(c_rx_payload[32*z+:32]) for z=1..15. Capture all 17 bits unconditionally without reset. Do not retain 15 duplicate output pins or tied placeholders.
2. Extend the actual qkd_d2ds binding, die master/RTL schema and payload bundle by these 17 live bits. Every one of the 11 actual stages carries the corresponding word's flags on its original edge. The full 565-bit live payload+predicate bus is partitioned into exact 188/188/189-bit registered shards. Keep the payload bit mapping exact across changed shard boundaries.
3. Add 17 real ATTN input landing FF, unreset like codec l_pl. Reconstruct C[0]=Z[0], S[0]=Z[1], and C[z]=S[z]=Z[z+1] for z=1..15. Replace only the original CMD data[511:19] and STATUS data[511:5] reductions. Both original observer predicates reduce 16 flags. Keep the complete immediate receiver/controller/health equations and all feedback state live. Do not use the separate unproved KV_SIDE specialization or move the controller's CMD equality into record rejection.
4. Integrate on a whole producer successor with the complete source repair below and a truthful four-bank storage interface. A distinct mapped-source fork can preserve actual source cells/ports while adding same-master-D/reset kept copies; the exact mapping and optimization survival must be proved. No current native view can qualify this changed interface.

The 17-bit reconstruction is an associative four-state OR identity, including X/Z values: groups1..15 use literally identical masks in C and S. `model.py` verifies the exact input sets. It differs from the unproved direction specialization that would remove STATUS checks. The first C/S group is deliberately separate. The generic32 model also shares the same combinational high-word reduction but retains both sets of real kept FF.

Payload and flags must form the same cohort. All 13 captures (producer, 11 relays, receiver) are unreset; after those actual edges, each predicate equals its matching payload reduction inductively. Arbitrary initial predicate FF can disagree before the pipeline fills. Actual first authorized event after POR, warm reset, PLL stop/restart and any phase change must establish that cohort before observation. Neither the inherited 128-cycle relay comment nor an invented64-edge skew supplies that proof. No first-use/reset qualification is claimed.

## Full source census and predecessor cost

`census.py` independently reads every native cell, vector macro port, top input/output and assignment alias. It counts actual tie H/L outputs and follows BUF/INV to logical endpoint pins. The uncapped complete root tables and per-root copy demand are committed compressed; no root class is exempted.

| Source | Old r7w | Current r7w_sf actual gate |
|---|---:|---:|
| Mapped source SHA prefix |16d87dc7|c5449c82|
| Actual cells / FF |40,694 / 11,054|37,553 / 11,905|
| Unsafe FF / comb / tie roots |71 / 18 / 2|7 / 67 / 2|
| Additional unsafe BUF/INV intermediate nets |340|11|
| Max non-tie nonclock demand |1096|161|
| Independent extra FF / comb / tie lowerbounds |430 / 138 / 133|7 / 71 / 144|
| Predecessor fixedpoint extra FF / comb / tie |444 / 144 / 138|8 / 71 / 144|
| Fixedpoint passes |3|3|
| Additional native master area, um² |163.50012|15.19236|
| TT / FF extra FF clock cap, fF |208.711309 / 228.472290|3.750540 / 4.100648|
| TT / FF extra async reset/set cap, fF |318.367000 / 344.289575|7.276960 / 7.869476|

The arithmetic fixedpoint charges every clone's actual D, reset, enable and combinational inputs back to predecessors, not just the original violating outputs. It finds no remaining top-input or macro-output demand above32. It is **not** an emitted source certificate: copies must retain canonical master D/reset/clock, native signal polarity, physical terminal partitions, actual output ownership and startup convergence. No copy holds its own independent feedback state. Functional proof, preservation through ABC, boundary registration and post-source complete census remain mandatory. The exact223 added current512-bit-source cells are named in the ledger. Narrowing to137 useful columns removes3008 tied-zero endpoints (375 data +375 mask bits and2 column-repair bits per bank). Recomputing the complete narrowed graph yields **129 added cells:8FF,71comb,50ties**, not223. The narrowed fixedpoint is11.0808um², with the same FF clock/reset capacitance; no94 dead tie copies are installed. This is an explicit analytical port-width transformation of the source hash, not a new mapped-source measurement. They include four q_sf_start/seg plain FF and four recovery ASR FF, including one predecessor begin_now FF exposed only by closure.

The old decoded-payload roots independently have maximum4 loads across all548 bits. The current gate uses merged `c_record_rx` names for the corresponding internal source FF; source site identification must use D/Q equations, not assume the old rx_flit instance spelling survives. Added raw-zero leaves have at most two loads per payload bit, new OR roots drive at most two D pins, relay FF drive one next-stage D and shared receiver flags drive at most two OR inputs. This added branch does not cure the existing whole-source defects.

The committed preflight-zero claim is pinned to 8cbe74cd0/results/rtl/kv_d2d_safe_fo_1019/census_over24.json.gz, generic source JSON SHA98f879df. Its exact source files match the gate shipping manifest (safe_fo9b369435; dies_sfo8cc1bca3). The preflight runs proc/opt/techmap plus native DFF/INV mapping, **without ABC combinational mapping**. Its transparent collector excludes constants and output BTerms. Actual gate1_2_yosys.log explicitly runs ABC speed mapping at D770; the actual37,553-cell netlist differs from that generic preflight. This is a coverage/netlist distinction, not a demonstrated shared-helper regression. The actual gate's true reg→reg−16.1ps remains a timing failure even though its outer summary says WARN. No failed gate is replaced.

## Storage access and lifetime

The actual source has four independent 64-slot banks of137 live bits, 548 read and write bits per edge (68.5B each), one shared logical clock, no backpressure and modulo64 publication identities. It is a statically scheduled slot store, not a variable retry queue. Keep all written-map, unread-slot, overwrite, late-write, epoch/abort and missing/stray-frame checks. The source issues the read after its scheduled write; this is not a blanket no-overlap memory.

The historical wrapper has420 FF/bank; the current safe one-hot select wrapper has445 FF/bank (three137-bit payload registers, six address bits, write-valid and27 select FF), total1780. Preserve dq/dqq, write command capture and every16-bit-group one-hot select. Current arrays still use four64x512 masters with only137 useful columns: 35,072 useful bits versus131,072 nominal data bits. Their old face contacts fail independently of padding.

The concrete candidate is **four**, not Qwen's five, `ot_sram_1r1w_64x137_m1_r2c2_p192` macros from99cbdd49d. Each is57.912×45.672um, four-bank area10,579.827456um². Each W/E face has229 signal contacts,5.014013/um, actual0.192um minimum centroid pitch and maximum6 contacts in a half-open1um window. The macro has118 abstract PG rectangles. `macro_contacts.json` retains every signal/PG rectangle. PG contact/via continuity, min-area escape and routed access are still unqualified.

This single-clock macro explicitly reads OLD at the same posedge before its write. Keep both current-age and prior-age forwarding equations; a dual-clock coupon cannot supply this guarantee. Adapt actual widths to rd_out[136:0], wd_in[136:0], w_mask[136:0], cr_sel[15:0]; repair disables remain real macro controls with their exact widths. They do not replace payload. Use OT_MEM_NO_INIT for arbitrary-memory first-use proof. No new predicates are stored in TX SRAM: they are computed at received-payload publication, so storage width stays548. New four-bank TT/FF clock capacitance is37.3832/41.4928fF; all input-pin capacitance is830.8552/916.6288fF, with bus widths counted explicitly.

Proposed43.2-lattice origins (43.2,43.2), (172.8,43.2), (43.2,129.6), (172.8,129.6) give macro bbox[43.2,43.2,230.712,175.272] and real W/E and N/S gaps71.688/40.728um. This is a capacity envelope, not a floorplan grant. A connected full-width standard-cell band, PG/OBS/clock roots and actual full-face external pin demand must be reallocated. Current sf source std master sum is5977.71252um²; its copy repair is15.19236um². New macro area cannot be used to infer final placement area or to erase fixed-face pin demand. The existing22/4/3-edge TX control delay chains also require explicit ring/calendar treatment or an owner decision; their inherited control-only note is not accepted here as a new storage waiver.

## Whole relay boundary and wire capacity

Current GEN8 frame relay528 is21.6×82.08um:528 data contacts/82.08um=6.432749/um, a physical defect. The20-bit remainder currently rides a36-bit frame with16 pads; this candidate takes no free pad area or clock credit.

The 17-bit option replaces each entire stage with exact188/188/189 live registered shards; generic32 uses193/193/194. Conservative43.2-square envelopes give max4.490741 signal contacts/um. These are bounds, not claimed minimum standard-cell sizes or macro lattice requirements. A concrete M4 proposal uses0.024-square contacts centered at y=2.892+0.192i; every center lies on native y=0.012+0.048k tracks. The worst194th center is39.948um, with real end margins. Local max is6 contacts/um. M4 min-area0.002um² needs0.083333um metal length at0.024width: a0.024 contact needs at least0.059333um outward extension, before via enclosure/spacing. A smaller outline must reprice actual pins, aspect and wiring, not squeeze the same contacts.

All11 stages use61,585.92um² outline sum, versus21,349.7856um² old two-frame sum: **+40,236.1344um²**. This pin-bound envelope has low fill requiring ROOT review. Total live relay FF are6215 (17) or6380 (32); all clock/data input capacitance is charged in whole_price.json. Three actual clock entry pins per stage add11 entries over the old two-frame topology; they need fresh native insertion, spread and neighbor-phase matching. No reset is introduced. Separate S/N clock/PG contacts and every rail/via still need actual geometry; no access pass is inferred from signal density. Monolithic64.8×108um per stage is a priced alternative with76,982.4um² total outline.

Each segment carries565 or580 real wires: raw M6/M7 track width at0.064pitch is36.16/37.12um, of which1.088/2.048um is the new predicates. M4/M5's0.048pitch gives27.12/27.84um. These are lowerbounds before PG, blockages, shields, turns, vias and utilization; no empty-channel grant is assumed. Every individual routed driver→endpoint wire must satisfy405um. New shard internal corner distance is86.4um, but intertile pin coordinates, parent overlap, neighboring displacement and actual routed lengths remain open. The captured existing placements are not a grant for larger envelopes.

## Concrete next review and proof

ROOT can review the17-bit candidate above as the source proposal. Source admission still requires the actual canonical-D terminal partition for129 narrowed-source copies, exact four-bank interface/lifetime replacement, complete565-bit shard schema/placement capacity and first-use/PLL/region authority. A fresh source owner must then prove complete old/new observed outputs and fault priority, positive traffic, malformed CMD/STATUS/high reserved bits, wrong mask, wrong flag, wrong relay age, bypass collision and reset/first-use causal mutants. The entire producer/receiver native depth and all-driver graph must be checked after synthesis; no local-input combinational exception or old physical receipt applies.

The conditional producer three-OR4 library calculation starts at20ps slew, zero wire, and actual one/two FF D load: the exact current TT/FF values in model.json for17/32. The final OR drives the charged INV D-polarity correction; its own delay and the FF capture/launch arcs are outside that three-OR estimate. It omits upstream CQ/load, wire and clock effects, so it is not timing closure. Original ATTN arrival1294.07ps / TT−569.32ps remains the measured receiver result. Actual complete first-use, native timing, PG, fixed-face clock and final GEN8 binding are irreducible holds at this stage.

Reproduce bounded ledgers with `python3 model.py`, `python3 census.py input/old_r7w_mapped.v.gz old_complete_census.json`, the corresponding current_sfo_mapped source, then `python3 price_whole.py`. No tool invokes EDA or hardware simulation. All input identities are in manifest.json; no running job was launched or cancelled.

The narrowed D2D storage+producer composition is also explicit: current std master sum5977.71252 + modeled predecessor repair11.0808 +17 positive producer captures5.70078 +179 OR gates18.0063 +four new SRAMs10579.827456 = **16592.327856um²** before new clocks, wires, physical ties after legalization, fillers, PG and spare placement. This is a composition of source/master bounds, not a freshly synthesized measurement. Receiver17 positive captures and10 OR4 gates add6.72138um²; the whole eleven-stage565-bit relay FF+INV area is2084.1381um² inside the conservative61585.92um² outline envelope. Actual MU calendars, occupancy and token throughput remain unmeasured.

For whole-source pricing, used_native_cell_prices.json retains every priced native master area and input capacitance. Full AO/OA table hashes are in large_source_metadata.json; unused timing tables are not duplicated. The actual FF/OR/INV delay tables used in the conditional branch estimate remain included.
