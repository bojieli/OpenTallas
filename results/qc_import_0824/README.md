# QC import continuation

Inherited source import is complete: 48,259 mapped cells (22,365 FF, 25,894 combinational), with 44,967 native cells and 44,906 original route records preserved. Physical source: intel2 `/srv/opentallas-scratch2/claude/qc-import-1/provider/provider.odb`, SHA256 23516fd27f5ad181e04ecea7c0e8c5115943bc343f45367eeb58db66f78d736a.

Actual post-import registered reach found two native reset fanout failures: 483.618/469.233 um. Internal provider arcs remain <=401.67 um. The first receiver of each failing chain is relocated by -79.92 um y, keeping exact cells/graph/clock nets and adding no cycles. See the review and `reset_fix.json`. Fresh abstracts, native bindings, preflight and import run under intel2 `/srv/opentallas-scratch2/claude/codex-qc-import-0824/reachfix`. The copied predecessor `qc_import_3_1029` source files preserve work that had not reached a commit at the usage limit.

Native power census on the actual imported source: 377 macros, 754 terms, 140,155 M7 fragments; 138,417 direct contacts and 1,738 short fragments. All 1,738 short fragments have bounded same-net M8-to-M9 bridge candidates (max 4.044 um), zero unplanned fragments. This is geometry, not DRC/IR. Full mixed 185,698-contact PG construction remains in progress, with a first failure being diagnosed. Original failures remain intact. No die freeze, routed clock or sign-off claim.
