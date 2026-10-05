Exact-size expert transport endpoint measurements

Both cases passed on EPYC2 using existing dsrom_1m_links.run_hop_case / tb_dsrom_1m_hop and the unchanged four RECOVERY_HOPS RTL/bench source hashes. Source 5bdbbee2f; terminal exit 0. Only these two payloads ran, sequentially on the existing Icarus endpoint. Model-before-measurement, command, headroom and raw summaries are retained.

| Payload | Flits | Measured endpoint cycles excluding vendor | Vendor board / UCIe cycles | PHY extra cycles | Wire cycles | Total cycles | Total µs at 1.2 GHz |
|---|---:|---:|---:|---:|---:|---:|---:|
| GU return 2304 B | 36 | 47 | 156 / 11 | 0 | 90 | 304 | 0.253333333 |
| W2 input 4608 B | 72 | 83 | 156 / 11 | 0 | 90 | 340 | 0.283333333 |

RTL last-flit latency already includes vendor delay lines: 214 and 250 cycles respectively. Total is that measured latency plus only the PHY serialization beyond the endpoint and 2×45 wire stages. The existing 130 ns board light-FEC and 8.5 ns UCIe vendor budgets quantize to 156 and 11 streaming cycles. Do not add vendor or wire again. Endpoint rate is 64 B per cycle; existing PHY rate exceeds it, so extra PHY serialization is zero for both measured payloads. No linear interpolation was used.

Board credits512/SEQW10 and UCIe credits64/SEQW8 exactly preserve the existing recovery-hop recipe. Both messages delivered the exact flit count, hash-pattern payload order/data/last, with zero mismatches, extra flits, endpoint faults, credit stalls, CRC errors or retries. Hash-pattern payload is transport-fixture data, not an actual GU provider output.

This is endpoint payload timing plus explicitly modeled vendor/PHY/wire terms on one idle link with an always-ready destination. It does not qualify six concurrent TP4 groups, provider/consumer format or visibility, mutable-context retirement, loaded fanout, SS60/FF25, a full token or adoption. Arendt and Maxwell own subsequent service/calendar binding. Historical field failures and the Claude spine/PQ redesign hold remain unchanged. CFG is parked and was not launched.

The measurement used one low-priority CPU worker after sampling at least one idle logical CPU and sufficient memory; existing admit.sh was unchanged. No CPU/wall/address-space/file/RAM caps were applied. Completed remote source and binaries remain at /srv/opentallas/repos/noether-expert-transport-5bdbbee2f and /srv/opentallas-scratch/codex/noether-expert-transport-5bdbbee2f-r1.
