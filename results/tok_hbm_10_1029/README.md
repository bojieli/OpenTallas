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
