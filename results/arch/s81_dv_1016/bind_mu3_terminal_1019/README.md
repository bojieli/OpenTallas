# Exact final MU3 strict bind terminal

The final `ceaed19c4` die/table replay against checker `58fc3dbc1` is **FAIL**: 1,182 unread bits and 28 open master-port entries. The full terminal report and log are retained; wrapper return zero and the older 41-master/9,009-instance binder PASS do not qualify this source. Fingerprints are in `terminal.json`. This differs from the preserved physical pilot `3158fce1e`, whose report has 39 open entries.

The 1,182 unread bits comprise 1,110 functional SEND header/upper-payload bits and 72 literal zeros across `u_s_3S/4S.bo`. The classification does not apply a pad or spare exception. Current compiler source has no selected QF SEND programme or proven pair-count bound.

The 28 open entries are frame xo/xok (two masters), SM mutable-row write outputs (two masters, 16 actual instances), ten PHY outputs, and four LEP tf outputs. Counts are unique master-port entries, not the number of instantiated pins. Neither seq_host t_mf nor block_fault remains open in this final source. All other summary error counters are zero; unresolved children zero.

All four original physical chains remain preserved. Functional regression success cannot authorize automatic GENmu4 binding, physical/native adoption, or full single-user/multi-user token qualification. QF producer, SM target/storage, parent placement/reach, routed electrical and native TT/FF closure remain open.
