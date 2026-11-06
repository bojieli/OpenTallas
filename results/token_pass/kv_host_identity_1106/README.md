# KV HOST service identity

`tb_kvslice_native.sv`, `main_kvfn3.cpp`, and `main_kvfn4.cpp` now default the HOST service epoch to the actual programme `+EPOCH`, which the boot runner reads from the image's `epoch.txt`. An explicit `+HOST_TOKEN_SEPOCH` remains available for deliberate controls. Missing or overflowing identities fail before sending a token.

The completed frozen c47 debug run used programme/service epoch `0b0b` and default HOST service epoch `0000`. That expectation cannot accept the advertised service. Token epoch `0004` is a separate job identity and is legal for position8191; substituting `0b0b` into that field would violate the required position low bits. Token generation remains a separate two-bit job field. The change validates both widths without conflating these identities.

The extracted actual policy functions from both C++ drivers and the SV bench pass15 cases each: the observed readiness mismatch, programme-derived service identity, explicit stale control, valid independent token epochs, invalid position encoding, and out-of-range token/generation/epoch fields. Replay:

```
python3 tools/qwen_layerbench/kv_dieslice/check_identity.py --sources tools/qwen_layerbench/kv_dieslice --out NEW_DIRECTORY
```

This fixes a driver/calendar mismatch. It does not fix the independent missing near programme witness: the completed c47 NOWAIT run still had no service-ready indication, KVN context IDs/generation zero, near abort0x80 at44312 and far abort0x04. Earlier ready-wait control also failed without sending HOST START. No new full-die simulation or hardware qualification is claimed here.

Evidence: epyc6 `/srv/opentallas-scratch2/claude/dkv80dbg/kvdbg3/{result.txt,run/sim.log}`; component result epyc5 `/srv/opentallas-scratch2/claude/codex-kv-identity-1106/proof/`.
