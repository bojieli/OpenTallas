# KV final reset distribution: source-bound planning inventory

This packet is diagnostic and **MODEL ONLY / NOT QUALIFIED**. It changes no die
netlist, reset calendar, physical placement, gate, timing constraint, or view.

Exact baseline: source `9d63284a1`, original placed d22bu netlist
`e9fcbd5474fc701999608075182d442132cca9c4674098c9a64a1d2598cf40f7`.
Inputs remain on ep6 in
`/srv/opentallas-scratch/claude/codex-kv-2210/d22bu-aliasbound`.
The original historical run and the DCAL alias-corrected diagnostic copy remain
separate. This is not a completed selected LAND candidate.

## Concrete defect

`kv_rst_regional.py` builds reset trees before `kv_fwd_lanes.py` forms forwarded
lanes. Lane formation adds `.en` and `.rs` consumers, selecting a most-common
reset on each clock tree without checking physical distance. A later invocation
of the original regional pass would omit the generated `n_rrs_` nets.

The exact exporter reports 12,993 potential reset pairs, 789 longer than 405 um:
379 `.en`, 219 `.rs`, seven `.rst_n`, and 184 relay `.a` pairs. The largest is
`rrs_n_rst_die_t1__m_0__g1_s188/b -> rly_pinfix_pll_lock_0__s0/en`, 28,959.8245 um.
Its selected reset root is `rly_rst_die_t1_64/b`, 28 downstream edges away. No
nearby candidate preserves that same root, depth, and source clock. Only 204 of
the 789 potential pairs have even a model candidate satisfying those three
identity constraints within reach.

**Direction caveat:** old generic frames use INOUT for some actual RTL inputs.
An example is the purported `ahub/rst_n` reset driver. Thus the 789 count is an
exporter diagnostic, not a count of confirmed physical reset drivers. The die
lead is replacing generic directions with exact bound RTL directions. Re-export
and rerun this inventory before adopting any repair. No reverse pair is repaired
by this packet.

## Source/model repair required before GRT

1. Final endpoint discovery runs after forwarded lanes and the health plane.
   Resolve each driver from actual bound RTL directions, not INOUT inference.
2. Preserve the reset producer identity. `.en` on a `qkd_landsh0` belongs to
   `ck_s`; `.rs` belongs to receiver `ck`. A common reset name or a nearby leaf
   does not establish compatible source, clock, or release edge.
3. Reserve real transport sites along relay channels and two receiver-local
   capture stages. Every actual pin span must be at most 405 um and every
   functional driver fanout at most 32. Reuse only qualified closed relay cells.
4. Export absolute assertion and release edges for every endpoint from the
   exact source clock/reset root, its input-chain depth, constant `dly` straps,
   selected root RTL, new transport stages, and two local captures. Refuse any
   unresolved root, unequal reset epoch, overflow, flush/hold violation, or
   unsatisfied first-use boundary. Adding transport changes the calendar.
5. Run standard RTL/netlist LEC and strict bind, then causal reset/protocol
   benches that change source identity, release depth, and clock selection.
   Qualify a fresh final GEN snapshot before trial GRT. No name waiver, timing
   false path, mask, or native formal proof is proposed.

The report records actual reset provenance, stage clocks, root input-chain
provenance and exact constant `dly` when present. Its root formula is deliberately
conditional on exact root RTL/bind qualification. Two local capture edges and a
transport-stage lower bound are model costs; no legal placement is claimed.

## Reproduction and validation

The tool checks the final netlist SHA against the facts before reading geometry:

```
python3 kv_reset_endpoint_calendar.py \
  --case d22bu-aliasbound \
  --facts d22bu-aliasbound/gen_safety_facts.json \
  --out reset_endpoint_calendar_2253.json
python3 -m unittest -v test_kv_reset_endpoint_calendar
```

Both ran unpinned with `ot-run --mem 4 --threads 1`, ep6 unit
`oth-ubuntu-786765-1792561824`, terminal exit 0. Five focused tests pass: matched
source/clock/depth, plus causal clock, root, depth, and cycle refusals. These test
the inventory only; they are not RTL reset/protocol qualification.

The first inventory attempt, unit `759385`, failed on a multi-rectangle pin
geometry assumption. The corrected tool retains every exporter source witness
point and uses the largest candidate distance. Original remote failures and
intermediate reports are retained. Final inventory is compressed here without
changing its contents; the full original remains remote.
