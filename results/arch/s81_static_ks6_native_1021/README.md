# Static KS6 source cost and native census

This packet concerns only the default-off static KS6 adapter. Source5cf63dca5
preserves six opaque descriptors and SPAN1259408 fixed launch edges. The original
indexed312-bit queue and wide shared enable roots failed the authoritative
mapped native census. The failure is preserved under baseline/.

The corrected source uses four13-bit descriptor banks and12-bit state banks.
Read pointers and epoch validity are replicated at the original update edges;
all52 descriptor bits retain their exact order and issue edge. Data is unreset
and protected by the existing SYNC/ARM/row0/seal/output-valid protocol. One
programme-length seen bit preserves rejection when no length was provided.
There is no extra run-time or reset-release edge, new clock, SRAM, layout or
physical qualification.

RVT TT mapping:3452→3248 cells,511→528 FF,395.87616→375.1434um². Added17 FF are
12 local read-pointer bits, four local epoch-valid bits and one length-valid bit.
The final authoritative census passes with max31 dynamic loads,24 reset-port
contacts, zero violations and zero role errors. Baseline max203/26 violations
and the intermediate bank13 attempt are retained. The coarse baseline had6485
generic cells,511 FF (312 payload and199 reset),3260 mux; it supersedes the old
470-FF estimate. Total sequential state remains below2kbit and needs no new SRAM.

Reproduce mapping on a fleet host with the source and tools snapshot using
`python3 tools/s81_dv/ks6_native_1021/measure.py --out UNIQUE_RUN`. The mapper
uses the five actual RVT TT libraries in the fleet PDK, Yosys0.68, ABC833ps,
and the unchanged tools/ref_tile/native_census.py. Exact source/tool/library
hashes and original reports are in final/. The mapper's generic source_ref
label is superseded by record.json's exact source ref; the source hash is pinned.

The meaningful mechanism composition uses ONLY the candidate adapter from
5cf63dca5, exact selected S10E host dependencies from1bf1d11bc, and the corrected
existing bench/runner fromfc7fc2453. The branch baseline has an older host and
is not release-host qualification. Its final eight-case run passed: six opaque starts/commands/KIT retirements plus
missing/late/wrong-user/epoch/phase/graph/programme-write-race rejection. Exact
source inventory and original logs are under proof_final/.
The prior3b40 candidate passed the original same-mechanism five cases; those
receipts are retained under proof_3b40/. No new cases or physical campaign added.
