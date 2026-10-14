# IDX measured endpoints and candidate-transfer diagnosis, 2026-10-13

All production unit cycle numbers use the same e2e record endpoint: retire minus dispatch. They include decode, operand reads, native selector/scorer work, result packing/writes and record retirement. They are not just the adapter-front measurement. Immutable prices remain L24 1080, L20 1212, L2 658.9, TOPK 283.008. Token weighting is four L24 + one L20 + three L2.

| Record | Current exact die dispatch→retire | Checked words | Immutable price | Ratio |
|---|---:|---:|---:|---:|
| INDEX L24 | 1140 | 1024 | 1080 | 1.056 |
| INDEX L20 | 1872 | 3756 | 1212 | 1.545 |
| INDEX L2 | 850 | 1024 | 658.9 | 1.290 |
| TOPK route.top6, each layer | 187 | 6 | 283.008 | 0.661 |

INDEX token cycles 8982 / 7513.6 = 1.195. This is a unit ratio, not a measured design tok/s loss. No ledger row is authorized by this document. accepted_cost.py documents the separate composition calculation; its old 0.282% loss was computed for the previous 9144-cycle measurement, so it is not current evidence.

The old L20 result had 2717 MISMATCHES OUT OF 3756 checked words, not 2717 checked words. The same 1366 D (id,value) pairs had the old descending-score order in the staged golden. Current architectural golden requires ascending block ID. Correcting only that ordering in vmw.bin and final VM produced 3756/3756 exact and final mismatch0 on the previous binary and now on current BASE. This is not a threshold or count change. A proper exporter re-export remains owed.

The die bench has real IDX records (two per layer), real native selector/scorers/service stream and modeled VM/DRAM. Other units are replay stubs. Its layer completion endpoints (L24 doorbell20537, L20 21194, L2 20822 cycles) are measured composition endpoints with those stubs; they do not prove all-real full-die tok/s. Current binary has no +IDXT monitor code: passing +IDXT did not produce phase traces. Older selector-tail figures from another source are diagnostic history, not current measured phase decomposition.

The current source establishes one concrete transfer bound: the CLOSED PK leaf has four D-link credits; its credit returns after WP pin landing, D FIFO entry, packer dequeue, registered d_cr, PK dcr_q and dcred. The previous six-edge loop limits sustained candidate rate to about 4/6 beat/cycle. WP alone can decouple that link: sixteen D FIFO slots, registered pin-landing acknowledgement, deferred credits above nine queued beats (six reserved slots cover four outstanding credits plus landing stages). All five CLOSED leaves remain unchanged.

Measured saturated candidate test (683 two-candidate beats, same equivalence harness): shape2 RT8 total1025→853, RT16 total1033→861, drain30→22. Front148/156 unchanged; exact3x100 frames pass, MUT1/2/3 fail. Initial acknowledgement from the FIFO register added an edge and did not improve total1025; the final direct pin-landing acknowledgement is the measured 172-cycle improvement. The current production BASE+MUT2 builds for that RTL are pending; do not extrapolate the synthetic gain into a qualified production number.

Production build failures were cgroup OOM at100GiB on every prior MUT2 attempt (journal saved). Prior BASE reached140GiB and completed. New builds request180GiB each, derived from that measured peak, with sourcea3896fbe1 in a separate directory. No original live simulation was duplicated.
