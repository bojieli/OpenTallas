# KVN owner-bank native diagnostic

Selected source19e0e1d63 remains functionally qualified only; no physical gate/layout has been launched. Generic scalar Yosys0.68 synthesis before ABC/buffers finds1596cells, max63loads and13drivers above32, including owner muxes/write enables and reset_last33. This is a diagnostic native-driver lower bound, not an ASAP7 gate qualification.

The preserved rejected_shards/source.sv trial adds real per-shard selector/write-control registers and an extra owner write edge with a pending-write replay bypass. All four good/wrong-user/stale/boot functional verdicts pass. Generic optimization nevertheless merges identical shard registers:1725cells, max63loads/13drivers above32. The trial is rejected, absent from selected RTL, and has no physical/latency adoption claim. Merely marking copies keep/dont_touch did not preserve separate drivers. A further repair must establish genuine retained physical partitions and measure the full native logical driver fanout.

Sources are SHA-pinned in each census. Runs ep5unit3158137-1792604717 baseline and3278584-1792604836 rejected trial,8GB admitted each. Original command bootstrap failure used a missing yosys/bin path; local kvn_census.log retains that error, corrected to installed yosys-0.68 path before successful census.
