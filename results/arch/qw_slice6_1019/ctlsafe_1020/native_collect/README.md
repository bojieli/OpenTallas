# Existing CTL/AMAX mapped jobs: terminal pickup

All three previously live synth-only jobs have finished successfully as synthesis processes, but **all three fail the binding mapped <=32 fanout census**. No job was relaunched, no RTL changed, and no gate or submit was launched for this pickup.

| Exact candidate | Mapped drivers >32 | FF drivers >32 | Raw input ports >32 | Maximum loads | raw rst_n loads |
|---|---:|---:|---:|---:|---:|
| CTL construct3, generic cap32 | 142 | 10 | 0 | 159 | 6 |
| CTL construct_rst1_16, internal cap16 | 7 | 3 | 0 | 61 | 2 |
| AMAX NU4, generic cap32 | 76 | 23 | 5 | 64 | reset port is named rst |

The native_census.py parser counts actual mapped primitive input pins and output consumers through transparent BUF/INV trees. It includes raw input ports and resets and excludes only clocks/constants/buffer roots. Each mapped Verilog SHA is recorded in census.json; gzip archives preserve the exact netlist and complete terminal Yosys log.

The cap16 variant is closer but remains FAIL. Seven roots: NOR2 _21650_61, _21656_58, _21658_58; plain FF u_22154 48, u_67 46; NAND2 _13290_33; async FF u_1 33. Generic-source tracing: u_67 and its bounded copy u_22154 capture tok_v; u_1 is a kept g_arm copy. The three NOR roots select per-user argmax output from am_eu[1:0]. NAND _13290_ includes chd_q_r[1032] (ar_q[512]) and a reduction term. ABC expanded/reshared these controls beyond the generic16 terminal-load estimate; further consumer-local decode/selection isolation is required before another native check, and all seven must be fixed. There is no count waiver.

Process completion:

- construct3, ep5 unit oth-ubuntu-1492343-1792482266, local client2891938: exit0, terminal01:04PT, Yosys0.67 loghash3179493d21, elapsed1196.86s.
- construct_rst1_16, ep5 unit oth-ubuntu-1572465-1792482895, local client3018469: terminal01:17PT, Yosys0.67 loghashffb304eecd, elapsed1341.22s. Complete mapped.json and mapped.v exist; client no longer live.
- AMAX NU4, ep7 unit oth-ubuntu-1939911-1792482414, local client2917450: terminal00:59PT, Yosys0.67 loghash74edc9c51d, elapsed397.34s. Complete n4.json and n4.v exist; client no longer live. Child earlier NU1 failure is preserved on codex/qw-amax-csafe-1020 @6ef383e8e.

Functional-model hold: ROOT identified an incorrect Yosys read_liberty-generated ASR functional model. These mapped **counts** do not simulate that model and remain valid. The CTL exact benches use only original behavioral RTL and generic qfd_bmath helper always blocks; they do not import or simulate the ASR library model, so those pure RTL equivalence receipts are unaffected. Any future functional proof importing the suspect ASR model remains provisional until the canonical PDK/Lib truth coupon is resolved by ROOT. No adoption is justified by this packet.

All original fleet outputs remain untouched at the previously recorded remote paths. There are no remaining live clients among these three jobs. Parent was given the results; pending entries and takeover lane/log are updated.
