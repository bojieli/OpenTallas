# Actual arbitrary single-sector HBM controller boundary

`ot_hbm_native_sector_stack` attaches 32 actual `ot_hbm_r14_stream_pc` instances with WR_EN=1/AQ_RD=1 to the existing per-PC K-port request/response ABI. This replaces the behavioral controller hidden inside the usual simulated PHY for this component. The external boundary consists only of physical row/column commands and read data. Real bank activation, precharge, refresh and R/W timing are executed by the existing synthesizable controller RTL, not a testbench arbiter or scheduler.

The first admitted protocol is explicitly single-sector (`len=1`), one outstanding request per PC. It validates the full native XOR channel mapping and stack capacity, derives the exact bank/row/column, retains the requester tag, returns read beat 0 and acknowledges a write only after its actual WR physical command. A row change drains the old open-bank state before enqueueing the new access: the access queue protects its target against PRE, so enqueueing while the old row remained open would deadlock a stale bank. Actual row commands update the wrapper's drain monitor. No external command is invented to clear it.

The controller inherits its documented 1.024 ns CK/2 domain. This is not a change to the core clock. A core-to-controller CDC and a real physical view/root assignment remain necessary. The existing R/W controller source lacks the SECDED shadows of the separate protected read-only `ot_hbm_accel_stream_pc`; this component does not claim protected-state admission.

Terminal unit `oth-ubuntu-1466583-1792054878` on EPYC4, 4 GiB/one thread: 64 physical WR, 64 physical RD, 64 true write ACKs, 64 exact read tag/data returns and 534 REFpb commands. Four fixed 512-edge windows each issue one request on every PC. The external DRAM-only checker validates address identity, ACT/PRE/REF bank state, tRCD and tRP/tRFCpb; six-cycle read-data return is modeled only outside the physical pins. An enqueue-ACK DUT mutant and a wrong-bank DUT mutant both fail. Maximum measured request-to-write-ACK age is 192 controller edges; maximum request-to-read-response age is 245 edges in this campaign. These are component measurements, not full programme prices or worst-case guarantees.

No physical, full native layer/token, complete DRAM timing-standard compliance, fault-protection or throughput qualification is claimed. This correct single-request baseline is structurally too serialized to inherit the wide WB price. A following same-row queued successor should retain many writes per PC while using the existing actual access queue and associating each physical WR command with the correct retained data. Different-row fencing remains local to the external HBM service boundary. K-port bursts above one sector are explicitly refused rather than silently interpreted with a different physical address layout.

Reproduce through fleet admission:

```sh
PYTHONPATH=tools python3 tools/hbm_native_sector_controller_gate.py --out native_controller_proof
```
