# Exact unread-review manifest API proposal

Default die_port_bind behavior and report remain unchanged. No manifest is admitted automatically. This is a Gate-Rule change requiring ROOT review, main regression, and safe sync before production use.

The source-intent review approves instance/master/output-port/net/width/inclusive-range identities. The producer writes a proposal only when die and contract hashes equal the review and selected RTL bytes equal the reviewed historical git revision. It retains every reviewed source pin and adds the complete selected child-module closure. The proposal pins actual instance parameters, top, compiler defines, model declarations, straps, and pads. Its SHA256 must be reviewed externally and passed explicitly; the checker never infers approval from a local file or updates a review hash.

```
python tools/die_port_bind.py DIE --top TOP [original source/define/strap/pad arguments] \
  --unread-review REVIEW.json --unread-contract CONTRACT.json \
  --unread-proposal-out PROPOSAL.json
# ROOT review of immutable proposal digest is a separate step.
python tools/die_port_bind.py DIE --top TOP [identical original arguments] \
  --unread-review REVIEW.json --unread-contract CONTRACT.json \
  --unread-manifest PROPOSAL.json --unread-manifest-sha256 ROOT_REVIEWED_SHA
```

Any source, die, contract, parameters, selected module path, build options, review, or range drift refuses and requires renewed semantic review. Overlapping, wildcard, malformed/out-of-range and duplicate-net permissions refuse. A reviewed bit must still have exactly one producer and no consumer: occupied fault/payload permission is refused. Manifest permissions affect only unread-bit accounting; output-open, undriven, multiple-driver, constants, width and child-closure checks remain strict. Disjoint reviewed ranges leave other bits failing; no master-wide spare union exists.

The current HBM source-intent review approves exactly 65066 bits across 309 entries. Its remaining 5254 bits remain FAIL. No source adoption, die qualification, or change to those held classes is requested by this tool implementation.

Validation: `python -m unittest discover -s tools/tests -p test_die_bind_unread_manifest.py -v`: 11 tests pass, exercising real producer/consumer RTL through both CLI phases, strict default failure, scoped success, disjoint residual failure, overlap/range rejection, occupied fault/payload refusal, missing explicit digest, altered permission/pins, consumer removal, and source/deep-consumer/die/contract/parameter/define drift. The tests build immutable temporary git source revisions; no synthesis is necessary.

Original-source diagnostic proposal: `original_d517a76ad/manifest_proposal.json`, SHA256 `2beccb8e65b7a62733fd9265ce4a0397192de0315202ba1a912c257f8ec5ddf2`. Exact reviewed die/contract/source revision d517a76ad, 555 selected modules with full child source closure, original OT_SMH_FC_HIER define,45 straps, original padding and PHY/PLL model declarations. Result is FAIL with exactly5254 unread bits and zero other top-level structural errors; child closure481modules/unresolved0. This is diagnostic evidence and an immutable proposal awaiting separate ROOT digest admission, not a production approval. Post-review source changes must refuse; the proposal must not be restamped to newer RTL automatically.

ROOT independently admitted only the exact original digest in `original_d517a76ad/root_exact_admission.json`; renewed source/die/contract/options require renewed review. Canonical follow-up adds two early argument-refusal tests, preserving KV source/parameter/selected-RTL consumption checks. Independent full CLI replay reproduces65066 reviewed bits and5254 strict residual failures; default report bytes exactly match59835e962 with70320 unread bits. No die or changed GEN2e admission.
