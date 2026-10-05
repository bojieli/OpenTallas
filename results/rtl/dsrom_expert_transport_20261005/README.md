Expert transport endpoint casebook: native raw32 and conditional packed shapes

Arendt source contract main7095e772 supplies raw32 native GU4608B, W2input9216B and fieldinput20480B per rank. Packed BF16 sizes2304/4608/10240B are conditional only: no actual source pack/unpack, rounding/visibility or consumer bridge is bound.

| Payload bytes | Current source role | Endpoint cycles excluding vendor | Vendor board / UCIe cycles | PHY extra | Wire | Total cycles | Total µs at 1.2 GHz |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2304 | Conditional packed GU | 47 | 156 / 11 | 0 | 90 | 304 | 0.253333333 |
| 4608 | Native raw32 GU; conditional packed W2 | 83 | 156 / 11 | 0 | 90 | 340 | 0.283333333 |
| 9216 | Native raw32 W2 input | 155 | 156 / 11 | 0 | 90 | 412 | 0.343333333 |
| 20480 | Native raw32 field input | 331 | 156 / 11 | 0 | 90 | 588 | 0.490000000 |

Original2304/4608 PASS records from source5bdbbee2f are preserved and reused, never rerun. Their historical gu_return/w2_input labels preceded the raw32 correction; casebook.json supplies authoritative current roles by byte count and the pinned Arendt contract. Only missing9216/20480 ran on source6580e0088, recorded under native_raw32/. Existing draft x_row10240B/428cycles remains an unchanged reused conditional packed-field reference, not a native field bridge. No linear interpolation was used.

All four distinct payloads passed the existing dsrom_1m_links.run_hop_case / tb_dsrom_1m_hop with identical retained endpoint/bench source hashes. Board FB64/CRED512/SEQW10, CH156 and UCIe CH11/CRED64/SEQW8 preserve the RECOVERY_HOPS recipe. Exact sent/received counts, hash-pattern payload order/data/last checks; no mismatches, extra flits, endpoint faults, stalls, CRC errors or retries. Fixture data is not actual GU provider output. Model-before-measurement, source/input hashes, command, headroom, raw summaries and terminal0 are retained for both runs.

RTL first-to-last latency already includes vendor delay lines (214/250/322/498 cycles). Add only PHY serialization beyond the endpoint and 2×45 wire cycles, once. The existing 130ns board light-FEC and8.5ns UCIe vendor budgets quantize to156/11 streaming cycles; these are vendor budgets, not analog measurements. Endpoint64B/cycle is slower than the existing PHY budget, so extra PHY serialization is0. Wire90 is the existing routed-geometry model term, not new loaded-route qualification.

Scope: one idle endpoint message, always-ready destination. Not six concurrent TP4 groups, actual provider/consumer format/order/VM binding, mutable-context visibility/ACK/leases, reverse credit or loaded fanout calendar, SS60/FF25, whole-token arithmetic or adoption. Whole-chain latency remains NULL. Maxwell owns source-bound composition; Arendt owns placement/consumer scope. Historical field failures and Claude spine/PQ redesign hold are unchanged; CFG remains parked/unlaunched.

Both jobs used one low-priority CPU worker after measured singleCPU/memory headroom guard and unchanged admit.sh1GiB scheduling estimate, with no CPU/wall/address-space/file/RAM caps. Completed remote sources/binaries remain at /srv/opentallas/repos/noether-expert-transport-{5bdbbee2f,6580e0088} and /srv/opentallas-scratch/codex/noether-expert-transport-{5bdbbee2f,6580e0088}-r1. No full array, collective or proof replay was launched.
