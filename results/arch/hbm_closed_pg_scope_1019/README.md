# Selected CLOSED HBM final native PG audit

Read-only, exact final OpenDB ITerm-inventory proof. Historical timing CLOSED is retained; these
four completed views are **PG_HOLD** for adoption. This packet makes no route,
fanout, numerical, whole-token or conductor-connectivity qualification claim.

| Frozen CLOSED receipt | Actual native PG ITerms | Unbound PG ITerms | Affected instances |
|---|---:|---:|---:|
| n12 g2c c11f3bb33 | 1,647,394 | 1,494,572 | 747,286 |
| argmax g2c c11f3bb33 | 191,464 | 780 | 390 |
| pretree p3 1dad69123 | 1,997,964 | 1,627,080 | 813,540 |
| rootctl r4 49a5acb8f | 7,078,106 | 6,931,852 | 3,465,926 |

All failures above have empty actual nets, correct native POWER/GROUND MTerm
roles and exactly one expected net from the original OpenDB global-connect
rules. The rules are exact `.*` instance patterns with explicit native VDD/VSS
and memory supply pin patterns; no inferred names, exemptions, or global_connect
calls were used. Full failures include fillers, hold ECO cells, clock cells and
other buffers/inverters. See grouped_summary.json for exact master/role counts.

N12 includes 1,450,868 filler PG terms, 41,302 hold ECO HB2 PG terms and 2,402
BUFx24 PG terms. Pretree includes 1,531,146 filler PG terms, 73,206 hold ECO HB2
PG terms and 22,728 other BUF/INV/CKINV PG terms. Argmax failures are 390
BUFx24 clock leaves, both supplies unbound. Rootctl includes 6,858,564 filler PG
terms, 6,476 HB2/HB4 hold PG terms and 66,812 BUF PG terms.

The bounded location check selects one actual failed instance per failed master:
6 n12, 1 argmax, 28 pretree and 14 rootctl instances. All 49 occupy covering native
placement rows; all 98 transformed native PG M1 rectangles overlap the existing expected
supply's M1 rails. This is a binding-repair model subset, not proof of complete
physical power connectivity, and it does not authorize a repair. The sample
script is specific to these verified single-domain native rules (VDD/VSS); it
does not infer the expected supply of an arbitrary voltage-domain design.

Rootctl has 3,539,053 native instances; its complete actual ITerm report and
unchanged ODB hashes are included. fc_xr2 r4 637a35abf is **NOT_AUDITED/INCOMPLETE** because its accepted
6_final.odb is absent after the recorded deep release on ep8; no older receipt
was substituted.

Collector native_pg_binding.tcl SHA256:
13e936d24fc2a2e35a9f8cc0c6047820753cb5cc8a559a13a7eb8fe56e1ebef3.
Read-only wrapper audit_native_pg.tcl SHA256:
a8445b4af300240b5b2544c39a83ab0f2bc2e42db2f0325cc33e863f6d2fb72a.
These are the standalone original644FAIL/clone0PASS-tested source prototype
from merger packet47e03369c, not activated production helpers.
Image sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29.

All OpenROAD work used unpinned fleet ot-run and read-only original ODB mounts.
The original helper overlay/source receipt, exact paths and source commits are
in selected.json. Before/after ODB SHA256 files compare identically for completed
runs. Full failures are compressed Tcl dictionaries; grouped JSON is derived,
not a substitute. Raw exports remain on their original fleet audit paths.

The initial launcher accidentally replaced its environment variable name; those
runs stopped before read_db and are preserved. Three subsequent mem4 audits
terminated137 without semantic results. Their empty/partial reports and logs are
preserved as mem4_termination; mem32 admission reruns produced the above actual
reports. Resource samples are included. Rootctl completed at exit2 before an extra32GB
reservation could update its already-finished container; that failed update
made no change and is recorded independently. No failed attempt was treated as PASS.

Qualification limit: this collector enumerates actual native ITerms and checks
their MTerm roles, domains and bindings. Newer source helper a92a40171 adds
master-MTerm completeness and missing/type-inconsistent ITerm controls. Those
stronger completeness checks remain OPEN here. The reported failures are actual
concrete negatives; these old-collector scans are not a SAFE/full-MTerm census
and are not re-run with a different helper or changed frozen source.
