# Explicit hardware/domain proposal and fixed edge price

Status: implementable contract proposal, not adopted RTL and not a clock certificate. No hardware phase interval is invented. Actual native corners, endpoints, reset cone and compiler join pricing remain required before any source build/gate.

## Exact current-binding absence receipt

Die owner directly inspected two current generated contracts read-only:

* DIAG/source11bf `/srv/opentallas-scratch/claude/codex-gen2e4-diag-s3-1020/views/contract.json`, SHA256 `9d1a3f207588adfca70b21075df2f9ef1c394d0a191909c8eae9bb65f8a0abb8`:16 `su_{SW,SE,NW,NE}{0..3}` instances use master `ot_hbm_su_static_pgslice_lg`; no `ot_hbm_su_static_pgslice_rgf_lp` or SAFE3 successor, and no PGLG `ck_s/ck_r0..3` clock_reset ports.
* Current GENREACH expanded/fprsv input `/srv/opentallas-scratch/claude/codex-hbm-genreach-forkfix-1020/views/contract.json`, SHA256 `1e46f68cfdd7271f3e22714d0b205714bbe69259a3a4497be47c2a4aa0442ec4`: likewise old `pgslice_lg`, no rgf_lp/SAFE3 successor. Its unrelated rf0070 serial-relay ck_s ports from `hb_ckgen.pll_serial` cannot establish a source for the unbound PGLG successor.

Separately, indexed source search `git grep 'ot_hbm_su_static_pgslice_rgf_lp' claude/hd4g-gen2e4-1019 -- rtl tools physical/ref_tile` had no match. This statement is restricted to that ref/path search; it is not a claim about all production trees. Candidate lg4's five native clock input ports and source reset topology are documented in HBM_ANCHORS.md. QW/S81 owners report no actual source-bound regional phase or reset-order certificate. Existing consumer phase admission is OPEN.

Die owner's follow-up exact old `su_SW0` mapping in9d1a3f contract:

|Actual old master port|Width|Domain|Actual source|
|---|---:|---|---|
|clk_bank|32|serial|hb_ckgen.pll_serial|
|clk_bank_macro|192|serial|hb_ckgen.pll_serial|
|clk_bcast|4|serial|hb_ckgen.pll_serial|
|clk_ctl|1|serial|hb_ckgen.pll_serial|
|clk_insert|128|serial|hb_ckgen.pll_serial|
|clk_lane|256|serial|hb_ckgen.pll_serial|
|clk_side|6|serial|hb_ckgen.pll_serial|
|pg_clk|1|stream|hb_ckgen.pll_stream|
|rst_bcast_n|4|serial|hb_ckgen.por_serial|
|rst_lane_n|32|serial|hb_ckgen.por_serial|
|rst_n|1|serial|hb_ckgen.por_serial|

`bridge_rst_n` width1 exists on that interface but has no clock_resets receipt. Its source/first-active edge is unproven. `hb_ckgen` master is `hfd_ckgen_nolink`, source `rtl/hbm_accel/control/hfd_ckgen_nolink.sv`, dependency `hfd_ckgen.sv`, directly connected to u_pll outputs. Die owner's CKGEN ETM has real FF paths and three ideal clocks; the PLL remains an interface-only pin reservation with no implemented divider/configuration/phase certificate. Thus the table proves an old binding, not absolute period, reset first-active order or a successor mapping. A future proposal may explicitly select the existing serial source, but must not label all new PGLG clock ports as already bound to it.

The candidate lg4 kit declares `clock_relationship={kind:same_pll_fixed_phase,ratio:[1,1],phase_ps:0}` and `clock_data_paths=related_same_frequency`. Those declarations are not source hardware evidence; they do not close the current missing phase/reset certificate.

## Concrete alternative to an unspecified phase relationship

Offer a new opt-in synchronous clock-domain contract, separately priced from the existing five/19/9 arbitrary regional input relationship:

1. Select ONE actual production clock cell output (exact source instance/master/view/port required) and one implemented common reset-release root. Connect the source producer capture, writer SRAM, reader SRAM, final output FF, FIRST external child capture and every inherited arithmetic/SRAM/PMA clock in that admitted pipeline to explicitly compatible delivered branches of that signal. Connecting only the backend while leaving the consumer on its old clock would move the CDC outside the backend and is forbidden. No separate PLL output, inferred identical frequency, RTL clock alias disconnected from physical source, clock mux, or independent reset synchronizer may stand in for this connection.
2. The parent owns separate physical regional CTS branches, but their common source is explicit in the production netlist and generated-clock/clock-entry constraints. Actual linked write/read macro and register pairs must pass the paired all-corner phase/minimum-pulse/period/setup/hold certificate. A common logical source removes frequency ambiguity; it does not waive delivered skew. Native clock propagation and paired phase measurements are still necessary.
3. A synchronous reset-release root registers an explicit release on that same clock. Equal-depth bounded reset trees distribute it; their physical setup/hold and first-active local edges are proved against the same root. Do not independently synchronize each region and then assume equal count. Required assertion duration is explicit and checked; all externally observable output data is zero until the tracked write/read epoch becomes valid, with arbitrary SRAM initial contents.
4. For the admitted first family, internal SRAM ring depth is at least4 and read offset is explicitly2. At common clock edge e, SRAM writes the source input word to slot e mod D. At edge e+1 it reads that slot, which was written a full clock earlier. At edge e+2 a final output FF captures the synchronous macro read, with a matching registered valid/zero path. The receiving child samples that output at edge e+3. A direct wire would have let that child capture the same source input at edge e, so the backend ADDS three edges relative to the flat direct connection. From a source producer FF update at e-1 through the receiving child capture at e+3, absolute latency is four edges. The read occurs on a different edge from the same-address write; actual write completion before read setup must still be checked.

Under this new contract, width replication and reset/control copies retain exactly the same epoch and edge ledger. Source pipeline SW and destination pipeline SR each add their own explicit edges. Memory wc/read counters are initialized with the corresponding fixed reset/epoch offsets; the generator must emit the event-edge ledger and prove it, not assume a counter offset from nominal depth.

`direct_domain_map.json` enumerates all16 HBM,17 S81 and183 QW source producers, exact writer/read/final instance clock/reset connections, and FIRST external child reader port with its declared clock/reset port bindings. It pins each generated parent source and parser SHA. This is a direct parent source map, not a proof of child-internal clock inheritance. Child internal arithmetic/memory/PMA clock roles are explicitly marked REQUIRES_CHILD_PROOF; unresolved port-level consumers carry MISSING. A coherent common-source proposal must close those downstream roles as well as the backend.

For HBM the migration includes the generated regional child ck inputs, each arithmetic leaf's clk_stage_0..7 and clk_insert_0..3, and each bank's clk/clk_rd/clk_ws/clk_macro0..5 where present. These are inherited physical clocks, not interchangeable aliases by name. The raw SRAM clock timing, parent clocks, complete hardware fanout/reset tree and command calendar all require requalification. For S81, PMA receive/transmit or recovered clocks cannot be moved to a serial source merely to simplify the backend; any such migration would be a separately priced protocol/hardware redesign. For QW, regional child clocks and all internal SRAM/compute pipelines must retain or explicitly re-solve their periods, offsets and reset first-use.

The following age table is conditional on the whole producer-through-consumer domain migration being accepted and proven. It does not establish preserved ages for children left in their original domains, nor preserve nanosecond cost if any child period changes. A changed period is charged in the command/dependency calendar and source hardware in addition to the edge count.

|Consumer existing contract|New admitted common-clock baseline|Minimum change before reach relays|
|---|---|---|
|HBM D2/K1/E1, +2 child edges|D>=4, explicit offset2, +3 child edges|+1 edge per migrated crossing; joins/pads and first-use reset priced|
|S81 D4/K2/E2, +3 child edges|D>=4, explicit offset2, +3 child edges|0 only if new common-source delivery/reset contract is accepted and proven|
|QW D4/K2/E2, +3 child edges|D>=4, explicit offset2, +3 child edges|0 only if new common-source delivery/reset contract is accepted and proven|
|QW fallback D8/K4/E4, +5 child edges|Either preserve explicit +5 age with extra fixed output delay, or re-solve to new +3 age|No automatic -2 benefit; full dependency/bundle/reset re-solve required|

For every migrated crossing, final charged ADDED age is3+SW+SR relative to the original direct child capture; absolute producer-FF-update to child-capture age is4+SW+SR. Replace the old added crossing age exactly once. For old HBM K1, absolute producer-to-child age is3 and added age2; the proposal changes those to4 and3 before relays, so minimum growth is exactly1. This is a proposed fixed interface price, not achieved timing or a rate claim. For short FF crossings retaining the old backend, the old age remains unless the reset/clock contract also changes. Parent joins therefore need per-edge ages, not one global replacement constant. HBM D2->D4 storage/macro cost uses the same physical32row master, but logical protocol and reset/epoch assumptions still change and require acceptance.

If a consumer cannot supply a single actual common source with provable delivery and reset epoch, keep the general dual-clock API blocked until a hardware-backed related-clock certificate exists. An asynchronous FIFO/credit handshake is not an authorized substitute for the static schedule.

## Endpoint-driven relay price

For actual source-pin s, proposed memory input/output pin m, final register r and destination-use pin d, record each physical route segment. Source-side hops SW are charged to reach the SRAM write pins; destination SR hops are charged after SRAM read/final capture. All data and coherent valid/epoch fields travel the same fixed number of edges. Each ordinary register hop must satisfy <=405um and real setup/hold, not only a centre-distance division. Per-bit longest paths and obstacles determine the requirement; ceil(ManhattanDistance/405) is only a necessary hop-count lower bound.

The actual HBM native bank/read anchors exceed810um for some matching bits, but they are old register locations, not approved new source-to-memory placement points. QW's actual183 pin/orientation geometry is missing. Hence no exact SW/SR is assigned here, and no complete price/gain is claimed. This explicit common-clock interface and +1 HBM minimum can be reviewed now; source build waits for an accepted actual hardware source/reset schedule and endpoint ledger.
