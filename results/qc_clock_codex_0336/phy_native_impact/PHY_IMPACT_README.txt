READ-ONLY QC native PHY entry/slot proposal. No source, plan, RTL or route edits.

{
 "scope": "READ-ONLY impact/proposal, no plan/source/RTL changes or new route. Native hard views selected from the exact currently-declared module/lib directory, not substituted nface variants.",
 "target_construction": "target2 uses die_trial.abstract_lef per type; synthetic slot SIZE, plan face pins and synthetic M7 clock/reset taps. No canonical native PHY LEF imported. Slot/body offset and leaf pin routing are absent.",
 "slot_transform_proposal": "Preserve current outer slot/origin/port fields. Declare inner native body origin[0,0], native SIZE, R0, LEF/lib source. Transform inner body corners through parent slot orientation; place native leaf bbox at their minimum, not naively at parent origin under MX/MY. Only after review realize explicit wire-only adapter from native FDI/reset pins to current outer face/epoch pins. Existing registered-hard RTL strips incoming epoch and drives outgoing epoch from delivered reset, no new flops.",
 "clock_proposal": "Bare hard PHY clock access must identify actual native M5 clk rectangle plus source hash, with exact slot/body transform. Any outer M7 clock port/via adapter requires explicit physical wiring; changing clock.tap alone is insufficient because clock_pins still snaps to partition tracks and abstract_lef fabricates M7 pin geometry. coll_ucie is mixed soft logic plus native PHY: preserve top/grid clocks separately, replace only native core entry and remove/reassign glue grid taps/stations inside PHY body before native build.",
 "minimal_guards": [
  "All native PHY cells/clock drivers/START/reset infrastructure must be outside full native body+declaredhalo; no interior die-clock island is opened by inherited contents-only metadata.",
  "Native LEF body SIZE/origin/orient and slot transform must match actual placed bbox; MX body-offset4.104um for current SerDes cannot be dropped.",
  "Native clk/rst terminal rect/layer must match exact source LEF; no lattice snapping or fabricated clock-center claims.",
  "Every current outer payload/epoch port needs exact native-bit/constant wire mapping; all real native PHY pins remain accessible with no synthetic undeclared native epoch pins.",
  "Do not replace coll_ucie soft wrapper by bare PHY; retain native core/body and soft logic/clock roles explicitly.",
  "Physical provider/source promotion waits for reviewed body exclusions+nativeentry+adapter recipe; current graph remains INFRA coupon."
 ]
}

Registered-hard-pin location proxy: native boundary pin is the declared boundary register interface (hard_pinreg). No native internal FF coordinates are published, so this is not an actual routed-cell R2 measurement. The Manhattan adapter wire is a physical lower bound before internal pin-to-FF wiring; a synthetic abstract cannot claim the existing R2<=30um budget for displaced faces.

{
 "phy_serdes": {
  "all_payload": {
   "bits": 1197,
   "min_um": 4.373999999999796,
   "median_um": 160.03799999999978,
   "p90_um": 237.03799999999978,
   "max_um": 287.3579999999997,
   "over30": 1037,
   "over405": 0
  },
  "buses": {
   "tx_flit": {
    "bits": 597,
    "min_um": 160.03799999999978,
    "median_um": 208.0379999999999,
    "p90_um": 246.34999999999968,
    "max_um": 255.94999999999982,
    "over30": 597,
    "over405": 0
   },
   "tx_v": {
    "bits": 1,
    "min_um": 287.3579999999997,
    "median_um": 287.3579999999997,
    "p90_um": 287.3579999999997,
    "max_um": 287.3579999999997,
    "over30": 1,
    "over405": 0
   },
   "rx_flit": {
    "bits": 597,
    "min_um": 4.373999999999796,
    "median_um": 52.22999999999979,
    "p90_um": 90.48599999999976,
    "max_um": 100.14199999999994,
    "over30": 437,
    "over405": 0
   },
   "rx_v": {
    "bits": 1,
    "min_um": 130.2059999999998,
    "median_um": 130.2059999999998,
    "p90_um": 130.2059999999998,
    "max_um": 130.2059999999998,
    "over30": 1,
    "over405": 0
   },
   "tx_up": {
    "bits": 1,
    "min_um": 286.0619999999999,
    "median_um": 286.0619999999999,
    "p90_um": 286.0619999999999,
    "max_um": 286.0619999999999,
    "over30": 1,
    "over405": 0
   }
  }
 },
 "phy_serdes_b": {
  "all_payload": {
   "bits": 1197,
   "min_um": 2846.334,
   "median_um": 2971.782,
   "p90_um": 3067.062,
   "max_um": 3097.566,
   "over30": 1197,
   "over405": 1197
  },
  "buses": {
   "tx_flit": {
    "bits": 597,
    "min_um": 2846.334,
    "median_um": 2922.782,
    "p90_um": 2984.3100000000004,
    "max_um": 2999.358,
    "over30": 597,
    "over405": 597
   },
   "tx_v": {
    "bits": 1,
    "min_um": 2871.854,
    "median_um": 2871.854,
    "p90_um": 2871.854,
    "max_um": 2871.854,
    "over30": 1,
    "over405": 1
   },
   "rx_flit": {
    "bits": 597,
    "min_um": 2944.478,
    "median_um": 3021.502,
    "p90_um": 3082.4700000000003,
    "max_um": 3097.566,
    "over30": 597,
    "over405": 597
   },
   "rx_v": {
    "bits": 1,
    "min_um": 2971.982,
    "median_um": 2971.982,
    "p90_um": 2971.982,
    "max_um": 2971.982,
    "over30": 1,
    "over405": 1
   },
   "tx_up": {
    "bits": 1,
    "min_um": 2873.1179999999995,
    "median_um": 2873.1179999999995,
    "p90_um": 2873.1179999999995,
    "max_um": 2873.1179999999995,
    "over30": 1,
    "over405": 1
   }
  }
 },
 "phy_ucie_kv": {
  "all_payload": {
   "bits": 1169,
   "min_um": 22.69999999999999,
   "median_um": 147.204,
   "p90_um": 381.492,
   "max_um": 383.508,
   "over30": 1167,
   "over405": 0
  },
  "buses": {
   "tx_flit": {
    "bits": 583,
    "min_um": 137.19600000000003,
    "median_um": 142.18800000000002,
    "p90_um": 146.156,
    "max_um": 147.204,
    "over30": 583,
    "over405": 0
   },
   "tx_v": {
    "bits": 1,
    "min_um": 22.69999999999999,
    "median_um": 22.69999999999999,
    "p90_um": 22.69999999999999,
    "max_um": 22.69999999999999,
    "over30": 0,
    "over405": 0
   },
   "rx_flit": {
    "bits": 583,
    "min_um": 373.41999999999996,
    "median_um": 378.54,
    "p90_um": 382.444,
    "max_um": 383.508,
    "over30": 583,
    "over405": 0
   },
   "rx_v": {
    "bits": 1,
    "min_um": 260.332,
    "median_um": 260.332,
    "p90_um": 260.332,
    "max_um": 260.332,
    "over30": 1,
    "over405": 0
   },
   "tx_up": {
    "bits": 1,
    "min_um": 23.72399999999999,
    "median_um": 23.72399999999999,
    "p90_um": 23.72399999999999,
    "max_um": 23.72399999999999,
    "over30": 0,
    "over405": 0
   }
  }
 }
}

[
 {
  "choice": "Preserve current outer slots/ports with explicit physical registered adapters",
  "impact": "Keep declared native views and add plan-owned external face-register adapter masters outside native bodies. Need 1197 data/control boundary flops per SerDes instance per direction split (input598/output599), plus valid/epoch/reset physical mapping, cycle/R8/START pricing and exact RTL lockstep+mutant. For phy_serdes_b all1197bits need>405um physical transport before any final pin-reg stage; place explicit repeater/registered hops only in available bays, then model congestion/area/latency. Nvariant also has R2proxy p90 above30 even though allwirehops<405, so it needs registers near the retained outer pins or revised partition contract."
 },
 {
  "choice": "Move outer partition port contract to exact currently declared native pin fields",
  "impact": "Bare registered-hard rule can remain, source native views unchanged, remove synthetic internal adapter distances. Requires new pin windows/layers, opposite-face neighbour port alignment, station placement and clock/root/CA/START regeneration; io_serdes_2 E\u2192nativeN is substantial die-edge cut/repartition. Outer macro outlines can remain unchanged but current exactabutment ports and frozen waveforms cannot be reused."
 },
 {
  "choice": "Explicitly evaluate an existing alternative published PHY view/orientation",
  "impact": "Normal Wface s597view is2320.056\u00d71563.570, M4clk[0,600,0.192,600.024]. Rotating90deg yields tall1563.570\u00d72320.056 but Wface becomesN/S, notE. KeepingW/Eface requireswide2320um footprint, which exceeds1563.84currentstrip by756.216um. View migration is a physical contract change requiring root/OWNER review; not silently selected, not a short fix to Eface."
 }
]

All native clock geometry is source-specific; nface UCIe candidate was not selected. Current coll_ucie uses old normal UCIe clk[188.844,777.504]; KV uses different native clk[276.396,777.504].

Synthetic SerDes outer1202pins include1197payload+5 epoch wires. bind.py3186 strips incoming epoch,3249 drives output epoch from delivered reset, no flop. Existing logical mapping must be physically realized by explicit adapters, not erased.

SerDes current slot1563.84x2324.16 vsnative1563.570x2320.056: MX nativebodybbox y14009.544, clockcenter14009.640; naive bare placement at parent y14005.44 would putclock14005.536 (4.104um wrong).

Source nativeFDI generator explicitly uses M5 pitch48nm and phase .012+k*.048, so SerDes1199Nface pins/57.528um is intended source geometry, not arbitrary density inference.

Both visualizations personally viewed before proposal submission.
