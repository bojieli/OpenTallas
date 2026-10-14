# Current Qwen edge closure audit

This audit preserves each source and routed result. A CLOSED child route does not establish the native parent pin, phase, payload, placement or pricing contract. No attempt counts are inferred. All die slots, PG assignments and final pin coordinates remain UNASSIGNED.

## Cache: functional readiness repair versus pin qualification

| Candidate | Exact source / routed record | Result and remaining native debt |
|---|---|---|
| Balanced 216 cache | `rtl/physical/ot_qfd_su_cbuf_native_l0.sv`; record `98c34391e` | CLOSED TT +53.74 / FF +16.64 ps, DRC0; clock spread33.2/20.6. Actual first-load TT has108 launch violations. Preserved original profile. |
| Registered request and ready position (HB4) | `ot_qfd_su_cbuf_native_l0_reqepoch.sv` and `ot_qfd_crom_lbuf_ready_epoch.sv`; producer `1daadbaf4`, CLOSED `82b5e8ca7`, imported `960408493` | CLOSED TT +87.74 / FF +16.17, DRC0, SS−222.26. Actual TT110 launch violations:101 far-address,8 far-read,1 CROM output; maximum238.68ps against220. TT capture≤182.92. No adoption. |
| Exact native P13/L12/HB2 | `rtl/physical/ot_qfd_su_cbuf_native_l0_p13_l12_h2.sv` source `1e83cb125`, routed producer `cc8e0c99a`, CLOSED `1d8db1bdc`, imported `1f618e9e3` | CLOSED TT +82.80 / FF +6.35, DRC0; SS−182.44. TT23 violations:22 far-address launch, max279.13; reset capture307.25. FF one reset capture252.03; FF launch max219.27 passes. This reduces violation count but does not qualify the interface. |

Source-defined changes are structural: actual ready position18 travels with stage/ready; an existing token-event priority bug is repaired only in the distinct ready-epoch clone; eight real groups join through a234FF, two-edge readiness cohort leaf. The P13 profile checks high position bits rather than truncating them silently; position8191 is positive,8192 faults. Fixed total far latency12 removes the31-tap dynamic selector. CROM remains five edges; external far response11 plus registered request is12 internal edges. HEAD36 is preserved; payload qualification remains actual layer0 only.

HB2 versus HB4 is physical pad tuning. It cannot repair the reset fanout/interface structure by itself, and its routed negative result is retained. Exact unit positives include38,152 and76,444 payload checks, two tokens, and the upper native position. Wrong latency, high position, row/bank, request epoch and stale-ready mutants are genuine failures. Full SU64+CROM5 generic operator composition is exact120 accepted operations, including regional reducers and all seven streams (`cbuf64_entries_bound`, source `b08c63a36`). This is separate from accepted native-program IB proof.

Decisive next repair: isolate external reset through an explicit local asynchronous-assert/synchronous-release register in a new named source and price its additional release edge; inspect the actual far-address Q→hold-stage→pin paths and driver/load before changing the supported hold/driver recipe. Keep220/190ps pin budgets, all corners, and actual output-driver/wire costs. Registering data or renaming a CLOSED view cannot erase the remaining launch failures.

The actual readiness join is CLOSED `7384c38a3` / import `c321dfb67`, view `physical/ref_tile/qfd_cbuf_ready_join8/views/qfd_cbuf_ready_join8`. TT +323.72 / FF +21.79 / DRC0. First-load TT launch194.70 and capture158.11; FF137.51/121.45, zero TT/FF pin violations. TT clock R85.9, min82.3/max89.1, separate extrema addends3.2 launch/3.6 capture. The SS pin sensitivity fails234 pins. Actual eight-group→join→native59 wiring and phases remain unqualified.

## TX adapter: relocated capture is structural, pad selection is tuning

Original P12 CLOSED `04eadee47` retains its source and view. Its TT20 TX launch pins fail, max240.95ps. The distinct two-clock source `rtl/physical/ot_qfd_link_proxy_txcap_candidate.sv` (`e1cc465ee`) moves the existing148bit TX capture into the leaf with literal `ck` and `ck_tx`. The complete proxy still has78 roots and the same16 added logical cycles. External4 TX/5 RX credits, DATA1024/FDI1043, real internal P12 storage and R queues are preserved. This is not an old IBUF4 view alias or proof of native573+573 record packing.

The HB4 two-clock child CLOSED `0bd41d600`, import `48ea35a31`, has TT +182.88 / FF +4.55 / DRC0 and SS−71.65. The complete family is `physical/ref_tile/qfd_link_adp128_p12_txcap/views/qfd_link_adp128_p12_txcap`. Literal per-root R: TT body304.5/TX178.0; FF243.3/190.4; SS405.6/169.9. Actual ck_tx boundary spreads are100.3ps TT,107.3 FF,95.6 SS, exceeding80 despite148sinks. This is an additional clock-distribution defect, not waived by the root count. Actual first-load launch fails130 TT pins(max307.40),9 FF(max225.30). TT capture167.25 passes. These facts prevent native adoption.

The source-bound, read-only phase diagnostic uses the actual final ODB/SPEF/SDC, exact loaded libraries, actual clock pins/posedge arcs and source150ps transitions. It clears source phases for raw checks and then compensates each real root by its measured−R, without changing exported raw records. All148 body→TX paths are checked for setup and hold; there are no reverse TX→body paths. Correct-unit diagnostic (`sta::time_sta_ui`, run2434926) gives:

| Corner | Raw setup / hold ps | Ideal per-corner common-phi setup / hold ps |
|---|---:|---:|
| TT |431.77 /97.61|558.27 /−28.89|
| FF |536.20 /15.14|589.10 /−37.76|
| SS |261.25 /224.95|496.95 /−10.75|

Thus raw equal-source-phase closure hides a real internal hold defect under this compensation hypothesis. Ideal per-corner compensation is an algebraic diagnostic, not a physical nominal die source/tap assignment. Fixed nominal delivery plus corner residual arrivals remains required. The earlier diagnostic supplied values in the wrong UI units; its logs are retained in `adapter_txcap/phase_v2_units_error` and are explicitly invalid as compensation proof. No phase PASS was claimed from it.

Distinct HB2 source `ot_qfd_link_proxy_txcap_h2_candidate.sv`, source `873ca79a7`, preserves functional behavior and ABI. Actual2000-word line rate is1.000word/clock, stall3000 and three reset epochs pass; all five credit/pointer/data/epoch/reset mutants fail genuinely. Fresh CTS primary root2965/sp28.5 has diagnostic hold−59.70ps. This is an open defect, not a routed or native success.

Decisive next repair: put a measured minimum-delay structure on the entire atomic148bit body→TX crossing, bind it to actual nominal source/tap phases and all-corner residuals, and separately repair the external TX pad driver/load path. Preserve every header/sequence/credit bit and whole-word commit. No new pipeline edge is presumed free; if required, price it and repeat actual parent/full FDI tests. The physical78-root frame, exact pins/PG and native record packing remain open.

## Head/SFUs: matching parameters do not establish source reuse

Historical CLOSED `qfd_su_lane_h`, `qfd_su_sfu_exp/rcp/rsq` views were produced by `943c39997`. Current `rtl/hdc/ot_hdc_fp32_mul_lat.sv` differs by30 changed lines from that producer. Default parameters still match actual ML15/RD2/QLA4/QLM5, but the changed dependency prevents automatic reuse. `parent_crom5/leaf_reuse_audit.json` pins the source differences; original views remain unchanged.

Source-exact generic retained-state census is13153FF + one real128×256 tail SRAM for the native head; EXP11306, RCP8190, RSQ12561. Each separate root is below15,000. The real macro is blackboxed and charged separately; the first behavioral-macro census OOM is preserved, not called a state result. QLA3/QLM3 is a separately labelled hypothesis; actual hard guards require4/5. No combined51k lane-root alias or count waiver is used.

Distinct current-source gate candidates are `qfd_su_lane_h_native_crom5` and `qfd_su_sfu_exp/rcp/rsq_native45`, wrapper/kit producer `eb35db4b5`, specs under `physical/qwen_native_cbuf/native_lane_views`. Head gate46726 completed:11845 clock sinks includingone realmacro, TT boundary550/sp33.5, FF425/sp27.9, SS762/sp71.2; estimatedcut638.5ps>600 remainsopen. Current SFU CTS:

| Candidate | Mapped FF | TT spread ps | Remaining physical debt |
|---|---:|---:|---|
| EXP native45 |9861|29.3|Estimated cut635.1ps>600; local reset driver3191 loads>3000|
| RCP native45 |6819|28.4|Estimated cut621.8ps>600|
| RSQ native45 |9688|33.2|Estimated cut620.1ps>600|

Positive clock-count/spread screens do not waive these cuts or reset fanout. Decisive next repair is loaded-scene path inspection, then a source-distinct arithmetic cut/retime or regional control replication with preserved or explicitly repriced latency. Whole-parent consumers and negative-source proof must bind the resulting implementation. The new wrappers are currently gate-only requests, not four newly qualified hard children.

## Parent milestone and live work

`rtl/physical/ot_qfd_native_crom5_su64_parent_candidate.sv` (`2383b4578`) concretely instantiates eight P13/L12 cache leaves, the readiness join and the independent-root SU. Source-exact remote lint passes. It exposes355 cache/consumer clock entries; adding the actual native59 control, station and16 program banks gives373 requested entries. `parent_crom5/graph.json` lists source hashes, typed joins, phases, slots and unresolved debts.

Native shapes are decoded from the exact25-word program SHA `cc5bc8fc17d4068ac9a49e8bf79f34e74350d56d114dd7fe5cde433d2ac82796`, decoder SHA `2009bf4312e43f405971f39e3fca747450d5467850e5a7f081781a2c0e3e6542`. PC6 is5×128 QK; PCs7–10 are4/1×64 RoPE. Candidate PC12 is ME, not the historical SU operation. Pos100/101 catalogs are source-generated, not hand-adjusted.

The96GB standalone actual shapes459/session16469/unit2218563 is terminalPASS120accepted: streams480/240/240/480/432/0/48, two epochs/waits345/go2/early0/fault00;119 samples ref3097/dut7381/delta36exact. The actual parent bodyf054/session59700/unit2281803 is also terminalPASS120, with identical exact receipts and119sample/ref3097/dut7381/delta36. Compile1569.852s, reported54,792.215MB allocation; no inferred RSS peak. All are memory-auto jobs, not timeouts relabelled as failures. CROM5/CRX4/MC6/ML15 alignment9 is explicit; external VM staysVL7. These are standalone source-decoded SU component proofs, not accepted raw native IB or whole-token qualification. Native59 accepted-program binding, writer lease, epoch/fence, die source/phase/PG/pins, constructive slots and full price remain explicit open joins. Old reset mutant70490 is still running; no duplicate or timeout-based failure is inferred.

Current follow-through candidate: `ot_qfd_su_cbuf_native_l0_p13_l12_r2.sv` adds exactlyone local asynchronous-assert/synchronous-release state bit, reducing the external reset toone direct register load. Its additional release edge is explicit; normal CROM5/far12 latency is unchanged. Separate HB4/BUF2 supported pad/driver recipe is a measured candidate, not a promised solution or new CLOSED view. Fresh exact/mutants/CTS will decide it.
