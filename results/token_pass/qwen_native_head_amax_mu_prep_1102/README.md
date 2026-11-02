This SOURCE PREP executes the actual `qfd_dv_amax_mu #(NU=4)` logical numerical
component. It does not execute the selected flattened HARD1 control subtree,
simultaneous sixteen-lane station assembly, full vocabulary, ROOT or token path.
The selected HARD1/NU4 wrapper uses generated `qfd_dv_s5_ctl_repair4`; describing
a standalone MU result as that hard subtree would require its equivalence receipt.

The11 full16-lane input words contain exactly the176 scalar values qualified by
the native post PASS9e2427a8c across8sequential2-lane regions. No zero padding or
synthetic values are added. Source addresses remain0+16*j for vectors0..7 and
18944+16*j for8..10. The finite partition gives distinct expected candidates:

| User | Vector indices | Index | FP32 value |
| --- | --- | --- | --- |
| 0 | 0,4,8 | 11 | 410d3210 |
| 1 | 1,5,9 | 30 | 41078928 |
| 2 | 2,6,10 | 36 | 4119bef9 |
| 3 | 3,7 | 63 | 40dd051a |

The independent subset maximum over all176 remains index36/value4119bef9.
All176 values are finite and distinct. This fixture does not claim new tie
coverage; existing MU tests cover the lower-index tie rule.

Four copies of the unchanged native MU module run in one ELF: baseline and
existing MUT2(currentSTNuser merge), MUT3(clearall), MUT4(emitcurrentSTNuser).
These are causal checks of the actual source mutations, not replacement math.
The baseline must emit all four exact index/value/user candidates without fault
or emit_empty; each native mutant must diverge observably at an emit. The bench
uses the selected logical ctl pending expression, allowing a new STN on the old
last-result edge. The MU captures the old STN user into au0 on that edge, then
carries it through au4 and merges atE+5. Six quiet edges drain before later clears
or emits. Later clears make clear-all destructive to already settled users.
Final currentSTNuser2/nonamax differs from firstAMAXemituser0, exposing MUT4.

The clock is an explicit nominal833ps with1fs precision, and the whole finite
bench has a200cycle watchdog. No production phase/calendar or physical timing
claim is made. No RTL compilation, elaboration or simulation has run in PREP.

Packet2 corrects descriptor legality: each of the11vectors has its own one-word
STN with exact original dbase and r_idx0. Same-user replacements are included
on every disjoint-vector boundary. The bench asserts r_addr equals the latched
old descriptor base and stn_left equals1 before each result. Same-edge capture
of the next descriptor leaves the old result attribution unchanged. The final
nonamax user2 context is a one-word dbase0 command; it produces no AMAX input
in this boundary fixture, so no station completion is claimed for that context.
Packet1 remains immutable NOT_RUN_SOURCE_DESCRIPTOR_CORRECTION.
