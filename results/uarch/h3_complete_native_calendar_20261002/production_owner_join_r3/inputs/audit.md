# HBM comparator owner/ACK bridge: gap review

Main `b1397a050`. Read-only. The full table, evidence and work items are in `hbm_owner_ack_gaps.json`.

**Headline.** No HBM-comparator RTL composes owner identity, common ACK, visibility, consumer, reverse and CDC together. The r14 composition does it only in tb_hbm_finite_stage (ROM persistent-KV vehicle), and the installed comparator PC service is count-only with no write-completion ready.

Legend: R = in RTL, R* = RTL only in a bench or unconnected (not in the comparator path), M = Python model only, A = absent.

| class | lease | SRAM acc | common ACK | visible | consume | reverse | tag/gen | backpr. | CDC | wait bnd | starv. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C0 | M | R* | R | M | M | M | M | R | A | A | A |
| SIMD | M | R | R | R | R | M | A | R | A | M | R |
| matrix | M | R | R* | R* | M | M | R | R | A | A | R |
| KV_read | R* | M | M | R* | R* | R* | R* | R | R* | A | A |
| L2 | M | M | A | M | M | M | R | R | A | M | M |
| KV_write | R* | R* | R | R | R* | R* | R | A | R* | A | A |

## Design split
- **Qwen3_8B_HBM**: Installed 128-PC x 6-client service RTL exists (rtl/hdc/hbm/ot_hdc_qwen_hbm_service.sv) but nothing outside tests instantiates it. GU epoch commit is Qwen-only. KV finite DAG: 198,594 nodes with 21 phase costs missing (causal_grants_r1/final_causal/summary.json).
- **DeepSeek_V41_HBM**: There is no shared multi-client PC service RTL for DS. The only joined scope is the directed PC10 rank0 call (1,152 calls, 9,216 shared64 children), with 0 production calls closed and 0 SRAM ACK observations. The GU epoch protocol is not inherited (atomic_source_g0.py:94). Every RTL-present cell for matrix/KV/L2/KV_write is ABSENT for DS until the same gate is instantiated.

## Zero-cost and zero-latency assumptions (forbidden; each must be priced or tied to an existing interval)
- `rtl/hdc/hbm/ot_hdc_qwen_pc_service.sv:27-28,83-87,104 and tools/h3_complete_native_calendar_installed_r2.py:49`: Write completion has no ready; counter decremented on any wr_done for the client (zero-cost always-capture sink, no tag check)
- `rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv:133`: Read credit (credit_we=0) granted with no identity match
- `rtl/gpu/ot_gpu_bulk_copy.sv:40-42,79,137-138`: Bulk-copy response has no ready and no tag validation
- `tools/h4_hbm_kv_validity_fence_model.py:280`: RF_both_copy_write count fixed at 0 (assumed charged in PC5/PC9 producer intervals; reuse unverified)
- `tools/h3_complete_native_calendar_grants_r1.py:98-99,306`: cost_addition=0, C0_V1_I64_provider_RF_mirror_cost_added=0, additional_cost=0: grant ledger adds no time; mirror writes priced only if existing intervals already contain them
- `tools/h3_complete_native_calendar_grants_r1.py:486 with :341,:379`: structural_frontier nodes (Qwen.PC*.retire, fence :ready) take 0 duration; native PC retire carries no reverse/CDC cost
- `tools/h4_hbm_production_owner.py:428`: new_RF_I64_RMW_C0_provider_costs=0
- `tools/h4_hbm_selected_cache_rmw.py:167,184; :43`: incremental_I64_RMW_charge=0, extra_C0_V1_I64_provider_charge=0; merge priced at 1 edge with SS_FF_merge_verified=False
- `tools/h4_c0_v1_owner_lock_addressed.py:154,175`: read_return/write_mirror_ACK stalls default 0
- `tools/h4_hbm_service_context_g0.py:218`: stall_bound=1 per L2/shared word with no source

## Defects found
- `rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv:20`: Default-off branch assigns undeclared 'commit_ready' (implicit net); output commit_r is UNDRIVEN when ENABLE=0. Verilator: IMPLICIT + UNDRIVEN. Violates default-off cleanliness.
- `tools/h4_c0_v1_owner_lock_addressed.py:175-183 vs rtl/gpu/ot_gpu_rf_service.sv:46`: C0/V1 model consumes two independently timed mirror ACKs; RTL produces one combined ACK. Use the h1_combined_ACK form (production_owner.py:136) or the KF combined_ACK form.

## Minimal ordered work items (each default-off, separately testable)
W1. **Default-off hygiene: drive commit_r=0 in the r14 provider off-branch**. Successor file (original is pinned by installed_r2 sha a8516d20) with assign commit_r=0. No behaviour change when ENABLE=1. Gates: `verilator --lint-only -Wall ENABLE=0 and ENABLE=1 (no IMPLICIT/UNDRIVEN)`; `tools/run_hbm_finite_stage_r14.py (tb_hbm_finite_stage.sv)`.
W2. **Exact completion capture in the comparator PC service**. ot_hdc_qwen_pc_service successor with param EXACT_COMPLETION=0: a per-client 16-entry outstanding table {tag32,gen,we}; read return and wr_done must match a live entry of the right direction, else sticky fault; add p_wr_done_rdy (or a 1-entry held capture register per client with backend stall) and c_wr_done_rdy; fault gates grant. Gates: `tests/test_hdc_qwen_hbm_service.py`; `rtl/test/tb_hdc_qwen_pc_service.sv`; `rtl/test/tb_hdc_qwen_hbm_service.sv`; `rtl/test/tb_hdc_qwen_hbm_mixed_service.sv`; `rtl/test/tb_hdc_qwen_kv_shared_service.sv`; `tests/test_h3_complete_native_calendar_installed_r2.py (add an InstalledQwenPC successor that mirrors the new RTL)`.
W3. **Generation on r14 credits and read-credit match**. Provider successor: carry a generation field in wr_word/credit; read credit (credit_we=0) must match a live mapped read owner; KV adapter compares the full MTAGW tag plus generation. Gates: `tools/run_hbm_finite_stage_r14.py`; `rtl/test/tb_hdc_qwen_kv_shared_service.sv`.
W4. **Identity-bearing common RF ACK**. rf_service successor (param ACK_ID=0) registers {owner_tag,generation} at write_go and returns it with ack_valid. Update the C0/V1 model to consume one combined ACK, not two timed mirror ACKs. Gates: `rtl/test/full_sm_service/tb_full_service_exact.sv`; `rtl/test/hbm_rf_visibility/tb_connected_rf_visibility.sv`; `tools/test_h4_c0_v1_owner_lock_addressed.py`; `tests/test_h4_hbm_production_owner.py (h1_combined_ACK)`.
W5. **Installed owner gate replacing external grant bits**. New ot_gpu_hbm_owner_gate (ENABLE=0): one finite lease entry per SM plus one per shared/L2 bank {gen64,seq40,rank,SM,lease,provider_ref}, contenders C0/SIMD/matrix-result/KV/L2. It drives rf_owner_grant/shared_owner_grant and holds the lease through consumer and reverse; the rotating cursor advances only on reverse (the BankArbiter policy). Size it from the 324-bit entry and 12,288-context envelope in installed_services_r2/model.json, narrowed by the emitted DAG. Gates: `rtl/test/tb_h4_hbm_rf_shared_context.sv`; `tests/test_h4_hbm_gateway_constructive.py`; `tests/test_h4_hbm_production_owner.py (OwnerController trace parity)`; `tests/test_h4_hbm_kv_validity_fence_model.py (BankArbiter parity)`.
W6. **Visibility -> consumer -> reverse ports on the RF fence**. Fence successor: add consumer_accept and reverse_grant handshakes after fence_valid, widen the 8-bit epoch to an owner-gate tag, and instantiate it behind the owner gate (still ENABLE=0). Gates: `rtl/test/hbm_rf_visibility/tb_connected_rf_visibility.sv`; `tools/test_hbm_rf_connected_preparation.py`; `tests/test_h3_complete_native_calendar_grants_r1.py`.
W7. **Endpoint trace export into CausalGrantLedger**. The bench emits per-bank acceptance, capture, common ACK, child reverse, fence, consumer and reverse events as origin=endpoint_trace for one PC0 RMW parent and one PC10 shared64 parent; replay them through CausalGrantLedger.observe. Gates: `tests/test_h3_complete_native_calendar_grants_r1.py`; `tests/test_h4_hbm_selected_cache_rmw.py`.
W8. **KV write sector owner in RTL**. SectorTransaction in RTL behind the owner gate: old-sector capture with a full-sector validity receipt, mask merge, write with W2 exact completion, then consumer and reverse. Add a MetadataFence that orders bitmap before record under writer exclusion. Reuse the KV adapter single-outstanding pattern. Gates: `rtl/test/tb_hdc_qwen_kv_shared_service.sv`; `tests/test_h4_hbm_kv_validity_fence_model.py`; `tests/test_h4_hbm_selected_cache_rmw.py`.
W9. **Generic L2 word endpoint plus bank fence**. RTL of BankFence/AtomicConnector: L2_128 read/write with a 16-bit seat tag tied to a full generation in the owner gate, visible, consumer and reverse; GU commit joins the same fence. Gates: `tools/rtl_qwen_gu64_pipeline_gate.py`; `tests/test_h4_hbm_atomic_source_g0.py`; `tests/test_h4_hbm_service_context_g0.py`.
W10. **CDC on HBM-service <-> SM boundaries**. Instantiate the r14 fifo2/clock_bridge on the request, return, write-completion and reverse paths of the comparator, exporting both-domain edge ordinals; lift the H1-only refusal in CausalGrantLedger only for paired receipts. Gates: `tools/run_hbm_finite_stage_r14.py`; `tests/test_h3_complete_native_calendar_installed_r2.py (CausalTransportOwners reverse CDC receipt)`; `tests/test_h3_complete_native_calendar_grants_r1.py`.
W11. **Bounded backend and credit-return terms (elapsed wait)**. From the W2/W10 benches, take a source-pinned backend acceptance gap and credit-return upper bound with a directed worst-case stimulus. Feed them to InstalledQwenPC.fairness and finite_bounds. Replace stalls=0 defaults and stall_bound=1 with these bound terms. Gates: `tests/test_h3_complete_native_calendar_installed_r2.py`; `tests/test_h4_hbm_production_owner.py`; `tests/test_h4_hbm_service_context_g0.py`.
W12. **Starvation freedom under the emitted DAG**. For the r14 allocation priority (tag_owner.sv:27) and write-visibility priority (provider.sv:86-91), either add a default-off bounded-aging counter or prove finite contender exhaustion from the emitted lease/contender DAG (the Qwen KV finite DAG). Replace the priority with round-robin for any contender pair that cannot be proven. Gates: `tools/run_hbm_finite_stage_r14.py`; `tests/test_h3_complete_native_calendar_grants_r1.py (schedule_finite_extension deadlock/credit checks)`.
W13. **Reconcile zero-cost placeholders**. For each zero_cost_flags entry, either attach the existing interval id that already charges it (with receipt) or price it positively; structural_frontier retire gets the native reverse/CDC term. Gates: `tests/test_h4_hbm_kv_validity_fence_model.py`; `tests/test_h3_complete_native_calendar_grants_r1.py`; `tests/test_h4_hbm_selected_cache_rmw.py`.
