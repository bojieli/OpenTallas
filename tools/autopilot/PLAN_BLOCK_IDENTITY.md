# Optional pin-payload block identity

KIT-WAVE keeps its existing raw dictionary hashes by default. No config or state
migration accompanies this tool change.

An explicitly enabled die may use `block_identity: "pins_payload_v1"`. The remote
probe resolves each `pins_file` relative to that plan, validates the JSON payload,
and hashes its exact bytes. Only that path field is substituted in the hash
input. Geometry, clock/reset contracts, parameters, budgets, list order and all
other fields remain significant. A missing or malformed payload makes the probe
fail closed. Pin-free types keep the original hash. Semantic probes are fresh on
each call, since a pin payload can change without the plan path changing.

Global hard-core module keys include every distinct instance profile in this
mode. The legacy probe hashed only the first profile. Existing legacy records
covering multiple distinct profiles cannot be reused: the tool holds them for
an explicit owner decision instead of assuming the first instance proves all.

To prepare a narrowly scoped legacy reuse receipt, run the following where both
plans and their payloads resolve, with a read-only copy of the current state:

```sh
python3 tools/autopilot/plan_block_identity.py \
  --baseline-plan /preserved/old/plan.json --plan /portable/plan.json \
  --state /copied/kit_wave_state.json --die qwen_kvsys \
  --item exact_type_name > proposed_identity_config.json
```

This prints a proposal and never writes state or config. Repeat `--item` only
for explicitly approved items. The proposal names the exact baseline and carries
`identity_reuse_receipts`. Before activation, review it with the owner and retain
it. Reuse requires the stored record's full old raw hash, exact normalized old/new
profiles, exact resolved payload receipts, and the original record fingerprint.
Only settled wave PASS/FAIL records qualify. Existing live/enqueued jobs remain
held for migration; their jobs continue under the original configuration.

After that explicit review, the returned fields can be added to the die config.
At runtime the probe re-resolves payloads and checks the receipt against actual
state. Proven reuse keeps the original state key and record, including FAIL,
reason, attempts and stage evidence. It creates no alias, duplicate stage row or
retry. Unapproved unchanged legacy profiles are held. Real profile changes get a
new semantic hash; the configured item allowlist and normal gates still apply.
No retries or wave launch are authorized by generating a receipt. Semantic mode
also holds automatic pending INFRA retries, which run before profile selection;
an owner must review and explicitly release these after the current identity is
proven. The default raw mode keeps its existing once-only INFRA retry.

`results/plan_block_identity_1030/kv_portable_coupon.json` records the read-only
controls against the actual old KV16980115, portable E0 and AHUB plans. Their real
E0 and AHUB changes remain distinct. The coupon does not approve any migration.
