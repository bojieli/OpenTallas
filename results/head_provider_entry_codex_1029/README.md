Actual HEAD AR provider entry — 2026-10-29

PASS_AR_PROVIDER_ENTRY_COMPONENT, source branch ee6a047bc plus receipts.
Unit oth-ubuntu-3702200-1793261883, ot-run24GB/4 threads, exit0.
Full runtime: intel2:/srv/opentallas-scratch2/claude/codex-head-entry/entry1

This is a new source/compiler entry mechanism through actual safe8 peer lanes,
HOST/HBC, HOST276, CTL, and all four real SRAM models. Existing RTL is unchanged.
Static compiled source calendar: model81 layer stages => separate HEAD81, rank3,
3 HBC setup records and8 CSR writes including CSR2=3; no ordinary HFWD.
The legacy417 HBC affine-book descriptor is HOST programme ABI, not activation.

Actual activation is80 K_XB records of1024bits (160x512 halves,5120 distinct
finite BF16 values). All81920 bits are checked through256 native SRAM replay
records, including the B bank repeated four times. Explicit pin-to-resident
timing places START486 after all80 beats and admits exactly one issue506.
The wrong-rank CSR2 control and omitted-last-XB control both fail the required
assertion. source_hashes.json binds every RTL/model compiled by this component.

Scope is AR-only glen0, provider-pin component transport. This does not select
or authorize a production S81 programme, bind actual die clock/reset transport,
qualify real-view timing, exercise a head compute/result, or qualify MTP. The
compiler requires a real selected job, inventory and static transport timing;
the included values are an explicit component fixture. MTP compilation requires
an explicit result mtag for CSR5; no MTP pass is claimed.

Original HOST data/control namespace collision remains a separate preserved
FAIL on an arbitrary ordinary HFWD carrier. Whether that carrier belongs to
the selected production K_HOST grammar is still unproved. This entry sends
no ordinary HFWD, and adopts neither a new wire tag nor a variable160-word
HOST book. Candidate namespace alternatives remain on a separate held branch.
