# PC private async reset conditioner — source proof only

This packet audits the actual retained-source PC and PC_H mappings supplied by
HOST6. It does not change canonical gate helpers, waive plain BRP refusal, add
hardware, or qualify a physical view.

Both selected source bytes and all model/Liberty identities are pinned in
`pc_async_source_graph_proof.json` and `manifest.json`. Exact source originals,
selected primitive sources and re-synthesized mappings are retained compressed
in `packet_inputs`. The original mapped source hash is also checked against the
primitive-copy construction record. Both selected tops have no parameters,
defines or explicit physical initialization.

For every one of four real banks (rst_n/ck and hrst_n/hck in each top), the
actual source graph proves:

- The raw reset reaches exactly nine `DFFASRHQNx1_ASAP7_75t_R` RESETN pins,
  with polarity zero. SETN is a Liberty-proven constant one on every stage.
- Exactly one first stage has D=1 and the literal destination clock. Its QN
  has exactly eight consumers: the final-stage D pins, each through one
  inversion. There is no first-stage export or other consumer.
- All eight final stages use the same destination clock. Every terminal
  consumer is enumerated by source cell, pin, polarity and Liberty function;
  no final Q is exported. Maximum final terminal load is 13 in the core bank
  and 17 in the HBM bank. The entire actual native mapping has max32 loads.
- Final consumers are ASR RESETN pins, ordinary HQN D release observers, or
  specifically enumerated AND3/NOR2 pins. The latter clamp their output to
  zero during reset for **all** values of their other inputs, using actual
  Liberty functions. No general extra-consumer or name-alias rule is used.
- Sixteen actual-graph mutations per top (eight mechanisms per reset bank)
  are refused: raw polarity, raw assertion value, first D, clock, QN polarity,
  stage bypass, an extra consumer and a missing stage. Total: 32 refusals.

The actual SS/TT/FF sequential Liberty signatures agree: QN state has
`clocked_on=CLK`, `next_state=!D`, `clear=!SETN`, `preset=!RESETN`, both-active
priority L/L, and QN output function IQN. The canonical ASR and DFF model bytes
are the repository's committed sequential coupon. They are not inferred from
a cell-name pattern or an old Liberty-import approximation.

`pc_async_coupon_proof.json` records the canonical nine-ASR theorem for that
exact source-audited shape. At both stopped clock levels, assertion and
reassertion force logical release low without a clock edge. Release remains
low with no edge and after the first destination rising edge; all eight final
logical releases become high exactly on the second destination rising edge.
Both baselines PASS. Six real coupon-source defects at both phases produce
twelve SAT failure witnesses. All `.v`, `.ys`, logs and baseline pre/post JSON
are retained. The proof uses direct `clk2fflogic`, no `async2sync`, no
`opt_merge`, no unknown-cell waiver, and no memory abstraction. All nine
physical state samples remain distinct and initially unconstrained. Fixed
previous-data/reset/clock history auxiliaries are separate from physical state.

The source contains existing post-release observer edges. In **each** selected
top, 25 plain-D observers sample on ck and 128 sample on hck, polarity zero.
They capture the final release one further destination edge later: direct
observers mature at edge three after raw release. Those source edges must
remain in the parent boot/calendar price; this packet does not mask or remove
them.

Fanout scope is explicit. Each distinct raw reset input has nine local loads.
The two distinct reset inputs in one top total eighteen loads; externally tying
them gives eighteen on that parent root. Tying all four reset inputs across
both selected tops gives thirty-six and therefore requires parent distribution.
The actual die/parent binding must count its real aggregate; this standalone
proof establishes no parent clock, reach or fanout claim.

Reproduction runs on the fleet in an isolated directory. Decompress the inputs,
copy the two canonical model files and parser snapshot, and use the exact
ORFS image ID recorded in `orfs_image_id.txt` to retrieve the five RVT TT
Liberty files and SS/TT/FF sequential libraries. Their hashes are in the graph
record. Run `tools/qwen_kv_die/pc_async_reset_source_proof.py`, then
`tools/qwen_kv_die/pc_async_reset_coupon.py`, from that directory. Both scripts
are read-only with respect to the selected source and emit separate proof files.

Canonical runtime admission of this narrow async-conditioner class remains a
separate ROOT review. The plain two-D-edge BRP correctly refuses these ASR banks.
