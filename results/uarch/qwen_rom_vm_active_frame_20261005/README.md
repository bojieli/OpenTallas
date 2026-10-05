# ROM active-frame candidate: source helper and pre-RTL price

Boole owns only `tools/qwen_rom_vm_active_frame.py` and this namespace.
Arendt owns the actual provider, source wrapper and schedule. Maxwell owns
unified composition, candidate selection and floorplan admission. Goodall owns
clocks/crossings. All hardware options are OFF; no RTL/build/inference was added.

The helper consumes Arendt's `compile_frame` input ABI and checks the actual
59492 core / 3d5 top / cba4 PART2 array / 2918 matvec / 3f594 args source pins.
`active_frame(reads, writes)` accepts one captured logical edge in original
source order. Disabled pins are ignored; active bounds and seat order retain
the existing guard. It emits every enabled scalar store in its original order,
including stores later overwritten on that same edge. Native ME/MX/collective
vector groups keep their actual masks and payload lane order. SU and reducer
stores remain in their original scalar positions. A native group spanning
multiple words cannot use the priced selector and must retain the old walker.

`compare_edge` compares original old reads, ordered emitted stores, final lane
winners and the actual aligned-window lane lookup/native masked-group merge
using opaque labels. It performs no arithmetic or model inference. It checks
the existing minimal component's five edges at 4096/4160/4224, same-edge
aliases across every writer family, duplicate reads, inactive garbage pins,
and a fresh next-edge read. Wrong order, out-of-range active addresses and
nonboolean enable inputs reject. The actual compiled HEAD PC3 and L20 W1 PC20
first k0/j0/round0 addresses also pass this logical-edge check. This is not a
native-RTL timing/ACK/numerical qualification or a later-phase trace.

## Priced candidates (all values below are ESTIMATE)

| First address obligation | Existing source walker | Active native-writer selector only | Selector plus same-edge broadcast |
|---|---:|---:|---:|
| HEAD PC3 | 3829 edges | 2964 edges | 5254 edges: reject broadcast |
| L20 W1 PC20 | 15829 edges | 15307 edges | 7037 edges: candidate |

W1 has 2048 requests, 128 distinct scalar addresses with fanout16 and64 aligned
windows. Existing walker misses1024 times. W1 emits768 scalars in48 native
masked ME vectors; all48 words are bank3/group2. The active selector traverses
115 possible native source groups (48 ME +1 MX +64 SU +1 reducer +1 collective),
using seven registered selection levels and one active group each seven edges,
including an extra completion traversal. It does not assume an II1 encoder.
The original865-seat encoded frame stays intact; no frame-storage saving is
claimed. Native vector extraction avoids a scalar-seat scan.

Broadcast remains within ONE immutable captured logical edge. A static,
source-phase alias table must match actual enabled seats and addresses before
any physical command; mismatch retains the original walker. No cache/lease or
cross-edge reuse exists. The price charges two validation edges per active read
plus drain; checked CAP1 reads retain11 edges each, then six registered scalar
selection levels and one matched destination capture edge per window. All
read dispatch drains before the next service command; all reads precede writes.
Writes retain30 edges per masked flush, including real postverification.
No overlapping read/write, credit reuse or early source release is assumed.

W1 candidate saves8792 service edges (55.54% of this static frame), with
**5.267571 mm2 incremental 50%-placement ESTIMATE** before clock, wire, fanout
buffers, PG and actual corridor. This large positive price includes coded
alias tables, address-validation cuts, bitmap/control, all writer/read-selector
pipeline bits and unchanged protection-codec proxies. Original224712 encoded
frame bits remain charged separately. Active-writer-only selection is priced
at0.668021 mm2 incremental placement. Generic HEAD broadcast is estimated at
44.847740 mm2 and slower, so is explicitly unsuitable. These are not mapped
areas, certified cycle counts, a 331us-segment reprice or per-user/token gains.

`price(plan)` exposes individual raw/coded bits, codec replicas, compare/mux
area, fanout and service terms for Maxwell registration. Stage plans are
ESTIMATE until minimum RTL service/loaded-clock measurement. SS60/FF25 and
actual source clocks stay unchanged. Home/corridor/clock costs remain unknown;
physical admission and adoption are FALSE. Use a candidate only after Maxwell
selects/registers it and Arendt supplies the actual immutable capture hook.

## Existing macro service replication: option only

The unchanged checked provider has one CAP1 state machine and rejects
multibank writes and read/write overlap. Raw full16 storage has256 existing
1R1W data macros (four128-bit columns per bank/group) and32 check macros.
Read group/row commands are shared across16groups within each bank. Each
check macro serves a pair of banks in one group with ONE address port.
There are no four free checked-service ports.

A per-group partition could reuse these exact macros but requires15 additional
protected controllers, codec replicas, request demux/return arbitration,
coded ownership/debt, real ACK retention and new clock/load/floorplan pricing.
The result includes positive controller-state/codec floors; total area and
service latency remain unqualified. Owner approval is required before any
replica RTL. It cannot parallelize this W1 output: all48 writes use the SAME
bank3/group2 data and check macros. No W1 replica gain is credited.

## Reproduce the small source-helper calculation

```
python3 tools/qwen_rom_vm_active_frame.py \
  --out results/uarch/qwen_rom_vm_active_frame_20261005
```

`summary.json` contains prices and exact-check summary; `model.json` retains
actual native address/alias/mask plans and source pins. These small metadata
calculations are the only local work; no whole-array job, HDL build, library,
new provider, HBM transfer, source padding or oracle input was used.
