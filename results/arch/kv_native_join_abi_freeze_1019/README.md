# Private selected-SU native owner join: pre-edit ABI and full state proposal

Artifact only, base ea19ed290. No RTL, compile, simulation, binding, or physical work. This proposes a complete functional common-clock component allocation. Emitted source must reconcile every declared bit before launch. Production clock crossings, H, response deadline, latency, SRAM realization and physical cost remain NULL/HOLD.

## Exact retained baseline

Use canonical retained scheduler SHA acf1208a092735df94d7555f76b19c9971b9ae4701e9dcbdc96c02a8ab5b14c2. Its bytes equal the newest integration_final scheduler, not historical private/integrated_* SHA547f8188. Exact added-declaration census is1566 bits at H64 (see scheduler_added_state_census.json), bridge27, eight endpoint additions16: total1609. These are declarations including storage, not mapped FF count. Historical integrated_NOTES1549/2848 describes a source lacking17 owner-record bits and predates duplicate-client descriptor corrections. The exact diff is retained. Final canonical event storage is16*(116+62+1)=2864 bits. The source snapshot in the identity model matches canonical scheduler byte for byte.

All25 frozen identity-model input hashes were verified (source_manifest.json); retained revision hashes are separately recorded. The manifest is an inspected source-family list, not an executable complete compile manifest. The actual new bench must separately pin its complete transitive source and helper closure.

## Ownership and proposed ABI

Descriptor namespace stays independent: client16, slot8 and descriptor generation2. Native namespace is actual request TAG59 plus native generation2, never clientTAG zeroextension. Actual allocation epoch0 is valid. TAG is {epoch16, stage6, input_token18, position13, segment6}; request stage0, terminal stage37, segment0. Next token remains returned payload, never the TAG input token. Selected8 participants are ranks, not users.

Proposed qkd_host_native_owner_join_rc ports (all event inputs in the explicit common component clock, raw_por_n reset):

| Event/input | Payload and authoritative source |
|---|---|
| issue_v / issue_ready | client16, slot8, descgen2, rawpos18, input18 from functional scheduler issue_fire; reserve before actual eng_start |
| package_accept_v | input18, rawpos18, package_gen2 from true ready accepted pkgctl start; never observer step_issue_v |
| hc_accept_v | token18, position18, gen2 from actual token-service retained HC reservation selected for allocation; keep PW/DW/START atomic |
| allocation_fire | actual allocator request_valid && request_ready with request TAG59 derived using actual pre-edge next_epoch and request tuple; gen2 |
| raw_done_v | actual raw completion plus exact active native TAG59/gen2 association; report_needed from real generated/CQ classification |
| certificate_v | exact accepted native TAG59/gen2 and genuine health cutoff/certification; no all-healthy vector |
| event_copy_v | exact active TAG59/gen2 and descriptor owner association when genuine event row is inserted |
| terminal_v | exact acknowledged terminal TAG59/gen2 from lifecycle acceptance |
| report_drained_v | exact event native key and descriptor owner after genuine CQ B; no-CQ prompt uses real retirement, not invented DMA |
| post_retired_v | actual POST terminal TAG59/gen2 |
| no_native_v | actual unready/package failure of pending step before central allocation; drains/reports failure with native_valid0 |
| outputs | pending association ready/valid; binding_valid, bound request TAG59/gen2 and descriptor owner; protocol_fault; allocation/dispatch eligibility |

Two-phase package/HC binding: issue reserves pending; true package acceptance establishes actual gen; actual HC reservation must match input/position/gen; only then can true central allocation atomically transfer into empty active. Allocation predicate must gate both real allocator request_valid and corresponding outward request_ready consistently. Do not infer acceptance from delayed request_ready_q. Add no anonymous wait after allocation: the binding is captured on its actual edge before dispatch. Chosen hooks are actual package hc[38] and station cmd_v && cmd_hc[38], with zero new holding registers; their existing held tuples supply the handshake. HC phase must be captured before a later actual allocation edge; same-edge HC/allocation is forbidden in this frozen contract. No extra edge can be called free; actual source must establish whether existing registered seams absorb it.

Check request stage0/segment0, full position high bits zero, token/position/gen exact. Terminal/certificate/report matching explicitly reconstruct terminal stage37 or request stage0 as appropriate. Each stage check is combinational, not an uncharged state bit. A duplicate/missing/out-of-order event or mismatch sticks protocol_fault until raw POR, blocks success/admission, and preserves raw cleanup and accepted transaction drain. Do not gate endpoint credit/result release or rawdone on certificate. A real failure without allocation remains typed NO_NATIVE and cannot fabricate a TAG. Existing failure_pending/report_once and descriptor error paths remain functional.

## Complete proposed register allocation

Pending66: client16+slot8+rawpos18+input18+pkggen2+descgen2+phase2. Phase EMPTY/ISSUED/PACKAGE/HC; there is no additional valid or handshake flag. Source valid must remain held until genuine acceptance; the corresponding phase captures exactly once. Active95: client16+slot8+requestTAG59+nativegen2+descgen2+valid1+raw_seen1+cert_seen1+terminal_seen1+event_copied1+post_seen1+report_needed1+report_drained1. Sticky protocol_fault1. Join total162. No other join registers or duplicated rank masks/payloads are proposed. Existing scheduler saved_* retain real result payload; existing pending_identity80 becomes actual native identity representation only after binding and cannot certify before then. Source-owned finite health/deadline counters remain the existing explicitly typed component counters.

Pending may coexist with prior active while POST is outstanding. Active frees only after exact POST and real report drain; terminal/credit/event-copy alone never releases it. Do not accept a new allocation while active is full. Allocation and POST in the same edge conservatively do not reuse the active slot; any optimization needs explicit next-state proof. report_needed comes from actual raw completion; prompt report_drained requires genuine non-CQ retirement; generated report_drained requires actual matching CQ B. All lifecycle, codec and POST gates remain unchanged.

Event metadata adds native_valid1+descriptor_gen2 per row, and same3 saved bits:51 bits. Row is116+62+owner_record1+native_valid1+descgen2=182;16 rows2912 indexed bits. Native lineage62 is {terminalTAG59,nativegen2,certified1}. Descriptor checks instead use event client16+slot8+explicit descgen2+owner_record, never nativeTAG==descriptor owner_tag. Active and pending descgen each cost2 bits as already counted. Descriptor owner cannot be reused while earlier queue/saved/report ownership survives: canonical release requires SL_DRAIN, true owner drain, no pending/inflight, ev_n0, D_IDLE, no failure_pending. Assert this lifetime in emitted source; modulo4 descriptor generation alone is not freshness proof. Duplicate client descriptor errors keep owner_record0 and cannot consume active owner failure report.

Increment213 = join162 + metadata51; proposed total relative original selected component1822 = scheduler1566 +bridge27 +endpoint16 +213. No added wrapper register is included: this exact budget applies only to a common-clock functional component with source predicates exported as wires and existing held tuples reused. Any actual source holding/crossing/landing registers are additional and must be enumerated before compilation/adoption. The1822 figure is not a production physical estimate.

## Minimum source seams and edit ownership

1. Scheduler owner: canonical private scheduler only. Export functional issue tuple including input token and descriptor gen; consume bound key, attach immutable native_valid/lineage/descgen to events and cq_saved; preserve descriptor lifetime, raw cleanup and offered AXI stability. Do not rewrite public scheduler.
2. Package/HC owner: private copies of selected service-pins, qkd_host_ctl and pkgctl only as needed to export actual ready accepted start/gen; actual HC station/token-service tuple is already explicit. Preserve existing61/182/93/120 payload widths, four command reservations and atomic PW/DW/START. Do not add client bits to native TAG or infer acceptance from d_start observed a cycle late.
3. Allocation/join owner: private allocator exposes allocation_fire and pre-edge acceptance TAG/gen; private lifecycle/coordinator/services propagate that seam and terminal/POST events; private join holds complete162-bit association. Cohort/codec/POST use existing8 request,8 return and8 release mechanisms independently. No replacement bitmap.
4. Endpoint owner: use existing private retained endpoint unchanged unless an explicit accepted-HC/result/retire identity export is necessary; these exports must derive actual accept/issue/result_ok/retire, not a testbench transaction. All8 actual endpoints and real transport are bench dependencies.
5. Harness owner: connect selected scheduler/package/actual HC/allocator/cohort/8 endpoints/result codec/POST using complete frozen inputs. Public root, die generator, MU family, PHY/controller reset retention and physical source binding remain outside this bounded component. Existing selected POST serialization remains mandatory. Separate clocks cannot be declared safe by this common-clock bench; actual landing/phase/reset qualification remains OPEN.

Upstream if-pins/fullcontrol/control-prompt/control-packet/packet-bundle/root wrappers do not need edits for this bounded harness if it instantiates at the stated actual seams and connects existing dataflow directly. A production root needs coherent private wrapper propagation and actual held transport; omission is not a production closure claim. No RTL or build launched by this packet.
