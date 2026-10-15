# Registered PC boundary candidate

`ot_hbm_svc_static_pc_boundary` is a distinct structural candidate around the unchanged `ot_hbm_svc_static_pc`. The original CLOSED route and identity remain valid. This candidate has component functional evidence only: no parent adoption, production calendar, area map, pin assignment, CTS, route, exported boundary timing or whole-token claim.

The retained core exported launch is 408.99 ps at `out_data[250]`, capture is 508.02 ps at `kr_beat[2]`, and boundary clock spread is 104.7 ps. Its generic route is CLOSED (TT +13.34 ps, FF +23.42 ps, DRC 0), but those boundary figures do not satisfy the current native boundary requirements. The core drives read data directly from its real SRAM; KR inputs drive qualification and SRAM write/control logic without input capture. The successor inserts actual FFs at both faces instead of changing timing metadata.

The candidate has separate `clk` and `core_clk` pins. `clk` clocks the new 1,313 declared register bits; `core_clk` belongs to the unchanged core. The 36 constant request-length/strobe register bits may optimize away, so 1,277 bits is an estimate before synthesis, not a mapped census. SRAM count remains one 128x256. A physical implementation must harden the boundary FFs as a real leaf, preserve the core view as a separate child, and provide independently phase-compensated clock entries. It must not declare a wires-only parent while hiding these FFs or deliver an uncompensated common clock at both physical pins. The bench uses logically synchronous 1:1 clocks; physical insertion/phase and inter-child hops remain to be measured.

All compiler open/fill/read/retire/command ports have one ingress FF stage. Data and status have one egress FF stage. With the existing SRAM/core pipeline, scheduled reads now return on the third sampling edge, versus the original first edge: exactly **+2 cycles**. Scheduled pulses remain II=1, with no ready, retry, credits or runtime rescheduling. All compiler sequences must retain their relative ordering and add the declared latency before dependent operations.

The request and KR queues each hold one entry at the actual HBM PHY/controller boundary. This elasticity is confined to off-chip service; it does not implement on-chip scheduling. A queued request is not a real accepted PHY transaction. Real read/write outstanding flags only become set on external `k_v && k_rdy`; KR data and write ACKs arriving before that acceptance cause a sticky protocol fault. Same-edge accepted-request/response or ACK is supported. Registered request fields are stable during stalls.

At the logical clock level:

| Event | Added latency relative to original core |
|---|---:|
| Compiler pulse reaches core | 1 cycle |
| Compiler read reaches `out_v/out_data` | 2 cycles total |
| Initial command reaches external request | 2 cycles total |
| Accepted KR data reaches core | 1 cycle |
| Accepted KR or write ACK reaches published done/status | 2 cycles total |
| Consecutive sector request after external response/ACK | 2 extra cycles per sector |

The last row is a real service-calendar cost, not just final completion padding. No end-to-end token or service-period loss has been measured or accepted. The actual parent service/CP calendar must account for it and remain within production goals before adoption.

Run `python3 tools/hbm_v15_harden/run_svc_pc_boundary.py --out <artifact-dir>` from a source checkout containing the generated physical SRAM functional model. The positive bench checks 129 payload reads, 128 regular writebacks, 64 regular prefetches, concurrent fixed-rate read/fill, variable request stalls, same-edge PHY completions, and seven independent fault cases. It checks exact response timing and one-cycle completion pulses. Five mutants reject real SRAM address corruption, response-stage removal, write-ACK stage removal, ACK-before-accept protection removal, and KR tag corruption. The unchanged baseline's separate original bench also passes (192 reads, 148 writes, 84 prefetches, 64 overlapping cycles, five faults), and its SRAM-address mutant fails.

Next: obtain actual parent instance/ports and production slot grant; split/harden boundary FF and unchanged core with independently compensated clocks; prove the costed complete service/CP calendar; measure native TT/FF, boundary launch/capture/spread, inter-child reach, and DRC before any adoption. There is no current production parent instantiation of this PC in the source tree, so creating a kit now would not establish parent fit.
