# DCAL BC3safe uncapped native source census

Exact source **190b12e9f**, prior source/equivalence packet **c9e453458**. This is historical ordinary AW11 / K0x03030415 only. It does not qualify ordinary codec2 K0x03030416 or OVL. No RTL, role assignment, geometry, timing constraint or physical view changed. No functional programme, miter or mutant was rerun.

Independent fleet-unpinned OpenROAD analysis loaded the exact final source-only mapped ODB, SHA256 `c6a86fb5628cdb9cc1c84c8b89f2b8408507f43ef7cd0fe947b1bbe47571ad04`. The inventory has **351 FF, 259.17408 um² standard cells, zero macros, 1,771 physical output/input-port drivers, 1,413 canonical nontransparent roots and 6,688 physical signal pins**. Every driver is retained, including buffer/inverter outputs, constants and clock. Every endpoint is an actual cell pin or output port. BUF/INV traversal records the full net chain and exact inverter parity; no inference that a mapped `QN` pin is logically complemented is made. Other combinational gates are stopping endpoints. Clock, reset/preset and FF data pins have separate roles. PG pins are outside the signal census.

There are zero unconnected signal pins, zero unknown FF pin roles, zero absent/multiple signal drivers and zero transparent-cycle/reconvergent-endpoint errors. The complete records are in `census.json.gz`; `audit.py` is the exact executed analyzer. No endpoint cap or maximum-list truncation is applied.

**The uniform all-signal-root <=32 predicate FAILS.** Its complete >32 list is:

| Driver | Role | Logical endpoints |
|---|---|---:|
| `_3004_/H`, net `_1554_` | static TIEHI | 347: 346 reset/preset pins and 1 FF data pin |
| `PORT/ck` | top input driving native clock pins | 351 |

The functional-source maximum28 independently reproduces the earlier result, and includes top output endpoints. It is a separately labelled subset statistic. Neither constants nor clocks receive a blanket safe-design exception. Tie replication and an actual clock network with measured loaded bounds remain obligations before physical admission. The raw source clock's 351 sinks are not a CTS result.

Reset ownership independently reproduces: raw `rst_n` has exactly one endpoint, `land0/D`; outer first-stage Q drives four outer second-stage D pins; the four outer release copies have reset/preset loads16,16,16,23. Inner first-stage Q drives19 second-stage D pins; the19 inner release copies have maximum16 reset/preset loads. All exact pin owners, paths and polarities are retained in `reset_owners.json`. Static TIEHI reset/preset pins are included in the uniform census and are not confused with these dynamic release trees.

All **44 nonclock public input bits** terminate at explicit same-edge FF data owners:38 address/data bits have one capture each, RX/TX write enables have five captures each, epoch_go/halt/reload one each, and raw reset one outer capture. `ck` separately owns351 clock endpoints. All **53 public output bits** have unique explicit FF output owners through INV paths (parity1). `boundary_owners.json` lists each actual pin and owner. This establishes fixed logical I/O FF ownership; it does **not** establish physical face placement, delay, electrical loading or native phase. The old21.6x34.56 frame is not inherited or approved.

The prior frozen-wrapper equivalence is behavioral evidence; this packet is native source topology evidence. Neither establishes parent source safety, placed occupancy, PG/access, native launch/capture/extrema, reset skew, parent slot binding or STATUS/admission qualification. Actual parent DCAL sticky-fault consumption remains open independently. No physical gate or submission ran.

`audit.log` records the terminal fleet unit and exit0. Two earlier invocation failures (missing executable paths) are preserved under `/home/ubuntu/artifacts/dcal-uniform-1019/audit.log` and `audit_r2.log`; they ran no engineering analysis. The first complete analysis (`audit_r3.log`) was refined to include unconnected-pin and unknown-role checks; the final analysis is the committed result.
