Current native source drift is limited to transparent prefix module renames and
one unobservable error bit. The recipe uses source80e52b927; current selected
r18h5 bundle files are pinned at e5b2ac1fc8d. Parent binder independently checked
the exact cut: one ring AG1/SPLIT_CLOCKS1, one clock tied across its local clocks.
The current pring_static body matches recipe source. Its add_lane instantiates
fp32_add_lat LAT7/DRST0 with err unconnected. The changed s2_err[1] cone feeds
only err, never y or valid_out. Prefix bodies match after module renames.

prepare.py retains both exact source closures and separates their module names.
The bench compares every y and valid bit from edge1 with strict four-state
inequality, no masking or valid qualification, for2201edges including POR,
repeated reset and X/Z inputs. PASS; wrong-output-bit mutant caught atedge7.
This is a scoped source lockstep receipt plus source-cone analysis, not a claim
of whole-ring formal equivalence. Existing whole-cut native/gate LEC is separate.

initial_neutral_xor_FAIL.log is a diagnosed harness failure: XOR-zero turned a
native Z into X. The corrected no-mutant comparison directly preserves Z.
