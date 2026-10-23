The first ds_l0 source-replay failure is rec2 at stream cycle 264, before rec6.
The four ring outputs fail before rec2's remote landing checks at 318. At318,
all 120 remote words fail, all 40 own-slice-kept words pass, and only ring-B and
gather-landing sticky faults are high. Thus rec6's later failures follow an
already invalid collective transaction and are not a first numerical defect.

Selected source d34578d6f really carries the S8b L12 pricing: hcollgi_SW VM_RT 95
and hb_coll_SW VM_RT 96; functional bind 1284 paths passes. The compiler files
match tools revision f613a2a39 byte-for-byte. coll_images.gather_record applies
VM_RT, but still assumes pin-level global launch and fixed two-edge far-end
ring timing. The generated source contains additional ingress/outer-ring
transport. Wrapper counts are NOT clock-cycle latencies: forwarded lane stages
are half-cycle and landings depend on epoch/K.

One bounded same-binary phase diagnostic preserved all 151 original prefix
drives and the entire 1,250-word VM preload. It ran 450 stream / 337 serial / 365 HBM
edges and 3,616 diagnostic zero-baseline checks, with 1,337 expected mismatches.
It is DIAGNOSTIC/TRUNCATED, never functional acceptance. All 40 own ring flits
match the original 280-bit header+payload exactly at 48 stream edges later than
scheduled. The old pre-l12 zero-payload problem is fixed in this source.
A late B-CCW terminal flit's exact payload identity independently gives 20 extra
transport edges relative to the component pin model. Reference forwarded-clock
samples are included at stream/serial sampling edges; these are visible rf0024
boundary clocks, not direct issuer clocks or physical insertion measurements.

The existing Graph.lane_latency helper, evaluated on this exact contract's K/N
and generated source paths, gives launch 48, calendar 24, A-CW 6, A-CCW 18, B-CW 4,
B-CCW 20 edges. NO_E/K placeholder warnings are preserved in transport_model.json.
These are source-functional timing values, never physical-clock qualification.

The isolated rec2 candidate retains the 151 original drives and 287 original
checks. Its four far-end schedules shift by 42 / 30 / 44 / 28 edges; ring/VM/fault
checks shift 48, while the configured check stays at 94. All retained values,
masks, six fault guards and the full preload are unchanged. Last check 366;
proposed run 450. One causal negative omits only B-CCW's 20-edge ingress term,
changing 33 drive-event times; its expected checks and preload remain identical.
The builder reads the selected profile and measured identity rather than
hardcoding 48 for other revisions. Both candidates were prepared for coordinator review. After review, the
coordinator authorized one run of each at 10:00; both are now running, with
results pending in their separate validation directories. Any residual write-side or protocol
failure remains actionable; none is waived by these proposed times.

The first phase launcher accidentally used the generic wrapper's rand-reset2;
the normal replay driver actually uses rand-reset0. It aborted at time 0 on a
TKM assertion before replay events and is preserved as a launcher failure.
The corrected phase run used the actual driver's flag 0 and the same binary.
No normal replay was killed, restarted, modified or duplicated. No RTL/build,
main publication, physical closure or full-layer/token qualification is claimed.
