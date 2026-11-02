# Current StoreA stage-home gaps and exact request-side lineage

This resolves the current 16-type composite's available homes without inventing native pins or FF placement. No RTL or physical job is changed. The local clone model contains 8,768 independent final-stage *field* targets in four eight-macro regions; strict source copies cost 8,800 FF because each stage-valid output needs two source FF plus an AND. These are not simultaneous placements or Q/D pin witnesses. The conditional local source model preserves three existing logical edges and proposes +0 local cycles, with proof and all input D/clock/reset physical joins explicitly unqualified.

The current B113 allocation contains an old 7,534-pin `ot_hgi_sfu_core_split3__opstore_a` profile, while the actual SOURCE13 StoreA master is `ot_hnx_sfu_store_a__da81d76763c9` with 6,040 ABI bits. None of the current old StoreA pin names match the SOURCE13 `store0_sw_d/addr/mask` or `cmd0_Q` fields. The old CTL profile has 11,819 pins and several clock families, with no SOURCE13 `u_core_procdff_66926__D` or `u_core_u_vm__stage*` pin names; the actual CTL closure has 11,810 ABI bits and one exported clock. Their allocation rectangles are available context, not source-compatible native pin contracts.

L54/L127 have declared B113 input and SU00 output windows, but only nominal generator boundary targets, with no current source-mapped/fixed FF home. Even an optimistic entire input-window rectangle is at least 1,214.328/1,205.208 µm from the old CTL allocation, exceeding two remaining 405 µm registered segments after the current input pad. A new native split must explicitly allocate staged D interfaces; it cannot borrow the old CTL pin profile. The three SOURCE13 `xi_…66926_D__{0,1,2}` B113 inputs and corresponding SU11/SU20/SU31 `xo_…c_rr` outputs have no exact named current type bus/window/FT witness. Any binder alias or independently priced transport requires its own actual source/pin/stage witness.

The actual source SFU reuse leaves do have current allocated bodies, but no c_rr LEF pin or mapped payload FF home. Retaining these bodies and the StoreA allocation gives optimistic source-body-to-destination-body L1 bounds, identical on both sides:

| Quarter | Minimum body distance | Minimum 405 µm spatial segments |
|---|---:|---:|
| Q0 / SU00 | 587.520 µm | 2 |
| Q1 / SU11 | 9,797.760 µm | 25 |
| Q2 / SU20 | 6,445.440 µm | 16 |
| Q3 / SU31 | 15,059.520 µm | 38 |

These are lower bounds with free choice of both endpoints inside their entire bodies. They exclude a retained-home SAME-three-edge physical return path for Q1/Q2/Q3. They are **not automatically added cycles**: global return/request transport, any relocation of existing stages and VM/compiler date allocation are separately owned by the coordinator. Local private-copy equality would not close those global links.

The exact SOURCE13 request-side trace is also retained, independently of READ_RETURN88/WRITE_RETURN85 pricing. CTL `g_compose_m21_q[135:0]` captures the VM's read-request pack and `g_compose_m22_q[2247:0]` captures four 562-bit VM write packets; both update every clock edge and use generated region-2 reset. Each preceding VM `write_q` is resetless, updating zero plus selected 281-bit packets on every edge. Its rounding/data/control cone is real and not free.

- Q0 read34 + write562 share source L47 payload596, while the current plan declares664. Same bus name grants no padding or functional alias.
- Q1 and Q3 each use separate direct read34/write562 xo/xi interfaces absent by exact name from the current type buses/FT slots.
- Q2 uses the existing named L731 path B113 → B012 → B002 → SU20. Frozen SOURCE13 has six W596 FF stages in B012, matching plan six; B002 has nine W596 stages while the current plan has ten. The proposed coherent native event must show this reconciled. A plan that already prices ten must not be charged that difference a second time.

`request_lineage.json` records all eight quarter instances / sixteen read/write paths, exact top wires, payload slices, boundary captures and each intermediate source FT cell. Payload FF are resetless and epoch companions have their own reset. The source facts are preserved without deriving or duplicating global VM dates, inserting stages, claiming current clocks/pins, or activating a source/default event.
