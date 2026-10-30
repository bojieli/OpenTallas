# Genuine native LOAD provider mechanism fixture

This main-based change supplies a real caller fixture for binder candidate
5fe9b74a9 (ot_hbm_static_load_provider_quad). It instantiates the compact227
count8 counter, combinational62bit mapper, eight actual NPC2 landing leaves,
registered packet merge and original128x256 SRAM models. There is no behavioral
provider stub. The source candidate depends on the binder's component closure;
that RTL is owned and reviewed separately, not copied into this fixture commit.

Actual retained programme windowbundle990 supplies14 effective227 runs covering
896 U32sector packets and all4 destinationVMquads. The fixture explicitly puts
those same localwindow offsets on stack2 to exercise the selected provider
mechanism. This is a test namespace, not a production rebase or reservation.
It executes3 ownership epochs, reuses buffer0 and then uses buffer1. External
pin bytes distinguish phase,sourceleaf,PCgroup,slot andword. Those bytes are
opaque canonicalU32 data, not checkpoint-derived arithmetic answers. The exact
native VM packet stream is compared; physical VMbank slot6/commit is outside
this packet-boundary mechanism. Perstep metadata and all8leaf release lifecycle
are exercised; wrongstep epoch and omitted release controls must fail.

The caller's body/drain/STORE anchors and production addresses remain in the
reviewed source-only programme; this bounded fixture does not install it.
PHY responses begin at actual ownedleaf fill pins, so native external PHY
service/calendar latency is also outside this component measurement.

To regenerate fixtures only:
python3 results/tok_hbm_provider_1030/gen_fixture.py --out OWNED_SCRATCH

To compile and run (through ot-run, with the binder dependency available):
python3 results/tok_hbm_provider_1030/run_provider_fixture.py --out OWNED_SCRATCH \
 --provider-dir BINDER_RESULTS/static_load

The helper defaults to canonical rtl/hbm_accel/loader/service_native/split
provider sources, with the repository binder result directory retained as a
historical fallback until that separately reviewed source closure is present. No heavy whole-programme rerun
is needed. Retained actual_window_runs.json validates each selected run against
the checked-in resident source manifest before generating227 descriptors.

Actual integrated baseline PASS at exact833ps clock (416/417ps halfedges,
1ps precision):42descriptors/2688packets/21504words/3epochs, all4VMquads.
Measured datedstep→nativepacket latency8edges=6664ps on everypacket.
Wrongstep epoch failsedge147; omittedall8release failsedge1104. Same models
and data at the earlier2ns clock also pass; those logs are retained separately
and do not establish production-clock behavior. No physical signoff is claimed.

Counter emits one count8packet/cycle inside eachrun with one descriptor setup
nonissueedge;14runs/896steps use910issue/setupedges per epoch. receipt.json
states first/last packet dates, timestamp conversion and deterministic TB date
derivation. Raw records are driven by TB desc_v_i/desc_i, not a host target.
The next concrete integration is binder's unchanged native
ot_hgi_dma_back_cp_collar MODE1CW308:cmd{mv227,buffer1,epoch16,issue32,drain32},
actual cfg/descriptor/launch ports and fixed dates. Our14run fixture fits its
128-entry table (two128x256 macros); full95313run programme capacity remains
unqualified. Binder owns that RTL follow-up, so no duplicate command interface
or invented MODE1 address loop is introduced here.
