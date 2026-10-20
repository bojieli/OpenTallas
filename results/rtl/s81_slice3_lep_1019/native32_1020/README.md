# Binding standard LEP / LEPNH native pickup

Exact source 0cf34e714. Existing gates completed: LEP FAIL FF clock spread81.8ps; LEP_W WARN TT/FF75.8/74.9; LEPNH WARN40.2/36.8; LEPNH_W WARN46.3/48.2. GRT overflow0 in every case. No submission/adoption is permitted from those labels.

Read-only strict census of actual mapped ORFS netlists finds LEP526 nonclock transparent roots above32 loads, maximum1188; LEPNH502, maximum1121. Full source/tool/netlist fingerprints and input/sink examples are retained. The full root lists are gzip-compressed without changing JSON bytes; plain JSON includes all offending roots. Native units ep6 oth-ubuntu-1032238-1792482569 and oth-ubuntu-1032438-1792482569 returned0 (analysis success, not physical qualification).

No RTL/kit/source changes, launches of layout gates, submissions, or writer-tree mutations occurred. Structural fanout/reset/control replication must precede any new gate. Real registered/landed405um reach, storage, pin, timing and PG audits remain required independently of fanout.
