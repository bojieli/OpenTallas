The opt-in `ot_hbm_idx_topk_link_static_tree` keeps the public interface,
registered shell, eight 64x512 SRAMs, record ordering, 171-slot ingest calendar,
and 16-beat II8 output calendar. It adds no pipeline edges or arithmetic.
A bounded binary compaction tree replaces the serial 32-bit-index writes into
a 4608-bit temporary; only seven carry records persist. Carry payload needs no
reset because reset/clear of `fill` masks all old payload before use.

Actual admitted gate, 2026-10-26:
`epyc1:/srv/opentallas-scratch2/claude/codex-hbm-topk-tree-1026/exact`
completed exit 0 (unit oth-ubuntu-42957-1793012344). Four frames compared the
canonical core and candidate on 2048 independently checked records, all 256
flits, and 1232 cycle samples. Halveswap, flit-tag, and dropped-slot mutants
failed with 2112, 320, and 2669 errors. The final frame exercises all 20 index
bits. This is a functional test clock, not an 833ps timing qualification.

The sibling `formal` run, unit oth-ubuntu-75427-1793012405, proved all input
masks and data for an 8-record/8-bit instance against serial stable compaction:
`SAT proof finished - no model found: SUCCESS!`.

`run.sh REPOSITORY FRESH_OUTPUT` replays these gates inside an admitted ot-run.
`../topk_tree_model.py` records the pre-build traffic, area, and timing model.
The 244404-cell estimate is not mapped evidence. Actual full-shape mapping,
400k-cell cap, floorplan review, and TT/FF timing remain open. No default RTL,
physical binding, clock contract, or release claim is changed by this source.
