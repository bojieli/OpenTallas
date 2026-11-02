# Private QC active two-peer PHY boundary diagnostic

This packet checks the selected QC macro ABI and a private registered simulation
service. It does not change model selection, the canonical plan, a whole-programme
verdict, physical eligibility, or the held hierarchy build.

The current source cohort is strict-bind receipt `82190c1ff` with paired-plan event
`f79c1e228`: frozen source commit `bd55b15b452761be8ceefeae7b97abdf4a915bd4`,
epyc2 `/srv/opentallas-scratch2/claude/codex-qc62-collect-1101/bind_complete4`.
That bind has 377 partitions and 119 types; its non-ANSI top has 639 ports and SHA256
`b7db6bb8157f4e55f274b2e1d11482428d25d40803ff5bf5cb4bd7758c112295`.
The numbers 821/f79 are commit prefixes, not port or partition counts.

`inputs/` contains the frozen selected BBs and companion candidate models/metadata,
the existing registered generic KV transport model, and the two current native
consumers. `prepare.py` checks the exact selected BB port inventory, FW/LAT metadata,
native instance pin inventory, payload width, and UCIE lclk feedback. It generates
private wrappers with the exact core-facing macro ABI. Peer-facing `far_*`/`link_*`
nets are internal simulation wires connected explicitly between two instantiated
peers by the testbench. No far endpoint is tied to zero.

The private UCIE service uses the existing registered transport at FW1043/LAT4
and explicitly generates its selected 1 GHz lclk. Its TX capture plus three RX
stages preserve the declared four sampled FDI slots. The selected UCIE companion
model instead has combinational TX plus four RX stages; an unchanged copy is used
as the stale-model negative control. The selected SerDes companion already has
registered TX and 222 RX stages at FW597/LAT223, and is used unchanged.
In these models LAT means the input sampled on the first edge emerges on the
LAT-th sampled edge, including the TX capture edge; it is not an extra LAT periods
after that capture.

The diagnostic configures the current bind's UCIE clk/lclk feedback at 1000 ps and
SerDes input at 833 ps following the frozen functional vehicle's clock policy.
The exact join is in `inputs/current_clock_join.json`: actual top instances
`io_serdes`, `io_serdes_1`, `io_serdes_2` receive respectively
`clk_region_coll_n`, `clk_region_coll_s`, `clk_region_c_W5_bf_01`. Both actual
SerDes wrapper variants forward `.clk(clk)` directly to the macro. Frozen
`inputs/qc_vehicle.py:215` maps these `clk_*` inputs to `ck`; its line 263 generates
an exact 833 ps period. Its bringup override applies only to the literal
`clk_serdes` port, not these three region ports. The independent mission clock
remains 833 ps throughout the diagnostic. SerDes metadata describes a separate
1 GHz FDI assumption. Thus 833 ps is the explicit diagnostic driver condition
under the existing generator policy; the physical clock contract remains
unqualified. A source-only attempt to emit a complete fresh current vehicle
without a START provider refused 313 `pst_*` inputs, so no complete current-vehicle
qualification is implied. No hierarchy build was attempted. Both peers are
synchronous to their tested FDI service, with independent
payloads, bursts and valid gaps; no ready/backpressure pin exists in this ABI.

Intel2 job `oth-ubuntu-4087940-1793606663`, admitted through `ot-run` at 2 GB/1 thread,
completed exit 0. Only the four macro instances and bounded testbench were compiled.

| Check | Result |
|---|---|
| UCIE, 1043 bits, LAT4, 1000 ps | PASS; accepted 324/227, delivered 222/318, two mid-traffic async resets |
| SerDes, 597 bits, LAT223, 833 ps | PASS; accepted 699/489, delivered 222/318, two mid-traffic async resets |
| Corrupt one bit on an active UCIE peer link | REJECT at cycle 5, payload/latency mismatch |
| Corrupt one bit on an active SerDes peer link | REJECT at cycle 224, payload/latency mismatch |
| Original stale UCIE model | REJECT on TX changing between edges |

Every delivered bit, valid bubble, sampled latency, TX hold between edges,
asynchronous reset flush, declared clock period, and exact existing TX_UP behavior
is checked. The inherited UP16 implementation asserts after the seventeenth
non-reset rising edge (`n >= UP` before increment); this packet preserves that
behavior and does not silently reinterpret UP as sixteen edges.

To reproduce, run `bash run.sh` in this directory through fleet admission.
`run/` contains the compact positive and expected-failure logs; generated source
and its input hashes are in `generated/`. No compiled binary is committed.

The physical hold remains: selected UCIE metadata explicitly says `MODEL_ONLY`
and `physical_qualification_eligible=false`; no licensed hard implementation,
measured clock service, GDS/SI/bump qualification or native physical clock-source
proof has been supplied. The canonical coll_ucie plan still references the older
non-lclk abstract, whereas the current native BB has lclk. A real implementation
and coherent plan/view/clock event are required before physical release. This
active boundary packet provides no TP8 collective-programme, whole-QC numerical,
external mission-peer, or physical qualification credit.
