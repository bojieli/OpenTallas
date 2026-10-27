# S81-ROWX3 (2026-10-26): cross-die rank-order row transport (OR-merge) + 16-owner bench + re-price

Base claude/s81-rowx2-1026@feaec58ef0 (rank-order RO = 1 export slots). Ruling COORD 19:18 RULING S81-ROWX-2: the
cross-die OR-merge transport is a release item. Static schedule: no credit / ready / backpressure.

## Where the row path lives (found)
svc_att RO export -> pv_od -> P.V return tree -> entry pv lane -> dsfd_dvland_pvrd -> C3 band port (ot_s81sl_xr bi)
-> leaf store -> xr send -> tier line ring (ot_s81sl_rstop) -> end-slice lep (ot_s81sl_slice_lep: UCIe lanes, the only
elastic boundary) -> peer die ring -> C3 band port bo -> dsdv_idx_bsplit -> peer svc entry q (ROWS type 6).
The existing path carries XB/XQ beats by hop count; it has no slot-wise merge. The new block
rtl/dsrom_sys/s81_dv/svc_rs/rowx/ is the merge, sized for one die half. It sits between the pvrd export word stream and
the band port.

## RTL (rtl/dsrom_sys/s81_dv/svc_rs/rowx/)
- `dsdv_rowx_rp.sv` re-pair: the half's export (7 passes x 8 tile windows x 40 words, XP 320) -> one PK2 slot a cycle.
  - Slot n of pair window (2j, 2j+1) = {window 2j+1 half h, window 2j half h} of word n mod 40, h = n div 40.
  - Each slot holds two tiles of one rank. Fixed latency 42 cycles.
  - Storage 120 x 512 b: A double-banked, B single. The bank-reuse proof is in the header.
  - Export word off its booked cycle -> f_mis.
- `dsdv_rowx_lc.sv` landed crossing: pin flop + D=16 landing FIFO. It pops on the consumer's own booked slot, never on
  arrival. Faults: late (empty at pop) and overflow. No ready / credit.
- `dsdv_rowx_xm.sv` one owner's stage in a static 16-position chain (POS is set by CFG):
  - REDUCE POS 0 -> 15: partial | own. Own valid halves get POS stamped in the spare half bits [171:168]. A half valid
    in both the partial and the own word -> f_ovl (a slot claimed by two owners). A wrong (rank, tile) for the slot ->
    f_slot.
  - BROADCAST POS 15 -> 0: relayed with one register per hop.
  - EGRESS: keep a half iff it is valid and its tag != POS, so the receiver's own rows are excluded by construction.
    Clear the tag. Drop the padding slots of rank >= NR statically. Lead with the CFG header. The ingress gets exactly
    1 + 2,048 words for any selection.
  - Every input lands in a flop and every output leaves a flop. Timing is data-independent.

## Bench (rowx/test/run_rowx_xm.sh, tb_dsdv_rowx_xm.sv): ROWXM_GATE PASS (bench/gate_g1.log)
- Setup: 16 owners. Each drives its RO export in the exact ROWX-2 RTL format and timing; the ROWX-2 bench checked that
  format against an independent golden. The owners run through 16 xm stages with registered links: fixed latency plus
  random jitter 0..J, in random chain order.
- Checks on every receiver: header + 2,048 words; each of the 512 x 8 (rank, tile) slots held by another owner lands
  exactly once with that owner's exact half; no own half; no other half.
- base: 20 runs PASS.
  - 5 seeds, J 0-3.
  - Identity chain order.
  - L 40 / J 3.
  - The 8 golden fixture layers (fix/gid_L*.hex).
  - Negatives, all caught at the expected stage:
    - a rank exported by 2 owners -> f_ovl, x2;
    - a link booked 2 cycles early -> late;
    - an owner exporting 1 cycle late -> f_mis.
- Mutants all FAIL:
  - mut1 (no self exclusion): err 4096.
  - mut2 (no overlap check): the overlap is not caught.
  - mut3 (re-pair bank): err 1441.
  - mut4 (padding slot kept): 2053 words.
- Span, measured (first export word -> last ingress word at the last receiver; bench/hop.log):
  - formula: 45 + 2 x sum of the 15 HOPs + 2,216 + 3, with HOP = L + J + 4.
  - 16 dies, every link die-to-die at L 37 (U_WIRE 34 + lep 3), J 4: 3,614.
  - 4 dies x 4 stacks (3 d2d links at L 37, 12 on-die at L 6): 2,870.

## Price (price_rowx3.py on the 9f97c5c993 ledger tree; price_rowx3.json)
The ingress figure is C = 98 + span, where 98 = ROWX header -> first export word (measured in ROWX-1).

| config | C | AR | MTP | S81 ledger % |
|---|---|---|---|---|
| ledger now (3809) | 3809 | 1259.6 | 3655.3 | 17.045 |
| B=80 (no transport) | 4801 | 1249.2 | 3621.1 | 18.23 |
| RO, transport NOT counted (ROWX-2) | 2049 | 1278.5 | 3717.6 | 14.90 |
| **RO + transport, 16 dies** | 3712 | 1260.6 | 3658.6 | **16.93** |
| RO + transport, 4 dies x 4 stacks | 2968 | 1268.5 | 3684.8 | 16.03 |
| RO + transport, 16 dies, lane cap 0.764 | 4397 | 1253.4 | 3634.9 | 17.75 (UNCHECKED arithmetic) |

- The baseline and the ROWX-2 RO row reproduce exactly: CHECKED.
- The ledger % for the new rows was cross-checked as linear in C against the ROWX-2 delta (-2.141 pp per 1,760
  cycles). It agrees within 0.01 pp: CHECKED.
- The MTP floor of 3,000 holds in every row.
- **The ~14.9 % does not survive the transport**: RO is 16.9 % with 16 dies. It still beats B=80, whose transport is
  not priced either.

## Open
1. Link rate:
   - Both halves at 1 slot a cycle = 1 XB beat (1,024 b) a cycle a direction. One lep lane pair carries only 0.764.
   - The fix is either the AB_EN second lane pair or NXW 30 windows (density 0.75; not built).
   - The bench assumes full rate.
2. Hop count: rooting the reduce in the middle of the chain (two 8-chains, a 3-input OR at the root) cuts the hops
   from 2 x 15 to 2 x 8. That is about -630 cycles at HOP 45, i.e. ~16.2 % (UNCHECKED). It needs a third input port on
   one stage.
3. Integration and the real-RTL e2e:
   - Integration: the xm per die half between the pvrd and the band port, or inside xr. That is a die plan delta for
     the S81 plan owner.
   - The real-RTL e2e is not run: an actual svc_att ex and rx through the chain. This bench uses the checked export
     format and scores the PK2 contract.
   - Whether ingress during the receiver's own export is legal in svc_att is UNCHECKED. The chain overlaps them on
     every POS.
4. Area (UNCHECKED, not synthesized): about 152 x 512 b of flops per half per die (re-pair 120 + 2 landings x 16), so
   roughly 25-40k um2 per half.
