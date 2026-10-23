# Actual r51 MAIN and geometry alternate head preparation

Both actual r51 die/forwarded-lane/parameter byte sets pass with13 core edges to the internal SYSFACE held bank:

- Selected cpub39_1 SHA5d45a822 calendar source capture and publisher:2.
- Actual TT.head_prepare bundle (all4 fields):3.
- Existing native prepare descriptor build:3.
- Actual SF.head_descriptor bundle:3.
- Source-qualified face input capture:1.
- Held-bank availability:1.

The face output capture is a separate1 edge belonging to the later published head-TX/codec-wire ledger; it is not included in this internal held-bank date. Physical clock/STA qualification remains separate. Both dies select publisher1/local2; the physical publisher2 prototype is not aliased as the geometry alternate.

The original r51 outputs were copied byte-for-byte into a bounded source-complete measurement readset so admission could place the tiny parser independently. main_input_hashes.json/alternate_input_hashes.json record original resolved paths and exact die/lanes/params SHAs, also present in each result. No original GEN, progressing projection or source was changed. The new endpoint audit enumerates all declared source/destination instances, fixing the old hardcoded seam-only set that skipped tt_ctlm entirely. Extra token-edge and missing-user-pin regression cases fail; the seven existing bundle tests pass.

Actual run: gold1 oth-ubuntu-198840-1792733112,4GB normal admission. Remote readset /srv/opentallas-scratch/claude/codex-headage-bounded-1022/{c,d}; source snapshot includes exact current typed source receipts and every SYSFACE wrapper hash dependency. No old local4, old RTL SHA or LP schema reinterpretation is used.
