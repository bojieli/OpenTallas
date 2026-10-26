# qfd_c_b16_reg1b: CB16 representative landed region c1r1 (QW-CLUSTER3/CB16, CRITICAL prefix: gate only, no REVIEW.json / submit)

FALLBACK (parallel, PARALLEL rule): leg-a alignment = 3 hard stn514 relays; otherwise identical to qfd_c_b16_reg1.

## Scope

CB16 parent rebuilt as clock REGIONS joined only by LANDED crossings (LEAD-QW 12:15 decision). This kit is ONE
REPRESENTATIVE INTERIOR REGION (c1r1 of the 4 x 4 block) plus all 8 crossings that touch it. The neighbour-side half of
each crossing runs on the neighbour's clock port (ck_c1r0 / ck_c1r2 / ck_c0r1 / ck_c2r1) and takes its reset leaf from a
port. The full 16-region parent is too large for a first gate, so this region and its crossings are gated first.
Generator: tools/qwen_cluster/qc_reg_kit.py. Per-bit reach table and priced cycles:
results/arch/qwen_cluster_1017/q_cluster16/reg1/plan.json.

Hard children are all CLOSED views except the A0:
- crossings: qfd_c_land_{w,r}{257,258}_narrow (closed 10-19, auto-merged). Writer on the source root, reader on the
  destination root, static D4/K2 ring, no credit. The bank_w / bank_e / vld writer-to-reader paths are the landed
  multicycle window (-setup 2 -hold 3, LANDING-CONTRACT L5).
- column station: qfd_c_xstnw_safe (closed, main c4350ec70).
- relays: qfd_c_stn514 / qfd_c_stn516 (closed views on main).
- A0 qfd_tile_nk_rp2_romleaf_rr: diagnostic STAND-IN (a0_standin). No qualified A0 view exists, so every A0 pin and
  timing figure is a stand-in figure.

Crossing geometry: N-S crossings are vertical writer/reader stacks with a 43.2 um gap (vld straight, banks on the side
channels). E-W crossings are spanning side-by-side pairs, R0/MX only: an x-mirrored closed half puts 150 pins off the track grid (gen FAIL), so each bank bus wraps one half over
the parent layers. Inside the landed window the bank wire can be 518-648 um long, so the crossing itself is the long-reach
hop.

## Safe-design checklist (owner 10-19)

1 Pins: PASS. Every data port lands in a closed-half register (writer slot capture or reader output flop). rst_c1r1 is
  registered at the face (rpin_q), then goes through 5 kept stages. Each lrst_* leaf is registered twice inside its
  closed half. cid / far are static straps (case analysis).
2 Reach: PASS by construction. The largest single-cycle wire is 380.2 um, checked per bit on the real LEF pins (plan.json).
  Every inter-region edge goes through a landed crossing; the bank window paths reach at most 648.0 um (2 T multicycle).
  The port-to-half hops are checked by the gate's wire_reach.
3 Fanout: PASS. The parent logic is rpin_q (11 kept chains) plus one inverter (far_n). The closed children carry their own
  kept-copy audits.
4 Depth: PASS. The parent has no combinational logic between registers apart from far_n (a strap).
5 Storage: ring variant (reg1) PASS: the 3-deep 514-bit alignment delay of leg a is a same-clock hard ring pair (K2).
  Fallback reg1b WAIVED: it uses 3 hard stn514 relays 130-260 um apart (relay hops, not a soft flop chain). The 1-bit reset
  chains (5 stages per leaf) are WAIVED: they are distribution relays, not storage.
6 Floorplan: PASS (stand-in A0). Child origins are on the 21.6 / 43.2 lattice, channels are >= 20 um (generator check),
  and no child is within 20 um of the outline. The outline is 1857.6 x 1987.2 (aspect 1.07). Area is set by the pin- and
  reach-bound children, not by synthesis area: the parent has almost no soft logic, so util is the children's.
7 Clock: one regional root per region (ck_c1r1 is the core clock, the neighbour roots are separate ports). Each tree drives
  only hard-child clock pins plus the 56 soft reset flops. All seams are landed. io_hold_margin 0.03. TT/FF pin-flop
  spread comes from the gate (OPEN).
8 Schedule: static, with no credit or backpressure. Added or removed cycles per edge class are in plan.json
  priced_cycles: column run -1, leg 3_0a -1, leg 4_0b -1, crossings +0 (hard halves = soft D4/K2), leg 2_0a +0. The full
  parent generator must re-derive the node alignment pads from these numbers.

Region size: about 1.3 x 1.7 mm. It is set by the 1.17 mm-tall A0, so it is above the ~1 mm guidance. This is recorded,
not waived silently: the A0 cannot be split across roots.

## Owed before any binding

- A region bench: ring K2 equals the 3-deep pad, and reset epochs are equal across the 8 crossings (RDL=6 on every leaf).
- A qualified A0 view.
- The full 16-region generator (this kit's netlist and placement rules applied to every region).
