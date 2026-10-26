Source acknowledgement only for selected G9 KV512

The helper acknowledges `u_s_3N` only when the top is exactly `ot_s81sl_slice_kv512`, top parameters are explicitly `{}`, and wrapper/base/bank/leaf source hashes match selected source `8a495768f02316a7a8ad2e2bafef2f4d3741b741`. The source manifest is pinned by full commit and SHA256 in `check.json`. Default-off `ot_s81sl_slice`, names merely containing `kv`, parameter overrides, changed source and missing files fail closed.

The fixed child is `u_slice` with HB0, DL4, DR6, DX6, VQ_XMEM2, KV_ENABLE1 and VS_MUT0. The enabled bank path is `u_s_3N.u_slice.lf[0].u_lf.g_kv.u_kv`. The source owner confirmed the exact 18-port passthrough: clk/rst_n and forwarded clock interfaces are unchanged; the wrapper adds zero state, logic, clocks, resets or edges. This records a source contract, without clock/runtime or physical qualification.

From a source root with the four exact relative paths named by the helper:

```sh
python3 tools/s81_dv/layer_prog/kv_source_ack.py \
  --source-root SOURCE_ROOT --instance u_s_3N \
  --master ot_s81sl_slice_kv512 --params-json '{}'
```

Required pure contract check, using immutable git source snapshots:

```sh
python3 tools/s81_dv/layer_prog/check_kv_source_ack.py --out NEW_CHECK_JSON
```

The committed check passed source acknowledgement and necessary rejection cases. No compiler, elaboration, simulation, programme, calendar, RTL/master or physical changes were made. Existing `lower_kv.py` and the prior 50 PARTIAL / 5 GAP receipt remain unchanged. Producer CAP/gather, operand/parameter transport, source identity, row lifetimes, fixed programme/commit/retirement dates and distinct-master physical views remain held. The physical master is UNBOUND. This helper is intentionally separate from lowering and cannot authorize a dispatch.

Base of this narrow branch: main `c2b6b4e72ad9a453c449f22332c6765df55702e6`. Only the helper, its required pure check and this source-acknowledgement receipt are added; no old functional/compiler branch ancestry is imported.
