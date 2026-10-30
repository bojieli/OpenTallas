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

Native command-port integration follow-up: actual ot_hgi_dma_back_cp_collar
MODE1CW308/RELF2 with its2x128x256 SRAM table now drives the genuine provider.
Only decoded nativecfg/descriptor/launch ports drive commands;227 records and
countersteps are not external inputs. At exact833ps the42nativecommands,
2688packets,21504words and3ownership epochs PASS, everystep→packet8edges.
Actual monitored edges:firststep285,laststep4720,firstpacket293,lastpacket4728.
Insideeachrun count8packets issue everyedge; this conservative literal schedule
starts64packet runs92edges apart. Wrongcmdepoch andearlydrain controls fault.
See cp_receipt.json/cp_baseline.log and run_cp_provider_fixture.py.

Production target106 already belongs to NW BACK. Its value here is a standalone
fixture strap, not ownership of a new FRONT target or a duplicate production
collar. Actualselectedsource will need explicit shared-collar LOAD/STORE
direction dispatch or a separately allocated target, nativearbitraryquad/bankDQ
routing, reservedslot6 and realbankdone. CPfront currently counts emittedpacket
maskbits at its drain deadline; it does not observe physical VMbankcommit.
The fixture is one retained window from N6MTPVERIFY, repeated in3ownership
epochs, not3complete MTPsteps and not3ARtokens. No tokenrate is inferred.

Peer review scope: these actual caller vectors use normative U32 5→5 only. Destination-format guard correction in the provider counter is separately owned by binder and remains required for other or malformed formats. The old broad-format toy vectors are not this proof. Release remains a caller obligation after the actual last consumer; the wrapper does not implement a complete inflight-packet or physical VMdone release guard.

Input programme scope is explicitly N=6 MTP VERIFY with data-dependent ACCEPT3913/TOKX3914 output count (TOKX A.n7). These bounded copies repeat three ownership epochs; they execute neither three full verify steps nor three AR tokens. Fixture generators and receipts now state that scope. Accepted token rates require actual native ACCEPT/TOKX observations plus draft/seed costs; no fixed acceptance gamma is assumed.
