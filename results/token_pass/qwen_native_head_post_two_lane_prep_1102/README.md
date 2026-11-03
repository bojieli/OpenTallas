This is source PREP for the actual selected native S8 numerical station. No build
or simulation has run. It reuses one real `qfd_dv_s8_station_tail1_nb0` sender,
one real `qfd_dv_s8_station_tail1` receiver and the real shared BTAB across eight
sequential two-lane contexts, with reset between contexts. The two tested row
blocks cover rows0..127 and18944..18991. The fixture covers176 scaled scalar row values;
it has no simultaneous sixteen-lane assembly, AMAX or ROOT claim.

The L6 words are explicitly REFERENCE inputs from genuine weights and canonical
H4096. Actual TG4 output capture crosschecks the first four groups independently;
the remaining L6 values are numerical component-boundary inputs, not executed
full matrix results. Exact selected brackets are independently recorded in the
adjacent `qwen_native_head_post_reference_1102/selected_post_port_map.json`.

The bench clock is exactly833ps with1fs precision. This is an explicit nominal
component clock premise. The selected boundtop uses distinct region clocks;
this fixture does not certify their provider phases, START epochs or mesochronous
count origins. It directly connects actual sender registered `nb_od/nb_oc` to
actual receiver `nb_d_p/nb_c_p`, retaining PIN_IN1. With matching own-input
publication, own9 writes at E, sender output publishes at E, receiver PIN captures
at E+1, and native L9 consumes at E+2 with positive lead. Native h9 SRAM bypass
and prefetch are retained. No artificial neighbor result or fitted delay exists.

Near inputs are published14component edges before matching far inputs, matching
the actual SKEW14 SRAM/control rings. Configuration is excluded from all data
valids; cfg payload/control pipeline settles before the first near publication.
The input boundary origin is the first near valid presentation before capture.
The bench records first/last neighbor publication, BTAB read/address, and result
valid/index/last ages relative to that origin. A finite1000cycle per-context
watchdog covers the64prefix beats,14edge near/far gap and native drain margin.
Native faults, exact counts, addresses and all176 unchanged scaled scalar values gate.

Potential same-ELF causal controls are `CONTROL=oldKC1`, `wrongBTAB` (first genuine
BF16 scale LSB flip), and `shiftedFar` (one-edge invalid near/far pairing). Their
expected mechanism and fail verdicts need review before execution. Source-only
preparation does not establish that the controls fail.
