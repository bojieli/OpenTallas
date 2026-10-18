# qkd_host_root_admission as a clock-family cluster (KVJ-A3, 2026-10-17)

Coordinator decision 0dd: the Qwen KV-die HOST root `qkd_host_root_admission` is hardened as a cluster. Each child is a
tile that is flop-first in one clock family (recipe 4, die hold budget). Every clock-domain crossing sits in a CDC leaf at
the seam between two family children. No credits or backpressure are added (static-schedule rule).

Machine-readable plan: `partition_plan.json` (same directory). Census: `census/census_rollup.json`.

## 1. Clock census

Source: proc elaboration and hierarchical mapped synthesis (RVT TT) of `qkd_host_root_admission`, with ENABLE_SERVICE/NATIVE/TOKEN=1
and NL=2 (the kv_die binding). Scripts are in `census/`; the tools are `tools/qwen_kv_die/host_cluster/{clock_tree_census,hier_rollup,partition_plan}.py`.

- Hierarchical synthesis: 784,320 std cells, 102,134 um2, 192,442 flops, and 45 SRAMs (32x 32x128, 8x 512x128, 4x 256x64, 1x 1024x256).
  The flat synthesis of the same root (`kvsys_v1_4_1/host_root_synth_sram`) gives 571k cells, 76.5k um2 and 143k flops, i.e. 0.75x area.
  Every per-child number below is hierarchical, so it is conservative.
- There are 53 flop clock domains on 45 ports in 4 families (fixture `host_owner.hpp`): core 833.3 ps, host 1000 ps, ingest
  1666.7 ps, phy 1043 ps. Within a family every port is driven by the same edge, so **each child takes ONE family clock entry**.
- Per-instance classification (flops hier):

| instance | module | cells | flops | class |
|---|---|---|---|---|
| u_rank.u_adapter.g_slice[0..7] | qfd_link_adp128 | 8 x 6,924 | 8 x 1,932 | single clock ck_phy[i] (phy), 1 SRAM each |
| u_rank.u_phy.u_pad | qkd_host_rx_pad5 | 13,017 | 4,208 | single clock ck_pad (phy) |
| u_rank.u_phy.u_rx / u_tx | ot_qwen_die_cdc_ch W546 PIPE2 | 2 x 38,121 | 2 x 10,452 | CDC phy<->core |
| u_rank.u_control | qkd_host_control_packet_admission | 132,798 | 36,161 | single family core (10 ports), 1 SRAM |
| u_rank.u_bridge.u_queue | qkd_host_qm_ingress16_service_debt | 39,895 | 10,304 | single clock core |
| u_rank.u_bridge.u_ing / u_done | ot_qwen_die_cdc_ch W546 PIPE2 | 2 x 38,121 | 2 x 10,452 | CDC core<->host |
| u_rank.u_qm | qkd_host_native_qm_debt | 174,428 | 36,004 | **mixed** core/host/ingest; u_eng 96,360 cells single-family ingest + 32 SRAM; 4 ot_link_afifo CDCs; 4.5k cells mixed own logic |
| u_rank.u_chain | qkd_host_ingest_chain_pt | 42,566 | 9,228 | single family core |
| u_rank.u_dispatch | qkd_host_boot_dispatch_debt | 37,144 | 7,898 | single family core |
| u_rank.u_guard | qkd_host_service_guard | 44,672 | 12,566 | single clock core |
| u_rank.u_fence | qkd_host_visibility_fence | 2,844 | 772 | **mixed** core 76 / host 696 (own logic) |
| u_rank.u_peer | qkd_host_peer_link | 19,868 | 5,756 | single clock ck_peer |
| u_rank.u_native / u_program / u_program_rx / marker / bootbarrier | | 2,944 / 3,790 / 3,299 / 914 / 492 | | single clock core (u_program 4 SRAM) |
| u_coordinator | qkd_host_tp8_coordinator | 40,033 | 6,197 | single family (ck_coordinator_*) |
| u_peer_codec / u_root_mux / u_records | | 4,537 / 7,290 / 5,309 | | single clock |

**Finding (family map).** `HOST_CLK_INFERRED` puts ck_peer and ck_root_mux in the host family and ck_coordinator_* in core.
The RTL connects them with direct same-cycle valid/ready and no synchroniser. root_mux<->coordinator is 2 x 8 x 512 b;
peer_link.normal_rx feeds program_rx (ck_program_rx, core); coordinator<->rank token request/grant are direct too. They must
therefore be one domain. The plan treats ck_peer, ck_root_mux and ck_coordinator_* as **core** (open decision D2).
With that, the host family is only the native_qm host face, the credit pacer and the fence host side (~4k cells).

## 2. Children

Children are cut on existing module boundaries wherever possible. Flop counts are held near the 15k-sinks guide (flat ~0.74x).
Outlines are estimated at util 0.55 on the 43.2 lattice. Pin bits are an upper bound from the elaboration (cross-level nets count as external).

| child | family | x | std cells hier (flat est) | flops hier | SRAM | outline est (um) | pin bits in/out (upper) | /um |
|---|---|---|---|---|---|---|---|---|
| qkd_hr_phy_adp | phy | 8 | 6,924 (5,193) | 1,932 | 1x 1r1w_512x128_m4_r2c2 | 216.0 x 64.8 | 280 / 279 | 1.0 |
| qkd_hr_phy_pad | phy | 1 | 13,017 (9,763) | 4,208 | - | 86.4 x 86.4 | 1,027 / 549 | 4.56 |
| qkd_hr_core_prompt | core | 1 | 40,025 (30,019) | 11,172 | 1x 1r1w_1024x256_m2_r2c2, 4x 1rw_256x64_m4_r2c2 | 216.0 x 172.8 | 2,937 / 2,242 | 6.66 |
| qkd_hr_core_rx | core | 1 | 49,650 (37,238) | 12,431 | - | 129.6 x 129.6 | 542 / 1,594 | 4.12 |
| qkd_hr_core_tx | core | 1 | 54,742 (41,056) | 15,377 | - | 172.8 x 129.6 | 1,899 / 2,013 | 6.47 |
| qkd_hr_core_guard | core | 1 | 47,616 (35,712) | 13,582 | - | 129.6 x 129.6 | 712 / 462 | 2.26 |
| qkd_hr_core_queue | core | 1 | 43,301 (32,476) | 11,349 | - | 129.6 x 86.4 | 746 / 723 | 3.4 |
| qkd_hr_core_order | core | 1 | 79,710 (59,782) | 17,126 | - | 172.8 x 129.6 | 683 / 1,598 | 3.77 |
| qkd_hr_core_peer | core | 1 | 71,728 (53,796) | 13,434 | - | 216.0 x 172.8 | 2,855 / 3,045 | 7.59 |
| qkd_hr_host_qm | host | 1 | 4,249 (3,187) | 1,316 | - | 43.2 x 43.2 | 7 / 2 | 0.05 |
| qkd_hr_ingest_eng | ingest | 1 | 97,410 (73,058) | 16,680 | 32x 1r1w_32x128_m1 | 388.8 x 345.6 | 1,029 / 366 | 0.95 |
| qkd_hr_cdc_pc | cdc:phy|core | 1 | 76,242 (57,182) | 20,904 | - | 172.8 x 129.6 | 1,082 / 1,082 | 3.58 |
| qkd_hr_cdc_ch | cdc:core|host | 1 | 76,392 (57,294) | 20,904 | - | 172.8 x 129.6 | 618 / 586 | 1.99 |
| qkd_hr_cdc_hi | cdc:host|ingest | 1 | 37,795 (28,346) | 9,346 | - | 129.6 x 86.4 | 586 / 587 | 2.72 |
| qkd_hr_cdc_ci | cdc:core|ingest | 1 | 35,764 (26,823) | 8,818 | - | 129.6 x 86.4 | 553 / 549 | 2.55 |

Members (exact instance paths are in `partition_plan.json`):
- **qkd_hr_phy_adp** = `qfd_link_adp128`, hardened ONCE and stepped 8x, one per ck_phy[i] lane. Its 174-um SRAM forces the 216 x 64.8 shape (3.3:1).
- **qkd_hr_phy_pad** = `qkd_host_rx_pad5` (FDI 1024 b in, W546 word out).
- **qkd_hr_core_prompt** = control_prompt_observed (1024x256 SRAM) + program_loader_target (4 SRAM 256x64) + program_rx_target + record_port.
- **qkd_hr_core_rx** = rx_class_admission. **qkd_hr_core_tx** = tx_class + axi_packet + ctrl_token_service_packet.
- **qkd_hr_core_guard** = service_guard + native_token_endpoint_cancel.
- **qkd_hr_core_queue** = qm_ingress16_service + marker_consumer + emb_boot_barrier + the core faces of native_qm and visibility_fence (re-cut A1/A2).
- **qkd_hr_core_order** = ingest_chain_pt + boot_dispatch_debt. **qkd_hr_core_peer** = peer_link + peer_rank_codec + peer_root_mux + tp8_coordinator.
- **qkd_hr_host_qm** = the native_qm host face + qm_credit_pacer + the fence host side (the whole host family).
- **qkd_hr_ingest_eng** = native_engine (32 SRAM 32x128; ck_qm_ingest/out/bank merged into one ingest entry) + the ingest face of native_qm.

## 3. CDCs: every crossing in a seam leaf

Each CDC leaf has two clock roots, one per side, each under 15k sinks. Each uses `hold_budget: "tile"` with reason "CDC leaf".
It is placed abutting both family children it joins.

| CDC leaf | modules (wclk -> rclk) | between |
|---|---|---|
| qkd_hr_cdc_pc | ot_qwen_die_cdc_ch u_phy.u_rx (ck_phy_rx_w -> ck_phy_rx_r), u_phy.u_tx (ck_phy_tx_w -> ck_phy_tx_r) | phy_pad / core_rx, core_tx |
| qkd_hr_cdc_ch | ot_qwen_die_cdc_ch u_bridge.u_ing (core -> host), u_bridge.u_done (host -> core), fence synchronisers | core_queue / host_qm |
| qkd_hr_cdc_hi | ot_link_afifo u_qm.u_hx W514 (host -> ingest), u_qm.u_cx W64 (ingest -> host) | host_qm / ingest_eng |
| qkd_hr_cdc_ci | ot_link_afifo u_qm.u_ox (ingest -> core), u_qm.u_rx W256 (core -> ingest) | core_queue / ingest_eng |

The single-bit sticky raw_faults that enter guard are already 2-flop synchronised inside `qkd_host_service_guard`; the pin register adds a third stage.
Resets: each child gets its own reset relay on its family clock (regional reset).

## 4. RTL action list

- A1 `qkd_host_native_qm_debt`: its own logic is mixed (core 586 / host 595 / ingest 352 flops plus 3 reset syncs). Re-cut it into core, host
  and ingest faces, with the 4 afifos as sibling instances. Gate: a cycle-exact lock-step bench against the current module.
- A2 `qkd_host_visibility_fence`: split into fence_core, fence_host and the crossing synchronisers. Gate: a lock-step bench.
- A3 `qkd_host_qm_clock_bridge_service_debt`, `qkd_host_phy_cdc5`, `qfd_link_adp512_split`, `qkd_host_control_packet_admission`
  and `qkd_host_packet_bundle_admission` have no flops of their own. They need a hierarchy move only, no RTL change.
- A4 Rank and top glue (491 + 14 cells): move each cone into the child that consumes it. A cone that mixes families gets a synchroniser in the receiver.
- A5 One wrapper `qkd_hr_<child>` per multi-member child: one family clock port drives every member clock, plus one reset relay.
- A6 No credits are added. Each new same-family cut adds 1 cycle out and 1 cycle in (pin registers). The composition bench must show that every existing
  v/d/cr credit loop still covers that +2 RTT.
- A7 Option: set ot_qwen_die_cdc_ch MEMM=1 (an existing opt-in) on the four W546 channels. This puts each FIFO body in a dual-clock 1R1W macro and removes ~100k hierarchical std cells from the CDC leaves.

## 5. Cluster outline vs die contract

The child outlines total 487k um2, which is **1.21x the 777.6 x 518.4 slot (403k um2)**. They do not fit at hierarchical sizes; flat-synth sizes come to ~0.9-1.0x, with no room for seams.
Proposal: grow the slot to **950.4 x 648.0** (616k um2, 0.79 occupancy, 20-um seams). Alternatively keep 907.2 x 604.8 (0.89) and take A7.

Band intent:
- S edge: the 8 adp tiles as 4 x 2 (864 x 129.6) over the serdes_host FDI.
- Above them: phy_pad + cdc_pc, centred, with core_rx to the W and core_tx to the E.
- Middle: core_order (chain_f / slice_* on the W/E faces), core_guard, core_prompt and core_queue.
- N: core_peer (peer link N), and ingest_eng in the NE.
- Between core_queue and ingest_eng: a column of cdc_ci | cdc_ch | host_qm | cdc_hi.

Every SRAM origin is on the 43.2 lattice with 20-um channels. Each child's clock entry is on the face nearest its register mass.

## 6. Open decisions (coordinator)

- D1 Slot growth (die lead).
- D2 Family of ck_peer / ck_root_mux / ck_coordinator_* (HOST owner; update `kv_die.HOST_CLK_INFERRED`).
- D3 The die feeds 4 family clocks (+8 ck_phy lane entries) instead of 45 ports.
- D4 The host family is tiny. Options: keep the 43.2-um host tile, fold it into a 3-clock CDC leaf, or remove the core->host->ingest hop.
- D5 Do the pre-existing intra-host credit channels fall under the static-schedule rule? The host and PHY are off-die boundaries.
- D6 fdi is 2,085 b on a 100-um window (20.8 /um), set by the serdes hard-IP face.
- A8 Found by the c1 gate: in `qkd_host_rx_class_admission`, the read pointer ir[1:0] of the 16 x 514 ingest queue drives 8,226 and 4,115 loads (textbook high_fanout WARN).
  Fix: replicate the pointer per 64-bit slice (registered copies, 0 cycles). Not blocking: TT setup is +204 ps.

## 7. First child kits (recipe 4, hold_budget die). Pre-route gates c2 at 3389941db, TT, with --cts

qkd_host_root is CRITICAL: there is no REVIEW.json and nothing is submitted. Specs are in `tools/ref_tile/specs_qhost_cluster/`.

| kit | top | outline | util | gate | CTS TT insertion / spread | sinks | setup / hold WNS (TT pre-route) |
|---|---|---|---|---|---|---|---|
| qkd_hr_phy_adp (x8) | qfd_link_adp128 | 237.6 x 86.4 (2.75:1, set by the 174-um SRAM) | 11 % std (33.6 % fill) | PASS | 236.6 / 62.1 ps | 2,491 | +271 / +19 ps |
| qkd_hr_phy_pad | qkd_host_rx_pad5 | 172.8 x 86.4 (pin-limited: 1,026-pin S face) | 22 % (WARN) | WARN | 188.2 / 20.0 ps | 5,765 | +122 / +42 ps |
| qkd_hr_core_rx | qkd_host_rx_class_admission | 151.2 x 129.6 | 48 % | WARN (high_fanout ir[1:0], A8) | 219.8 / 15.7 ps | 14,558 | +170 / +14 ps |

The c1 gates found pins clustered on partial faces and the clock on the W face, away from the data. c2 fixes this with per-port pin_ranges and
route.pin_balance: buses cover the full face (<= 6.2 /um) and ck sits mid-face between the data buses. Moving the clock cut adp insertion/spread from 302.6/89.0 to 236.6/62.1.
The SRAM sits on the asap7 track lattice (offtrack 0) at (31.5, 28.1). The 43.2 lattice applies to the child origins in the cluster;
an adp SRAM on the 43.2 lattice would need a 108-um tile (20-um pin-face margin).

## 8. r2 (10-17 evening, after coordinator decisions D1-D6): protocol-safe partition and generated cluster RTL

**Seam rule.** Every child pin is registered (pin_regs, +1 in / +1 out), so no same-cycle valid/ready may cross a
seam (die interface rule 2026-10-07). The r1 cut audit (census elaboration, every member-to-member net) found four:
AXI s_*/m_* between fullcontrol (core_prompt) and qkd_host_axi_packet (core_tx); token request/grant valid/ready
between qkd_host_ctrl_token_service_packet (core_tx) and the coordinator (core_peer); the cancel handshake
ctrl <-> peer codec; and, inside native_qm, every FIFO rd/rempty, wr/wfull and engine d/in/w valid/ready that an
A1 face cut would place on a seam. r2 (`partition_r2.json`) removes all of them; every remaining seam is a credit
channel (v/d/cr), a registered single-cycle event or a level.

| child | members | family | note |
|---|---|---|---|
| qkd_hr_phy_adp x8 | qfd_link_adp128 | phy | direct; closed view stands (CLOSED_STANDS) |
| qkd_hr_phy_pad | qkd_host_rx_pad5 | phy | direct |
| qkd_hr_cdc_pc | u_phy.u_rx, u_phy.u_tx (ot_qwen_die_cdc_ch W546 PIPE2) | phy/core | wrapper |
| qkd_hr_core_rx | rx_class_admission, IR_REPL=1 (A8) | core | direct |
| qkd_hr_core_tx | tx_class | core | wrapper |
| qkd_hr_core_prompt | fullcontrol (+prompt pins), hc_station, **axi_packet**, program_loader, program_rx, record_port + 45 glue cells | core | wrapper |
| qkd_hr_core_peer | peer_link, peer_rank_codec, root_mux, tp8_coordinator, **ctrl_token_service_packet** + 4 glue | core | wrapper |
| qkd_hr_core_guard | service_guard, native_token_endpoint + 25 glue (service_faults, observed faults) | core | wrapper |
| qkd_hr_core_queue | ingress16 queue, marker_consumer, emb_boot_barrier | core | wrapper |
| qkd_hr_core_order | ingest_chain_pt, boot_dispatch | core | wrapper |
| qkd_hr_cdc_host | bridge u_ing/u_done, credit pacer, visibility fence | core/host | wrapper; D4 fold of the host family |
| qkd_hr_ingest_qm | the WHOLE native_qm_debt | core/host/ingest | wrapper (one ck_ingest drives clk_i, clk_i_bank, clk_i_out) |

- **A1 / A2 are superseded.** native_qm and the fence keep their internal FIFO and toggle/ack crossings; their own
  faces are already registered credit channels, so the modules themselves are the multi-family leaves.
- **A3/A4/A5 = generated, not hand-written.** `tools/qwen_kv_die/host_cluster/gen_cluster.py` elaborates the
  UNCHANGED flat sources (yosys 0.68), keeps members, flattens the wires-only levels and moves each of the 74 glue
  cells into the child that consumes it (prompt 45, guard 25, peer 4). An explicit Python submod cuts one module
  per child with one port per family clock net. Output: `rtl/qwen_sys/host_cluster_20261017/qkd_hr_cluster.v`, with
  the D3 face `ck_core, ck_host, ck_ingest, ck_phy_fam, ck_phy[7:0]`. The parent is wires only plus the 8 adp instances.
- **D2** is applied in `kv_die.HOST_CLK_INFERRED`.
- **Composition bench** (`bench/cluster_gate.py`, Verilator 5.050): flat root vs cluster in lock-step, with the 4
  families clocked as in host_owner.hpp. All 73 outputs are compared after every evaluation, over 3 seeds x 2 modes
  x 20k core cycles: **PASS 6/6** (`benches/cg_exact.log`). Mutants, each a child's reset input inverted at the
  parent: all six core children **FAIL** (`benches/cg_mutant_*.log`). A mutant on core_rx rx_d[5] is NOT detected,
  because random stimulus does not reach the rx packet path. That is a coverage gap: the bench proves the binding of
  what it reaches, not the packet datapath.
- **Kits (recipe 4, hold_budget die, pins <= 6/um).** prompt 259.2^2 (5,335 pin bits) and peer 302.4^2 (6,301) are
  pin-limited: the u_ctrl status faces (tk8 744 b, kst8, boot8, service epochs) and the 528-b packet channels set
  their size.
- **CDC leaves.** `cdc_synchronizers` cannot admit the Gray FIFOs (no 2-D register names; FIFO storage is read
  whenever the synchronised pointer differs, not only while an event is in flight). The reviewed mode
  `reviewed_gray_fifos` (branch claude/kvhcl-cdc-1017, NOT on main, review pending) admits cdc_pc. cdc_host also
  needs the fence's toggle/ack event syncs in the same leaf, and ingest_qm needs its 32 ingest-clock SRAMs. Both are
  extensions being built on claude/kvhcl-cdc2-1017.
