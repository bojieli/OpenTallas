# D8 hybrid storage and edge model

MODEL ONLY, pending ROOT review. No RTL, prototype, synthesis, gate, native qualification or token-rate claim. This refines cdf9e0528, fd363bb2c and the exact f68bd657b nine-lane failure inventory. Full original bus ordering is retained. Additional semantic/control/lifetime fields remain uncertified; no field is omitted on an unused-bit assumption.

The proposed hybrid uses six independent FF pointer rings and three complete SRAM words. A coherent wide word is never divided to evade the storage rule. A 16-bit region is a kept fanout/reset copy of the same pointer, not a separate FIFO. The choices depend on the complete declared architecture, including state outside the array:

| Lane | W | Direct FF bits | Gated FF bits | Proposed choice | Macros |
| --- | ---: | ---: | ---: | --- | ---: |
| dvs_W5.ag_wo -> tt_ctlm.ag5 | 10 | 184 | 312 | FF pointer ring | 0 |
| dvs_W5.dd_wo -> native59.dd_i | 548 | 5740 | 10444 | dual-clock SRAM | 9 |
| dvs_W5.ss_wo -> tt_ctlm.ss5 | 107 | 1183 | 2135 | FF pointer ring | 0 |
| io_collective.cmd_free -> sys_face.io_cmd_free | 1 | 103 | 159 | FF pointer ring | 0 |
| io_collective.fault -> sys_face.io_fault | 1 | 103 | 159 | FF pointer ring | 0 |
| io_collective.shared_fault -> sys_face.io_shared_fault | 1 | 103 | 159 | FF pointer ring | 0 |
| native59.dr_o -> dvs_W5.dr_wi | 520 | 5446 | 9910 | dual-clock SRAM | 9 |
| tt_ctlm.cmd -> dvs_W5.cmd_wi | 116 | 1285 | 2317 | FF pointer ring | 0 |
| tt_ctlm.hr -> dvs_W5.hr_wi | 453 | 4759 | 8655 | dual-clock SRAM | 8 |

The direct FF model explicitly declares eight payload/4-bit-epoch banks, one output bank, eight externally reset valid bits, both 4-bit counters, registered K, expected epoch, read slot/run, initialization/full/warm/ready, source/receiver reset landings and sticky fault. Each 16-bit region reserves eight kept write-select and eight read-select FFs, two reset stages per domain and one run FF. Total **9W+73+21ceil(W/16)**. This is a proposed declaration budget, not a measured existing implementation. Additional required lifetime, reset or fanout state must be added before final selection; W107 has865 bits and W116763 bits of headroom to2048. The write-enable feedback muxes, complete8:1 read mux and epoch compare also need mapping. Data pins feed at most eight selected first-bank FF paths; actual BUF/INV-transparent all-driver fanout and first/last-Q registration must still be audited.

The comparable gated FF architecture adds eight read payload/epoch banks, delayed regional selects and aligned expected/run/slot state: **direct+8(W+4)+8ceil(W/16)+8**. W107 and W116 then exceed2kb. That is a reason to evaluate a genuinely different direct-read pointer architecture, not a reason to pretend its gated clock constraints remain applicable. Direct FF uses ordinary write-root clocks on every write-bank FF with enabled feedback, and ordinary receiver-root output FFs. Its complete ungated clock load must be priced. Existing per-bank ICG/native families do not qualify it.

The three wide lanes need **26 real ot_sram_1r1w2c_32x64_m1 macros**,52 functional macro clocks,53248 physical bits and14393.328768um2 before soft cells, access, clock trees, halos or PG. Their complete records are553/525/458 bits, preserving548/520/453 bus bits plus four epoch bits and one written bit. Each independent ring has its own addresses/epochs/clocks. Selected views, compiler/calibration hashes, TT/FF/SS arcs and every source/root/ordered instance from cdf9 are embedded in model.json. W/E faces have103 contacts over17.304um=5.95238/um. Actual array escape/PG/parent slot is unqualified. The hypothetical43.2-lattice grids are structural reservations only.

The model declares4672 soft FFs across all nine lanes, including SRAM control and returned-metadata alignment reservations. This is not mapped cell cost. The SRAM branch uses W+46+2B soft FFs, reserving full output payload, all common controls except stored bank epoch, five returned metadata/alignment bits and per-macro read/write enable copies. Exact state can change when RTL is permitted; changing it requires recount and source equivalence. Macro TT clock cap is485.9816fF; one full read edge1553.826fJ, write edge2946.666fJ, eight initialization writes23573.328fJ. These omit soft clocks/logic/wire energy explicitly. Chosen FF/ICG masters, per-domain soft clock cap, mapped logic, total silicon, PG and channel cost remain NULL; a numerical total would be unsupported.

A SRAM write is synchronous storage, but is **not evidence of an explicit input-face FF**. If a separate input-face register is required, add1521 FFs (total6193 declared) and shift macro write by one source edge. Keeping the old R edge then reduces the prior gated1.25T minimum age to0.25T=208.333ps, already below60ps uncertainty+150ps reserve before macro setup. Neither that shift nor an early read is authorized. ROOT must accept the actual registered boundary proof or price a new source/read edge from the real producer/consumer ledger.

| Edge | Legacy production/direct FF candidate | Gated candidate | SRAM alternative |
| --- | --- | --- | --- |
| W(s,j) | write selected full bank | write selected full bank | write full record, only if no extra input stage |
| R(j) | mux full bank into output FF | capture selected read bank | synchronous registered read |
| R(j)+1 | next independent word | capture prior selected read bank into output | capture prior macro output into output FF |

Thus SRAM can only reuse the gated read-capture edge conditionally. It adds a receiver edge relative to legacy direct output. Direct FF must close its actual8:1 data/epoch path with native clocks; it gets no bank-period or multicycle exception. The previous1.25T write-to-read-bank/3.875T read-to-overwrite figures are scenario arithmetic for the gated model, not this FF timing proof or absolute output latency.

The required D8 ABI is D=8, AW=3, four K strap pins k0..k3, wc/rc modulo16. Payload remains [W-1:0], epoch occupies [W+3:W], written bit W+4. Write index is wc[2:0]; read expected epoch is rc-k_q and index its low3 bits, with predecode from the previous rc+1-k_q. wc and rc denote preedge values at their actual captures. K=0 denotes a logical16-edge warm threshold. Own-instance ties supply all four static straps; no silently zero-extended three-pin binding.

Historical wrappers emit D4/three pins and lane_groups computes modulo8. model.json preserves each old K and lists the arithmetic (E+G-R0)mod16 **only as an audit value**, never a candidate strap. Extra face/meta reset stages change G/R0/zero edges. Even the exact complete ordered bus does not certify its internal validity/epoch/command lifetime. The source-authored semantic field ledger, actual final forwarded write-clock pin, receiver root, source PLL/divider phase, reset release/pulse/recovery and cold/warm/stopped-clock first-use are all required and currently UNKNOWN. Modulo16 alone cannot prevent a stale record alias after a long asymmetric stop/reset.

Read disabled holds rd_out. Arbitrary memory/rd_out state must be used. Eight external asynchronously invalidated row-valid bits cannot be replaced by an uninitialized stored written flag. **Same-address simultaneous cross-clock read/write is FORBIDDEN; there is no cross-clock OLD guarantee.** All eight distinct writes cost four more source edges than D4, but are not a first-use or whole-token price. Mixed resets/stops must invalidate use and preserve a fixed finite publication/consumption calendar without credits, waiting or backpressure.

Next, before RTL: ROOT selects the hybrid architecture and resolves the macro-input register obligation; source owners supply semantic fields and actual4-bit-K/reset/read/output edge manifests for all nine lanes. Then prove the smallest mechanism per genuinely distinct architecture across K0..15, source/receiver phases, FIRST0/1, arbitrary initial state, cold/warm/abort and stopped-clock restart. Mutants must change slot/epoch, allow stale early use, collision, wrong enable or dropped metadata. Map every port/state/control, prove transparent all-driver fanout<=32 and <=405um reach, count real cell area/clock cap and every contact/PG path, and review actual TT setup/FF hold and source phase before any gate. Only actual compiler composition can assign absolute SU/MU token delta.

The original CTLM HR age16 instead of20 failure512/512 and all nine D4 E_sta6/7 failures remain unchanged. No old failed receipt is overwritten.
