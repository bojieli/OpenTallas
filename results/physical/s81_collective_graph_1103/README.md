# Source-pinned collective ownership graph

The audited native parent is `dsfd_sp_collective_static_c` at `2eb33e9a8e8046d4f579fc1395e0ac6038a11341`. Its slab still instantiates **one-clock** `s81_static_calendar_controller`. The separate calendar7 candidate is not integrated into this parent. The delivered slab has 29 clock roots: five control, eight transport, and sixteen HC roots. This is a clock ownership decomposition, not evidence of 29 hardened, placed constituents.

`graph.json` contains SHA256 values for the inspected source files, exact ANSI module port declarations, parsed module instance connections, the 112 signal hyperedges at the slab boundary, and all 29 ownership entries. Expressions preserve RTL slices. Reproduce it with:

```sh
python3 tools/s81_static_collective/physical_graph.py --source 2eb33e9a8 --out results/physical/s81_collective_graph_1103
```

The parser is a structural source index. It does not elaborate generate loops, synthesize storage, resolve wildcard connections, determine physical pin coordinates, or establish timing closure. Generate ownership and slices below come directly from the source. Pin-bit totals in the JSON are declared RTL port bits, including clocks/reset and outputs; they are not physical cut pin counts.

## Missing physical partitions

| Root | Actual same-root ownership | Missing physical boundary |
|---|---|---|
| control0 | Current calendar/three ROMs; wrapper `reset_q`; slab reset synchronizer | Complete root cut and current calendar integration. Calendar7 cannot silently substitute for this source. |
| control1 | TP4 core; wrapper rank capture/configuration faults; remote-rank combinational mapping; reset | Core-only view would omit actual wrapper logic. |
| control2 | VMB `PINCAP=1`; raw VM rows `REGISTER_VM_WRITES=0`; slab `status_q`; reset | VMB alone excludes raw buffers, status register and reset. |
| control3 | Static pass adapter; host completion queue `DEPTH=16`; reset | Adapter alone excludes the queue. |
| control4 | Reducer identity pipeline/fault; assembler seen bitmap/tag/output metadata/fault; write/emit qualification; reset | Metadata is distributed across reducer and assembler modules. No extracted combined metadata leaf exists in this source. |
| lane0..2 | Dynamic FMT1 codec and gearbox; each lane reset synchronizer; forwarded-clock buffer | Native lane module exists, but its reset and clock-buffer integration still needs ownership/boundary binding. |
| lane3..7 | Raw FMT1 codec and gearbox; each lane reset synchronizer; forwarded-clock buffer | Same missing physical integration. |
| hc0..15 | Scalar reduction tree, local reset, and scalar assembly/output storage | Reducer and assembler are separate source instances. A coherent same-root hard leaf must own both, or a physical parent must place both and price their internal crossing. |

For each HC root `g`, the arithmetic input is exactly `{gather_data[1536+32g+:32], gather_data[1024+32g+:32], gather_data[512+32g+:32], gather_data[32g+:32]}`. The reducer has three FP32 adders in the fixed pairwise tree. Its `word_data[32g+:32]` feeds the matching assembler. That assembler owns 512 assembly bits and 512 output bits. Its output bit mapping is `t_hc_y[512w+32g+:32] = lane_row[32w+:32]` for `w=0..15`. These are sixteen interleaved lanes of a common 8192-bit row; they are not sixteen contiguous 512-bit output slices.

The scalar reducer declares 165 RTL port bits and scalar assembler 551. Peer lane and raw lane declare 2179 and 2166 bits respectively. VMB declares 6614 bits. Adding these values would double-count internal reducer/assembler data and would omit the extra logic/control cuts. No combined physical cut pin count is claimed.

## Incident neighbors that placement must preserve

The machine-readable slab hyperedges preserve every explicit slab instance connection, including shared source buses. The following root-level relations explain the placement pressure:

* control0 calendar drives control1 issue/identity/commit, peer-lane beat schedules, control2 read/raw/write controls, control3 channel schedules, raw dispatch qualification and host queue slot selection, pass-lane schedules, and control4 HC reduce/assemble/emit controls. HC slot qualification also reaches all sixteen arithmetic leaves. Calendar receives the aggregate datapath fault.
* control1 TP4 core broadcasts the 569-bit TX record to all three peer lanes. Each peer lane returns its own 569-bit record and valid through the rank-dependent map. Core gather outputs are 2048 data bits, four write enables, 60 row bits and 49 identity bits; they reach the VM boundary, HC arithmetic leaves, and HC metadata as specified by their individual ports.
* control2 raw rows sends/receives a 552-bit raw payload plus valid/last/channel through the control3 adapter. VMB consumes gather data, reduced data/identity, raw write sources, PHY fault/live/valid inputs and host RX status. It drives external VM `t_crq[14:0]` and `t_vm[2203:0]`. The external `f_crs[512:0]` also reaches the TP4 source and raw capture buffer. Slab status collects faults from all datapath functions and the calendar status on control2.
* control3 adapter exchanges 552-bit payloads and valid/last with each of the five pass lanes. External WFC buses have 514 bits in each direction. Host ingress is 77 bits into the completion queue, with completion/status plus valid feeding the adapter; host RX is 516 internal bits and 515 exposed bits. All eight transport lanes participate in aggregate transport/channel faults, even though these OR reductions introduce no additional clock root.
* Each transport lane has 512 data bits and beat-valid in each physical direction. The slab also receives separate fault and live bits per lane. Physical order is W0,W1,W2,W3,E0,E1,E2,E3; lanes0..2 are rank XOR1/2/3, lanes3..7 are pass0..4. The wrapper also forwards each lane clock through its own `ot_s81ph_ckbuf`.
* Each HC arithmetic leaf receives 128 gather bits and qualified slot/reset, returns 32 reduced bits plus valid/error, and shares its clock with the matching assembly leaf. Metadata reduces the sixteen valid/error results and supplies assembly write-good, emit-good and destination index to all sixteen assembly leaves. Word/tag/sequence/last metadata and write/emit validation must remain coordinated with these leaves. HC row-valid/tag come from metadata; row-data comes from the sixteen assembly leaves.
* The wrapper clock/reset service receives refclk/por and exports three PLL clocks and three reset outputs. Wrapper reset qualification is on control0 before slab root synchronizers. Lane synchronizers receive their respective control-domain reset; HC arithmetic synchronizers receive control4 reset. Assembly scalar storage has no reset port. These relationships must be included when a physical root cut is extracted.

No placement can discard the shared wide buses, HC interleaving, aggregate fault/status fan-in or reset/clock service edges merely because a primary interface faces another neighbor.

## Physical view evidence and geometric gate

The pinned tree contains **zero committed LEFs** named for the ten required native module masters listed in `physical_view_evidence`. A VMB kit exists under `physical/ref_tile/s81coll_vm_boundary`; its job is a configuration/template and does not establish a current immutable placed view. Its historical source/geometry prose is not proof for the present `PINCAP=1` source. The parent's ongoing VMB and calendar7 jobs are independent work and were not duplicated here.

The supporting clock service does have `physical/s81_ph_views/closed/dsfd_coll_ck/dsfd_coll_ck.lef`, a real 216 by 216 outline. The four source files in its archived route specification (`dsfd_coll_ck.sv`, `ot_s81ph_coll_rstc.sv`, `ot_s81_pll_bb.sv`, `ot_s81ph_ckbuf.sv`) are unchanged between archived source `752a48488384dbe9c95a72c084bc24e0ac800a17` and this audit source. Its abstract explicitly describes SS setup / FF hold and **no TT verdict**, so source identity alone does not establish the requested full signoff set.

The old 1727.976 by 2721.576 slab rectangle remains a reservation. Actual required area, 29 root-cut outlines, placed homes and physical pin coordinates are unknown and represented by nulls. There is no defensible numerical packing candidate yet. The source supports a structural adjacency candidate: pair each HC arithmetic leaf with its own assembly leaf, keep all sixteen close to the shared TP4 gather and HC metadata, keep VMB/raw-row control near the external VM face, keep host queue with adapter, and align each codec/gearbox lane with its actual W/E PHY face. This is an adjacency requirement, not an authorized geometric placement or a road grant.

Before a coherent die grant, extract the missing cuts without changing functional edge counts, synthesize their complete same-root ownership, export source/parameter-bound outlines and pins, then pack all cuts plus clock/reset service with every incident neighbor priced. The historical 7431b0d19 census cannot supply these missing measurements.
