The native writer programme is an opt-in component candidate. It provides the
four expectation inputs of `qkd_kv_static_writer_native` from six ascending
boot writes and captured transaction roots. Runtime slots depend on an elapsed
cycle counter, four fixed cycle roots and the configured stage. They do not
depend on actual payload, word-valid, readiness, credit or completion.

Boot addresses 0..3 contain the four cycle32 values (upper32 zero), address4
contains `{reserved26,stage6,stop32}`, and address5 contains `514b565052473031`.
Sealing validates monotonic slots, first slot >=4, at least three drain cycles,
and stage1..36. Reset is required to replace the sealed image. A malformed boot
or start faults and cannot open a transaction. The parent supplies an already
accepted epoch16/token18/position13/generation2; this leaf does not allocate an
epoch or implement the parent's epoch-wrap/drain protocol.

After an accepted start, cycle0 is the interval before the next receiver
sampling edge. The four compiled outputs connect directly to the writer's
`compiled_word_slot`, `compiled_word_index`, `compiled_identity` and
`compiled_generation`. TAG59 is `{epoch16,stage6,token18,position13,segment6=0}`.
`kvn_word_slot` duplicates that slot for a receiver at this same boundary; it is
not a schedule for an upstream formatter or a D2D launch. Transport calendars
must account for their own implemented clock crossings and registered hops.
The independent physical descriptor appears after the same two capture edges
as the writer: expected_valid4, expected_pc20, expected_stack2,
expected_identity59, expected_generation2 and expected_address29. The component
bench checks it against the actual physical writer, including actual raw data
and an inverse physical-address oracle. No hierarchical signal access is used.

`tools/qwen_static_kv/native_programme.py` validates the actual TP8 source plan,
source pins, complete programme hash, exact descriptor bytes/segment bases, and
sole native PC11 capability. A production invocation additionally requires a
source-bound measured writer receipt and the existing full segment physical
profile. Missing receipts, unaligned word arrivals, unimplemented clock
conversion or expectation relay, and controller/front/ring scope are refused.
Component-test mode is explicitly marked noninstallable. No production image
or performance credit is established by its component timeline.

Reproduce the current source candidate from the released local snapshot with:

```sh
QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 QWEN_O4_AR_WORDS=256 \
python tools/qwen_tp8_fulltoken_plan.py --snapshot /path/to/b968826d9c46dd6066d109eabc6255188de91218 --out /fresh/source
python tools/qwen_static_kv/run_native_programme_gate.py --source-dir /fresh/source --out /fresh/gate
```

The source and gate evidence are in
`results/rtl/qwen_native_kv_programme_1103`. Regeneration produces programme SHA
`f7a290112c2858f5b8dd169ade5c7c9afbaa372cc7f0f8e29a387c064f54bd71`;
the historical installed candidate remains
`cc5bc8fc17d4068ac9a49e8bf79f34e74350d56d114dd7fe5cde433d2ac82796`.
Only PC16 chase_n (64→509) and PC20 chase_n (24→192) differ under the current
decoder. Native PC11 and K/V source PCs3/8/10 are byte-identical; descriptors are
byte-identical. The historical source plan has stale current ISA source pins,
so the compiler refuses it rather than silently updating the installed identity.
The whole-stage timing consequences of the regenerated candidate remain open.

The unified model's `qwen_native_kv_programme_candidate_model` counts 384 logical
state bits per writer, 48 bytes of exceptional boot traffic, 64 expectation
bits/cycle plus a duplicated KVN slot, and 116 independent descriptor bits/cycle.
The replica count is explicit. Area, slot fit, routing capacity and SS/FF timing
remain unmeasured. No added writer capture stage is introduced; no token-rate
improvement or full-root integration is claimed. Controller command/refresh and
reservation outputs, HBM `blk_go`, ring expected-return slots and their physical
ages remain separate required work.
