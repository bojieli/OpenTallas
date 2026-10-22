# Landing cost on the corrected six-position pipeline

This composes the measured end-slice landing cost with the accepted8020b90f3 causal pipeline. The default remains zero. The zero-cost AR and MTP calendar bodies are identical to8020b90f3; only the checker source hash changes. All six calendars pass same-user collision checks and both causal negatives fault.

| Added edges per crossing | AR per user | AR at50users | MTP per user | MTP at6users |
|---|---:|---:|---:|---:|
|0|952.8|47,642|2963.4|17,780|
|6|950.6|47,529|2957.6|17,745|
|7 (IN_PIPE included)|950.2|47,510|2956.6|17,740|

Rates are model tokens/s. At+7, the packing solver happens to admit52 AR users (49,411 aggregate), compared with50 for the baseline/+6. The comparison above holds population at50; taking a subset of an already non-overlapping schedule cannot introduce a collision. No extra release-user credit or new admission campaign is claimed.

The six model computations ran in the inherited unpinned fleet job, gold1 unit424115-1792638581, exit0. No computation was repeated to collect this packet. The physical landing bench and exact selected source/edge receipts remain separate. Full pipeline programme emission, current receiver lifecycle and actual die binding must finish before an RTL-qualified rate claim.
