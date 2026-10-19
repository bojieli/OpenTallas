# Direct calendar guard edge and 4-state component verification

Final run **r6**: baseline **267 checks PASS**, all **10 causal verification-copy mutants fail named assertions with nonzero exit status**. Private calendar source SHA256 `351145254ed523a0a062dd56151451b4d0184ebc5fae2ebd80f9608e9d161faf` stayed unchanged. This is functional component evidence only; no synthesis, SRAM initialization guarantee, native timing, physical adoption, or whole-die claim.

The bench uploads actual 32-entry storage and the segment base through the original `cfg_we && !running` acceptance predicates. It checks each of 32 missing entries and the missing base independently. It rejects a start on last write W and W+1, then accepts healthy W+2 with unchanged expected `cur`, `cnt`, `pc0` and running state, and checks the event on the exact seven-count edge. Unreset table/base registers are X before reset; no memory initialization is added. A configuration word accepted at the first post-reset edge earns a receipt immediately, without a quiet window or readiness mask. Real local reset and reload invalidate receipts. An early rejected request remains poisoned after later uploads and reload, without queued retry.

Malformed controls include consumed low/high data corruption and X, wrong base and X, address 33, wrong epoch, invalid or X metadata validity, unknown start identity/copies, and a same-edge pair fault. Standalone malformed-upload checks ensure a simultaneous start veto cannot conceal a missing data/base comparison. Unconsumed low/high data copies may be X without poisoning the actual accepted word. Vetoes check internal `cur`, `cnt`, `pc0`, running and first-consumed state, rather than checking event outputs alone.

The emitted-vs-accepted negative presents valid metadata/data/address without actual `cfg_we` for missing entry 9; the original storage retains its previous word and the receipt remains incomplete. The separate already-running write test deposits a missing receipt bit as **verification fault injection only**, not a legal producer trace; it checks both rejected table mutation and no receipt credit.

Mutant witnesses in `r6/results.json`:

- Removing settle/recent authorization: `W_PLUS_1_FORBIDDEN`, actual running=1/cnt=7/pc=16.
- Crediting cfg_valid without cfg_we: `EMITTED_VALID_NO_ACCEPTED_CREDIT`.
- Crediting an emitted already-running write: `REJECTED_RUNNING_WRITE_NO_CREDIT` (fault-injection test).
- Omitting consumed data comparison: `MALFORMED_UPLOAD_POISONS_WITHOUT_START`.
- Omitting base comparison: `MALFORMED_UPLOAD_POISONS_WITHOUT_START`.
- Omitting reset invalidation: `RESET_INVALIDATES`, unknown receipt state remains.
- Clearing existing poison on upload: `UPLOAD_MUST_NOT_CLEAR_POISON`.
- Retrying after a late complete upload: `LATE_UPLOAD_NO_RETRY`, actual running=1/cnt=7/pc=16.
- Applying an output-only veto: `W_START_FORBIDDEN`, actual internal state starts with unknown old prefetched data.
- Omitting reload invalidation: `RELOAD_INVALIDATES`.

All builds ran through unpinned `ot-run --mem 4 --threads 1 --disk 2` with measured fleet admission. Per-run `fleet.log` records the selected host, admission, unit and command exit. `precompile_manifest.json` freezes exact calendar, bench and runner hashes before compilation and specifies every mutation. Verification copies are generated only in fleet scratch, not installed as another RTL family.

Historical r2 is preserved: the first baseline passed 243 checks, but missing-data/base mutants and a redundant poison mutation survived. This exposed insufficient checker sensitivity, not a baseline RTL failure. r3 added independent malformed-upload checks; r4 strengthened the poison and retry mutations to actual targeted causal changes; r5 added the legal emitted-valid negative. r6 reordered W/W+1 first so the settle mutant demonstrates the exact forbidden start edge. Every historical result and failure witness remains separate. Initial r1 admitted an empty `bash -s` because tool stdin was not forwarded; it was **not a simulation run** and is not counted as evidence. Final runner passes a quoted script as an explicit command argument.

Reproduction, on fleet only:

```
python3 tests/kv_d2d_firstepoch/run_calendar_edges.py /path/to/new-results
```

Full immutable scratch results, generated verification copies and binaries remain under the recorded fleet scratch `claude/kv-d2d-calendar-edges-1019/r2` through `r6`. Local raw transport logs and extracted archives remain at `/home/ubuntu/artifacts/kv-d2d-calendar-edges-1019/`.
