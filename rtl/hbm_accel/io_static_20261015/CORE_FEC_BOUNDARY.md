# Actual core-to-FEC and FEC-to-core boundary

`ot_hbm_core_fec_word_window` instantiates two unchanged actual
`ot_hbm_static_word_cdc` FIFOs at 487 bits, 16 entries and a 2,048-word finite
window. One writes on core and reads on FEC; the other writes on FEC and reads
on core. All starts/takes/last flags are compiler reservations. Gray pointers
only diagnose ownership; they never select issue. Each fault output belongs
to its declared local clock domain. The two storage arrays contain 15,584
actual register bits, plus 974 registered read bits and control.

Core and endpoint clocks remain 1.2 GHz (833.333 ps). FEC runs at 16/17 of core
(1.1294117647 GHz, 885.417 ps). One model tick is 52.083333 ps: core period 16,
FEC period 17. The full gate uses separate clocks at these declared rates;
there is no core-frequency relaxation or ideal wire replacing either crossing.

The original continuous gearbox cannot discard one word in 17. The distinct
`ot_hbm_static_gearbox_step_tx/rx` and frame wrapper accept an explicit
compiler `word_step`. Their phase advances only on those reserved edges;
skipped edges produce no word/frame valid. A received word on an unreserved
edge faults. This fixed calendar is independent of data, ready and credits.
The original continuous gearbox and prior 102/151 component profiles remain
unchanged.

For word index k=0..2047 and C(base,k)=base+floor(17*k/16):

| Boundary | Reserved edge, in its own clock units |
|---|---|
| TX gearbox word | core C(511,k), first 511, last 2685 |
| TX CDC write | core C(512,k), first 512, last 2686 |
| TX CDC read | FEC 488+k, last 2535 |
| Actual FEC input capture | FEC 489+k, last 2536 |
| Actual decoded capture | FEC 640+k, last 2687 |
| Existing internal finite CDC read | FEC 648+k, last 2695 |
| RX CDC write | FEC 649+k, last 2696 |
| RX CDC read | core C(697,k), last 2871 |
| RX gearbox word capture | core C(698,k), last 2872 |

The unchanged 512-PMA wrapper from `79c582847` retains the trained starts
serializer FEC16/PHY40, deserializer PHY41/FEC64. Its measured FEC age is 151
FEC edges. These fixed reservations are never derived from observed arrival.
Endpoint epoch begins at core400. Frame j acceptance is
A=C(511,floor(613*j/487)); the actual TX6 endpoint writes at A-11, reads at
A-7 and publishes at A-1. With k=ceil(613*(j+1)/487)-1, RX endpoint capture is
core C(700,k), publication C(702,k). The actual gate verifies those edges.

`word_step=0` after the finite window permits the core to continue local work;
the full gate continues to core2900 without false missing-word faults.
The window holds 1,627 complete 613-bit frames plus 25 tail bits. The partial
tail must carry an idle frame; a compiler must not truncate a valid frame at
that boundary. The full workload has 300 slots (234 valid, 66 idle), with idle
padding for the remainder. No unbounded-window streaming claim is made.

`core_fec_calendar.py` models both real two-stage Gray observations. Actual
RTL tests check all 487 bits of 2,048 words in each direction for nine safe
profiles: FEC phase -8/0/+8 ticks crossed with relative FEC drift
-500/0/+500 ppm. Minimum observed read fill is 1, maximum conservative write
fill 10 and maximum actual occupancy 9. ±10,000 ppm profiles fault; native
write-drop and read-bit mutants fail the independent payload reference. These
finite numerical tests do not establish metastability MTBF or physical phase.

The stepped-gearbox component separately checks every bit and valid of 1,627
complete frames (997,351 bits), including idle payloads, through all pauses.
Bit corruption and missing word-valid are detected. The actual full gate
instantiates both native SRAM/CRC TX6/RX2 endpoints, stepped wrappers, both
external CDCs, rooted encoder/decoder, the real 544/512 PMA gearboxes and the
existing internal finite CDC. It checks 234 payloads at exact core edges,
2,048 actual decoded words and 2,048 internal CDC words. Valid flip, missing
word-valid, pre-FEC corruption, PHY-abort and actual Forney mutants fail their
required checks. No C arithmetic or substitute transport implements the DUT.

Application bandwidth before idle is 64*487/613*16/17 = 47.854141 bytes per
core cycle; 545/8 is only the logical flit-face peak including metadata.
The unified entry is `hgi_collective_core_fec_boundary_model()`.
Physical CDC roots/phase, MTBF, routed interfaces, recovery, whole G96
integration and token throughput remain unqualified. The nominal full gate
proves the declared trained phase; the explicit ±phase/drift scope above is
for the new CDC component, with the unchanged PMA profile qualified separately.
