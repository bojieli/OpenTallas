# HBM token compiler continuation, 2026-10-29 08:2x PDT

Current source/bind remains incomplete, so this packet does not claim G5 or a current token rate.
No inherited HBM token job remains live: previous SU PR0/1 and FUSED PRE/POST N1/N6 positive/mutant results
were already collected in TOK-HBM-9. No duplicate simulation was launched.

## Added lane compiler ABI (d17 candidate)

Input: intel2:/srv/opentallas-scratch2/claude/die-hbm-16/c25c_d17/die_plan.json + lane_add_report.json;
strict missing-bit census: intel1:/srv/opentallas-scratch2/claude/hbm-bind-2-1029/s1_unplanned_lanes.json.
Local read-only snapshot: /srv/opentallas-scratch/claude/codex-hbm-token-0830/inputs.

`tools/hbm_b2/lane_timing_contract.py` exports the existing LAT_* compiler ABI directly from
canonical `Plan.lane_latency`, preserving every station/boundary/clock-landing component.
All 60 added lanes match their reported cycles (2,5,6,7,8); no cycle values are invented.
D17 source reports 60 lanes/98,239 bits, 90 far pairs, and 14 failed attempts. Of the strict bind's
158 missing pairs, 54 have complete new aggregate capacity and 104 remain incomplete (81,148 bits).
New capacity excludes old lanes because the strict report already accounts for those lanes.

The partial-pair failure is concrete: NW/NE su30->su31 each need 3,356 bits; L166/L190 only build
1,678 bits, with the remaining 1,678 failed. Root<->hub splits are also incomplete. D17 is retained
as failed preparation evidence; the die owner is fixing reach/partial-capacity behavior in d18.
Mixed existing root/hub lane dates (2/13/15 or 2/13/30 cycles) cannot determine a missing signal's date.
The generated package is preparation only. The authoritative binder must assign actual signal bits to lanes,
then derive coherent delays and transport budgets from that assignment and the actual clock/reset table.

Checks on actual d17: both half-built SU pairs stay incomplete. Modified report cycles, bits and endpoint
controls all raise errors. This is the minimum relevant check; no new die gate or broad test sweep was added.

Reproduce:

```
python3 tools/hbm_b2/lane_timing_contract.py --plan INPUT/die_plan.json \
  --added INPUT/lane_add_report.json --unplanned INPUT/s1_unplanned_lanes.json \
  --out OUT/d17_lane_timing.json
```

## Six internal +1 station changes

The d15 station-resite report names NW `u_vmb_Q4.rr1|u_hb_dbk_Q` (2->3) and five NE Q7 bank->hub
outputs (`eg`, `pr`, `status`, `xq2_done`, `xq_done`, 5->6). The latter are parallel output classes,
not five serial pipeline nodes; `status` is observability. Actual source transport and VM return budgets
must be regenerated from these connections. The price script reports conditional fixed per-record
exposure scenarios, rather than asserting an unmeasured exact traversal. The six-serial-return case is
explicitly pessimistic and is not a source date or a universal bound on arbitrary repeated transfers.

`price_six_chains.py` uses the existing S2 scheduler on the full model tree and refuses the known sparse
DS fallback (expected 576,702.4 cycles). Current bind/clock/START/whole-source qualification remains with
HBM die/bind owners. No owner decision is needed by this packet.

## Actual source defeats the unimplemented NE two-slot assumption

`six_source_links.json` gives all six exact actual source port and sink bit ranges. They are DIRECT links
with zero intermediate source link registers. The NW row matches 257 source bits plus the plan's epoch;
the NE plan rows use serial_k=2 and bits_parallel=278/268/19/2/2 against actual 276/266/18/1/1 source bits.
The plan's serialization does not currently exist in that source. No VM_RT/CR_RT parameter can repair it alone.
The generic native_istations.py materializer handles bus OUT entries, and kit_istations.py's core classes are
S81-specific; neither materializes these HBM native core connections. Coverage owns an opt-in same-width
NW three-stage source materializer. NE needs k1 transport or an explicit retimed compiler/source two-slot contract.

Measured minimum source probe: actual ot_vms_bank_q0_faces_body RG5/WG2/EG_WIDE1, real existing SRAM model,
same body SHA b069136bfe9572147c212d2c9ba2a11ad162663f777b8a52829e9327b7483a17 as the selected source manifest.
At 833 ps, 24 valid legal mirror writes on 24 consecutive edges yield 24 valid egress outputs on consecutive
edges, every distinct 256-bit payload correct, status=0. Therefore a two-edge serializer cannot transparently
carry the existing legal source stream. This is a source capacity failure, not permission to drop events or
assume unused mirror traffic. The production compiler must either prove/establish at least II2 for each such
link (including output pulses and response dates), or the plan must retain full-width links.

Proof: intel2 ot-run unit oth-ubuntu-2189907-1793288032, ne_bank_eg_ii1.log, tb_ne_bank_eg_ii1.sv.
Initial elaboration unit2150410 exit2 lacked ot_vms_ce_counter_pipe dependency; adding the exact existing module
fixed it. The actual bank/SRAM RTL was unchanged. Run with iverilog -g2012 on the bench, body,
ot_vms_ce_counter_pipe.sv and ot_sram_1r1w_1024x256_m2_r2c2.v, then vvp. No new heavy job remains live.

## Source-directed VMS plan correction

`tools/hbm_b2/native_vms_station_map.py` prepares a narrow VMS/bank plan correction from actual_hub_r2's
actual port directions and every bit mapping. It preserves all other plan fields and station rows.
On d17/d18 there are 256 actual links (four source roles, eight banks each, eight ports each).
The old plan has 120 VMS/bank station rows per hub, all with stale `u_hb_vms_Q` aliases and original
North bank names, with no South `_mu1` bank station row. The companion source map explicitly retains all
128 missing South-role links; it does not copy their North geometry or claim the plan is complete.

For the 128 North-role links, select the row with the actual driver direction, drop 112 redundant/reversed
rows, and replace aliases with the exact `__q1` instance selected by the source bit identity. Five bank-6
outputs per hub have only the reverse old row, so their path is reversed while preserving its count.
The optional `--full-width` form uses exactly the source's 276/266/18/1/etc. bits, removes `serial_k`,
`bits_parallel` and `r11_cc_serial`, and introduces no epoch bit. Every source/destination bit pair is
preserved in lossless contiguous runs. The source data/control semantics and arithmetic are unchanged.

D17 candidate VMS station wire*stage count (an inventory, not a cut/routing gate): NW 108,458 -> 87,016,
NE 110,100 -> 89,782. Actual pin coordinates and clock/reset/runtime budgets must be recomposed by the die owner;
the selected rows are explicitly GEOMETRY_UNQUALIFIED. The full candidate plan remains in scratch:
`/srv/opentallas-scratch/claude/codex-hbm-token-0830/vms_native_fullwidth_d18.json`.
The report `vms_native_station_map_d18.json` is the small source/materializer input, not an executable programme.

Controls: exact all-256 bit map reconstruction passes; malformed width and duplicated-bit controls refuse.
All 128 prepared North links are full-width and select q1; all South links remain MISSING. The candidate
builder leaves its input plan unchanged. This prepares the source correction; it is not a new die check.

## D18 added lanes

D18 fixes canonical reach and no longer publishes partial failed pairs. Exact compiler ABI regeneration
retains d17 failed evidence: 60 new lanes / 95,311 bits; 55 strict missing pairs have complete new capacity,
103 remain incomplete, 84,076 bits still uncovered. All 60 lane cycle values match canonical Plan.lane_latency.
Both exact packages remain preparation only pending the binder's bit map and clock/reset dates.

## Intrinsic RR1 and materializer input

The same actual bank fixture now performs one real port-1 SRAM read of the last mirror-written word.
Unit intel2 oth-ubuntu-2548544-1793288677 PASS: bank samples request at edge62; rr1 valid/data24
is presented after NBA at edge68; a downstream consumer samples it at edge69. All 24 egress checks
also remain correct and status=0. Source code in ot_hgi_dma_back_static_vp4_banks.sv:93-100 defines
RR_RT as request LAUNCH edge to reply LAUNCH edge. The actual controller registers rq_v at edge61,
so the measured bank request edge62 corresponds to rr launch68 minus rq launch61 = 7 edges.
Consumer capture is 8 edges after the producer launch. Its expected-mask pipeline and response pin
capture both align at edge69; these two conventions must not be interchanged. Coverage owns composing
all 16 exact DMA source slices to the current RR_RT80 budget, including common return dates.

`native_vms_station_map.py --chains-out FILE` exports a component-only direct_stations contract:
128 North-role links, 176,798 state bits of which 3,074 are explicit control bits. The source offset and
width mean a selected slice, e.g. NE bank7 pq is source bk_pq[2279:1995] (285 bits) in a 2,280-bit port.
Bank output clocks use their actual face entries; the VMS wrapper's selected nominal clock and bank
clock resolve to the same source bit. Existing reset expressions are retained and remain unqualified
for die delivery. Valid bits/status receive reset; data bits do not. The recipe does not adopt runtime
source, manufacture South geometry, or solve unequal pipeline/calendar dates. Coverage owns materializing
these source-preparation recipes with its existing guarded direct_stations primitive.

## Old regular VM cannot hold the unchanged a122 programme

`tools/hbm_next/vm_capacity_witness.py` reads the actual immutable a1228bb5... binary, not its allocator's
reserved extents. The SU chain at records1470/1472/1473 (offsets199776/200128/200304) forces four distinct live
input sets: current A122880 + current B122880 + deferred C122880 + deferred A30720 = **399360 words**.
Current R feeds bridge A; bridge O feeds the future B, so that future operation cannot run before the current
operation. No intervening operation writes either deferred input. These exact word sets are disjoint, including
the strided tail and broadcast semantics. Old regular VM has262144 words: **137216 words short**, 52.34% above
capacity. This is a concrete lower bound under the unchanged programme/row-array lifetime contract, not a claim
that399360 is its full peak. It rules out fixed address relocation; it does not rule out a separately compiled
streaming/rescheduled/finite-phase design with explicit transfers and cost.

The earlier producer-aligned emitter.json reports C4 peak452534 at segment14 and total allocated need506112;
those numbers describe its pre-lowering schedule and are context only. They were not substituted for the actual
binary witness. Unsafe-alias, broken-dependency and intervening-overwrite controls all refuse the witness.

Reproduce using the pinned P3 compiler tools (decoder from42d0caba4) and the retained a122 image:

```
python3 tools/hbm_next/vm_capacity_witness.py --image candidate_mtp_N6_a122.hgi1r \
  --compiler-tools PINNED_P3_REPO/tools --out capacity.json
```

## Existing grown VM candidates and the adoption work

The clean source package is already on main as **d0b824a772f720861a9c4fcb9eda9392a7d3bf44**. Historical
source branch codex/hbm-vm-capacity-1029@bf5060667 includes the same blobs plus its publication receipt; use the
clean main package. It remains default-off/unselected and does not qualify the current old-bank bind.

- Native bank: rtl/hbm_accel/generic/vm/static/faces_q0_r2048/ (body/core/face/oneclk wrappers). Keep regular sector
  high-row bit15 distinct from mirror bit16. Address fields are17-sector bits; banklocal row is12bits. No truncation
  or old mirror reinterpretation. Native input widths: rq18,wq/dq/kq282,xq/xq2/eg277,pq286; rr257/pr266/status18 stay.
- Physical cost: 32banks need four SRAMs each (128 vs96), adding32 actual1024x256 macros and one high-regular macro
  per bank. Macro3 clock/PG/lot/outline/pins and current staged transport must be composed in the single die event.
  Existing component proof preserves read7/write4,0 added steady cycles. It has no physical signoff.
- `tools/hbm_static/vm_r2048/caller_packet.py` lifts the exact32 callers. A legacy adapter preserves low regular and
  old mirror addressability; **it cannot reach upper regular storage**. Every runtime producer/consumer that touches
  relocated high storage needs its real17-bit native packet/address path, including mutable writes; widening banks
  plus legacy lifts alone does not execute a122.
- INDEX native reader/collar/share candidates: rtl/hbm_next/idx/ot_hnx_idx_vm*_r2048.sv,
  rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256r_r2048.sv and the corresponding static_r2048
  share source (exact paths in d0b824's file list). `index_packet.py`/`native_idx_config.py` produce four role-local
  fields (weight/query sector and row strides),289 configbits/+2F20frames,144-bit request bundles,2056 response bits.
  Their current source proposal explicitly selects SINGLE_ROW_ONLY=1. Actual a122 has active N6 INDEX records, so
  **multirow control/calendar/publication is an additional required event**; do not claim the single-row package
  covers those records. Actual queryA SID2 / weightB SID0 still need legitimate role-local publication/replication.
- Existing F20 boot publisher `ot_vms_f20_boot_publish_r2048.sv` + `publish_packet.py`/`publish_frames.py`: target120
  (0x78), header0xF00,payload0xF01,19-bit regular WORD address,one header per contiguousregion and one payload per
  eightwords, five drain edges after bank sample. It rejects collisions/active INDEX/unconfigured/early commit.
  Proof unit3179360 exercises real four-SRAM low/high readback plus four source mutants. This boot-only publisher
  is not a runtime computed-A replication mechanism; that remains a source/dataflow obligation.

Current HBM-BIND explicitly retained hfd_vms_bank_native_q0_faces (old16-bit sectors). Choosing a complete grown
source event or a priced finite-phase/rescheduling source is necessary; silently rebasing high bits into mirror
storage or importing a legacy-only lift would lose the actual programme semantics.
