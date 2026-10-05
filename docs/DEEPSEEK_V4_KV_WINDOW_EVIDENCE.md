# DeepSeek V4 circular KV-window reference evidence

**Evidence class:** source-pinned deterministic state-transition reference  
**Qualified graph kind:** `KV_WINDOW_WRITE`  
**Reference profiles:**
`opentallas.deepseek_v4_kv_window_write.v2`,
`opentallas.deepseek_v4_kv_window_retire.v1`, and
`opentallas.deepseek_v4_kv_window_valid_view.v1`

## Scope

The qualified reference freezes the circular window-cache assignments used by
the pinned DeepSeek V4 Flash attention implementations and adds the causal
metadata that the accelerator service boundary needs to keep independent
sessions from observing stale capacity. It covers:

- fresh prefill for sequences shorter than, equal to, or longer than the
  128-row window;
- one-row decode at exact absolute cursor position;
- circular wraparound and chronological valid-view reconstruction;
- fixed-capacity active-lane prefixes and trailing-suffix retirement;
- canonical session identities, tombstones, absolute cursors, and monotonic
  uint64 versions;
- complete capacity-wide version authority for writes, retirement, and views;
- deep immutability, poison-before-transition behavior, and exact logical
  payload/metadata counters.

It does not cover KV projection, RMSNorm, RoPE, FP8 QDQ, sparse-attention
composition, combined `ATTENTION_KV_VIEW`, compiler/service lowering, atomic
compare-and-swap across requests, RTL, physical memory placement, cycles,
bandwidth, PPA, checkpoint-derived activation values, or complete-model output.

## Pinned authority

| Artifact | Pinned identity or field | Use |
|---|---|---|
| Repository | `deepseek-ai/DeepSeek-V4-Flash-0731` | Official source owner |
| Revision | `7872f01b1d1fe23eabc4c98b48bffcef5a386062` | Immutable release |
| `inference/model.py` | SHA-256 `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` | Prefill/decode circular assignments |
| `config.json` | SHA-256 `6c8f3d2d3b48707541b88f32f22ef3f0f8a6b57d8523281e2b8d3cdb0ae9a023` | Architectural maximum position `1,048,576` |
| `inference/config.json` | SHA-256 `c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71` | Standalone source default `4,096` |
| `inference/generate.py` | SHA-256 `775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812` | Interactive override `65,536` |

The position values above have different meanings. The top-level metadata is
the reference's address ceiling. It is not evidence that the standalone
program allocates or executes a 1M-token request.

## Payload rule

The official logical cache is `[B,128,512]`. The 512-value latent KV row is
shared by all 64 query heads. The reference exposes a shape `[B,W,H,V]`, where
the official profile is `H=1,V=512`; bounded smaller products are admitted only
for structural tests.

For prefill at `start_pos == 0`, every row is committed when `S <= W`. When
`S > W`, only the final `W` rows remain and absolute row `p` occupies slot
`p mod W`, matching the official split-assignment order. Decode requires one
row and writes slot `start_pos mod W`. For an active lane at next position `N`,
the only visible chronological range is:

```text
[max(0, N - W), N)
```

Every BF16 value is validated as finite before address derivation or successor
construction. A failed call returns no partially updated state.

## Session and epoch rule

Each capacity lane binds the tuple:

```text
{session_id, active, next_position, version}
```

Active lanes form a contiguous prefix and share one cursor. A never-used lane
has no identity, zero cursor/version, and positive-zero payload. A retired lane
retains its identity and payload as a tombstone, resets its cursor, and advances
its version. Retirement accepts only an exact nonempty trailing suffix.

All public operations require the exact complete version vector. Decode also
requires every active identity and the expected cursor. A deliberate prefill
may replace an authorized tombstone and reuse a prior session ID, but stale
authority, cross-session decode, skipped or replayed position, duplicate
identity, non-prefix activity, and version overflow poison.

The pure reference does not make the check-and-successor operation atomic
between independently scheduled service requests. A later session controller
must provide that synchronization and bind committed state hashes to requests.

## Counter and storage boundary

Write, retirement, and view records reconcile source/state rows and BF16 bytes,
preserved capacity, circular modulo evaluations, visible rows before and after
invalidation, identities, active flags, cursors, versions, and immutable commit
count. Those counters describe semantic work. They do not claim HBM or SRAM
transactions, bursts, banks, cache hits, flits, cycles, latency, achieved
bandwidth, energy, area, routing, or PPA.

Window KV and all session metadata are mutable. They are therefore outside the
mask-ROM weight capacity by construction.

## Verification

The committed suite covers the official default shape, reduced exhaustive
profiles, prefill boundaries, circular wraparound, multi-step decode, active
lane shrink, explicit retirement, tombstone replacement, session reuse,
maximum position, stale versions, wrong identities/cursors, uint64 overflow,
nonfinite and malformed payloads, deep alias resistance, forged public result
records, exact counter equations, and randomized physical-slot versus causal-
history oracles.

Reproduce the reference gate with:

```bash
pytest -q tests/runtime/test_deepseek_v4_kv_window.py
pytest -q tests/compiler/test_deepseek_v4_graph.py
```

The source/cache identity test reads the locally cached pinned release when it
is present and otherwise skips only that redundant local-file check; all target
transition and rejection tests remain self-contained.

This evidence changes the semantic ledger from 40 to 41 qualified operator
kinds. It does not close `COMP-01`, M4, M6, M8, target-node feasibility, or any
performance claim.
