Bounded W10 mask-domain fix and first-principles NAND-basis audit.
Base main4eb19f90ac1859e42d140dd30ff097ec5c2f029a, isolated sparse tree
/home/ubuntu/w10-q-mask-domain-fix, branch codex/w10-q-mask-domain-fix.
Ram whole-candidate64c6bffe0442cdf9126a6eaac752591b6a8e8389 is integrated as4eb.
He retains sole whole geometry/allocator ownership; this patch only validates
the existing balanced NP8192/128region/BF8 masks before search inputs/allocation.

Fix: explicit ValueError for q outside [128,7168], strict int not bool, combined
per-region/NP bounds and count checks. Q then BF occupies disjoint intervals by
construction. All choices are prevalidated, including mixed valid/invalid lists.
No allocation policy, target geometry, default choices or accounting changed.
Guard survives Python-O; no invalid output receipt is written. Frozen original
q8192 mask remains in a meaningful negative test, showing all128 BF spills and
final first_pair8192. Positive7168 fully covers8192 Q+BF slots, all in bounds.

Validation:
 python3 -m pytest -o addopts= -q tests/test_w17_geometry_mask_domain.py tests/test_w17_conservative_geometry_search.py
21PASS including independent interval/disjointness checks, boundary negatives,
pre-input rejection and optimized-Python CLI negative. Default CLI receipt
reproduces original e61 search.json BYTE_IDENTICAL:
 python3 tools/w17_conservative_geometry_search.py --out /tmp/w10-mask-default.json
 cmp /tmp/w10-mask-default.json results/quality/w16_w17_geometry_search_20261001/search.json

First-principles source finding, original construction preserved:
tools/w10_q_constructive_area_bound.py at6da3c7a60 has SHA
3ca30a894172a506ae0e62a905b3c248dc81e38a3e99080cc259fab93cf0895f.
It groups AND/OR at two NAND2s/output bit. Independent-input OR requires three
NAND2s without free complements. Audit exhausts all acyclic networks up to two
gates, even with free constants, and finds none; three gates implement the exact
OR truth table. Negative missing input inversion changes the truth table.
 python3 -m pytest -o addopts= -q tests/test_w10_q_nand_basis_audit.py
2PASS. These prove a generic coefficient defect, not a whole-netlist minimum.
Shared complements/constants may optimize actual logic; no such sharing proof
is emitted by this per-operator allocation. The prior conservative construction
cannot be promoted as a proven NAND upper bound from its coefficients alone.

Actual coarse JSON SHA9739ef29a2cb4b494e47c6ae19d4215486a46eaac91973188c3eefeb98037b2f
contains3937 OR cells/18827 output bits. A local OR3 repricing sensitivity adds
18827 NAND2s:1646.98596um2 stdcell,3293.97192um2 at50%density per Q pair;
OR-only pair allocation would be0.249840488880mm2, additional3.373027246080mm2
for q1024. This is not a complete corrected construction, area/power proof or
new architecture candidate. Reset/multiport/signed/bidirectional-shift network
semantics, complement sharing, fanout/clock/SSFF remain unproved. Published
6da construction and e793 power stay unchanged. Ram must explicitly join any
later corrected complete construction/power, not silently reuse those pins.

Source-pinned audit reproduction (Python3, retained coarse JSON, no heavy tools):
 python3 results/quality/w10_q_mask_basis_audit_20261001/reproduce.py --output /tmp/w10-mask-basis-audit.json
 cmp /tmp/w10-mask-basis-audit.json results/quality/w10_q_mask_basis_audit_20261001/audit.json
All changed tool/test and audit sources are pinned in audit.json. Unified model
SHA2da5b6d9...260c45 byte-identical. No old result/failure/RTL/macro/main/TASKS/docs
edits, allocator replacement, synthesis/mapping/engine/P&R job, tuning or retry.
No new complete geometry, thermal, latency, exactness or adoption credit.
