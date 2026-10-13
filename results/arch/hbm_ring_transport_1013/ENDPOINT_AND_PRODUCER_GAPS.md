# HBM B2 ring: regional endpoint view spec and producer-contract gaps (2026-10-13, Claude ring-station-1013)

Status: SPEC + GAP LIST. No RTL, view or bench in this note is qualified. Read with `RING_CALENDAR_REDESIGN.md`.

## 1. Regional ring endpoint view (new master, never an alias of the native D3 `ot_vms_rstop` view)

| item | value | reason / evidence |
|---|---|---|
| master | new `ot_vms_rstop_regional` (same protocol and ports as `ot_vms_rstop`, FW 2,224) | the closed native view is D3 / HF2: 0.5005 flit / cycle injecting, 0.7502 forwarding (`results/rtl/hbm_ring_transport_1013/endpoint`) |
| per-VC input depth D | plain-stage transport (proposed): `2 x S + 4` = 86-138 entries, held in a memory-macro FIFO; elastic-chain transport: 8 | full rate needs credits >= the credit round trip; D8 only suffices with a credit terminator on every segment |
| VC0 storage | D x 2,224 b in 8 lane chunks of 276 b + one 15 b header chunk; VC1 D x 271 b | chunking as in the native stop; at D 8: 17,792 + 2,168 flops; at D 138: 307 kb + 37 kb, macro only |
| hub inject depth HF | 8 on BOTH sides | HF 2 -> 1,998 cycles / 1,000 flits; HF 8 with D 6 -> 1,000 |
| control | one kept control copy per payload chunk on that chunk's clock, registered one-hot write-enable / read-select per <= 16 payload bits | the station lesson: a shared binary pointer drove 4,416 loads (gate a / b receipts) |
| clocks | 9 chunk roots + 1 control root, each <= 15,000 sinks, or measured insertion <= 300 ps and spread <= 80 ps | owner clock rule 10-13 |
| pins | every `l_in` / `l_out` / credit pin a flop at the face; faces and layers of the native stop (l_in W, l_out E); M5 cap for the new leaf, parent PG M6 | die timing by construction (owner 10-13); the native pin mix M4 / M6 needs the die lead's M6 PORT grant or a re-plan |
| slot | must fit the native ring-stop slot (241.92 um wide by the LEF bbox) or carry a slot change request | D 138 macro storage will not fit it: slot change request required |

Benches that would qualify it (all at production parameters, each with a mutant that must fail):
1. `tb_vms_endpoint_rate` at the edge's real S with the chosen transport (plain relays for the proposal): >= 1,000 flits
   in <= 1,100 steady cycles, both directions, SID 3 wrap; mutants: every 8th credit dropped, VC credit swap.
2. `tb_vms_ring4` (four slices, real hub / bank / stops) with the per-edge relay counts 41 / 60 / 42 / 67 instead of
   S = 2: exact packet and mirror-write results, measured PREQ->PRSP round trip and WBC rate; mutants HMUT / BMUT / CMUT.
3. Production throughput bench against the hop price actually adopted (not 12 / 11), ratio <= 1.10 or a ledger row.

## 2. Producer-contract gaps

| gap | where | measured today | what is needed | bench that would qualify it |
|---|---|---|---|---|
| HF2: hub inject credits | `ot_vms_slice` localparam `HF = 2` -> `ot_vms_hub` `CWI` / `CCI`, `ot_vms_rstop` `HF` | 0.5005 flit / cycle per ring direction (credit loop of 4 cycles on 2 credits) | HF 8 on both sides. `ot_vms_hub` holds `cwic` / `ccic` in 3 bits (`3'(CWI)`): 8 does not fit, widen to 4 bits. The hard hub view was built at 2: re-harden | `tb_vms_endpoint_rate -GHF=8` through the REAL hub (not the bench's ideal `pi` driver): 1,000 PREQ in <= 1,100 cycles; mutant: hub credit one short must fail the rate gate, one over must overrun |
| EGC1: bank egress credits | `ot_vms_slice` localparam `EGC = 1` -> `ot_vms_bank` (default 2), `ot_vms_rstop` | UNMEASURED: a mirror write needs a credit of both stops, so one credit a lane bounds the WBC rate by the egress credit loop | EGC >= the egress credit round trip (expected 4); the hard bank view was built at 1: re-harden | `tb_vms_slice` mirror-write stream (NWG only) with an EGC sweep, WBC flits / cycle counted at `l_out`; pass at >= 0.91; mutant `BMUT` (queue one short) must fail |
| whole producer chain at wire length | hub -> stop -> 41-67 stages -> stop -> bank / ring client | never run: every ring4 bench uses S = 2 | ring4 at real S, credits sized to the round trip | bench 2 above |
| remote read round trip | SPEC 5: 50 cycles | physical: 2 x (44-70) + 4 = 92-144 one hop, 2 hops up to 230 | compiler must treat a remote read as a scheduled pull with that lead | `tools/hgi_e2e/b2.py` with per-edge latency (done, model) then `tb_hgi_e2e` B2 = 1 + B2_RING (measured) |
| COLL star latency | `b2_params.json` bcast 12 cycles | no corridor study; estimate 33 | star polyline study, then the same sweep | `calendar_sweep.json` rows `*_bcast_phys` with the studied value |
