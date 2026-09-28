# Qwen O4 INT8 arithmetic: direct ASAP7 route diagnostic

Source commit: `8458580674f8f75094024685585312820c1b4b34`. The tested
`ot_hdc_qwen_int8_arith` is the adopted signed INT8 code and BF16 product
path plus the five-cycle FP32 post-accumulation row-scale multiplier. It
contains no memory macro, matvec controller, TP-2 exchange or whole core.
The exact source and script hashes are in [direct_route.json](direct_route.json).

The local, pinned Yosys/OpenSTA lane mapped 3,222 ASAP7 RVT cells
(436.892 µm²) and found −190.99 ps setup WNS at the 0.92 ns O4 period.
Direct local OpenROAD then placed, built a clock tree, globally routed and
detailed-routed the same mapped netlist. Detailed route reached **zero DRC**
after four iterations. With extracted SPEF and a propagated clock, setup
WNS is **−297.76 ps** and the worst hold path is **−62.76 ps**. The
electrical report has 310 max-slew and five max-fanout violating pins;
most max-slew entries are reset pins. The 0.92 ns target is **NOT_MET**.
The relevant raw logs are in [artifacts](artifacts).

This is a diagnostic direct route, not ORFS signoff. The local synthesized
netlist leaves `one_`/`zero_` as constant nets; the direct route treated
them as signal nets to make the detailed router accept them. A production
route requires explicit tie cells and a PDN. This experiment also omits
ORFS timing/hold/slew repair, antenna, post-route equivalence, macro models,
and full tile and package assembly. Its Fmax cannot be extrapolated to the
Qwen die. The complete ORFS route remains the next gate.

To rerun the local prelayout gate:

```sh
bash tools/run_hdc_qwen_int8_arith_physical.sh --force
```

To launch the source-pinned ORFS gate on a host with the pinned Docker
image and disk-backed scratch (suggested memory cap 8 GiB; the observed
direct route peak was 815 MB):

```sh
OT_PHYSICAL_STAGES=pnr bash tools/run_hdc_qwen_int8_arith_physical.sh \
  --force --keep-workdir /disk/qwen_o4_int8_arith_orfs
```

The direct route can be reproduced from the three `tools/qwen_o4_int8_arith_*.tcl`
scripts after retaining the mapped netlist with `--keep-workdir
/tmp/qwen-o4-int8-arith-sta`; their paths are deliberately local to this
diagnostic and should be adjusted on another host.
