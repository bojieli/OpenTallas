# Native VM static primitives, 2026-10-14

This is component evidence for new actual RTL and actual SRAM functional models. It is not full-layer, full-token, physical timing, or production throughput qualification. Production has no ready, credit, retry, demand arbitration or dynamic schedule extension.

The 32-bank slice uses independent real read and write ports of `ot_sram_1r1w_512x128_m4_r2c2`. Four physical slices preserve the existing 16384x512 capacity. Bank = row[4:0] XOR {row[7:5],2'b00}; bank-local address = row[13:5]. The offline compiler must supply at most one read and one write per bank per edge, with request slot index 8*row[1:0]+lane_index. Collision detection faults without postponing requests. Read-before-write semantics apply to the same physical row.

With all clocks ideal and coincident, packet sample E0, scatter output E1, bank input E2, actual SRAM read/write E3, registered read E4. Actual physical relay and phi-R timing may add compiler-visible stages; these are not assumed zero. Serial0.9GHz clients still require explicit fixed3:4 transport into proposed stream1.2GHz bank service. No such transport is qualified here.

`slice32/run_base.log`: 32768 reads and 49152 writes, bad0, including 1024 consecutive cycles of 32 reads AND 32 masked writes. `run_mutant.log`: real macro mask forced full, bad30447, FAIL observed. Gate unit oth-ubuntu-2771145-1792032707 on ot-epyc4, ot-run16GB/8threads.

`rscatter`: 2545 exhaustive dense16/dense32/QR32 legal address batches, bad0; tag mutant bad2545 FAIL. Gate unit oth-ubuntu-2771138-1792032707,6GB/4threads.

`reset_replay`: same final synchronous-reset-release source used in scatter, bank and return. Scatter base2545 checks bad0; hash2353 and data2545 mismatch mutants FAIL. Bank20000 reads/20512 writes bad0; physical mask mutant18353 mismatches FAIL. Return64 groups bad0; explicit missing-row release faults on its compiled edge; silent-release mutant FAIL. These component tests do not establish simultaneous SU/HC/PQ return capacity. One return leaf emits one16row group per edge and has two parity buffers; complete compiler reservations and any additional return leaf copies remain required.

New native bank leaves contain no queue. Historical `../s81_vm_commit_1014/service_trace.csv` measures the old queued serial ctrl path only; updated bank_enqueue events observe actual QD4 admission, not speculative issue. This trace is diagnostic and does not set timing for new leaves.

Hash native field/hierarchy evidence is archived in `../s81_vm_hash_1014`. Existing functional field identity is preserved because the same bijection applies before every native memory ingress and logical counters remain in logical address space.

`group32`: real request scatter ->32real1R1W SRAM macro leaves -> actual return buffer,1024 consecutive16row groups,16384reads/49152writes,bad0. Compiler fixed release E6 for request E0; bank response E4 is captured into return storage E5. No runtime check postpones a release. Physicalmaskmutant bad16209 FAIL; one-edge-early release mutant bad2053 and zero returned groups FAIL. Unit oth-ubuntu-3288840-1792032929,20GB/12threads. This proves one grouped response path under ideal common clock; it does not prove serial3:4 crossings, physical timing, or concurrent client return capacity.

`native512`: actual full-capacity512-bit parent with4physical slices,128actual SRAM macro instances and4actual return leaves. Distinct per-word stimulus verifies all16FP32-sized words, per-slice real macro commit address/tag/mask and exact grouped read visibility. 16384logical reads/49152logical writes,1024groups,bad0. Slice-order mutant bad1017 FAIL. Unit oth-ubuntu-3690347-1792033087,24GB/8threads. The parent exposes all four slices' valid/group and128physical commit observations independently. It does not hide physical slice skew or infer all-slice completion. Clock pins remain separate, idealcoincident test clocks only. `tools/s81_vm/static_native_ideal_template.json` records exact signal definitions and compiler offsets, with explicit physical/nativeproduction qualification false and illustrative external-stimulus allocation only.
