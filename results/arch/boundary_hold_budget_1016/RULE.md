# Die-wide boundary hold budget (FLOW-HOLD, owner approval 2026-10-16 ~22:00)

Status: **rule + impact study, not deployed.**
- The branch `claude/flowhold-1016` carries an opt-in implementation: spec `"hold_budget": "die"`, default off.
- Kits that do not opt in regenerate byte-identically.
- Deployment to the closure daemon or the recipe defaults waits for the coordinator.

## 1. Problem

Every tile currently pads hold on its own boundary pins, which pushes native capture past 190 ps. The padding has three sources:

- **Sign-off/route SDC (`io_ref_skew.sdc`, rule H1).**
  - Input min = `L_min`, so a sender launch of 0 ps is assumed.
  - Output min = `-L_min - 50`, so the sender must launch at least `L_min + 75` (the 50 ps die skew plus 25 ps U).
  - The tile's 25 ps hold uncertainty (U) and the route hold margin HM (30 ps in recipe 2/3) also apply to every boundary path.
- **Structural pin pads (recipes 2/3).**
  - `inhold`: a BUFx4f followed by an HB2xp67 at every input.
  - `outhold`: BUF, HB, BUF at every output.
  - Both are inserted before placement, whether or not any hold race exists.
- **Repair overshoot.** CTS/GRT repair stacks BUFx2 chains on top of the structural pads.

Measured on the views the dies bind today (section 6), from their exported FF Liberty:

| | median | worst (closest to a violation) |
|---|---:|---:|
| Sender guaranteed FF launch (O_min − R) | 94 ps | 72 ps |
| Receiver FF hold need (H − R) | −50 ps | −37 ps |

A negative hold need means data may arrive that many ps *before* the clock edge. Both sides therefore pad. Every link carries about 110–170 ps of FF hold margin, against the at most 105 ps that the die needs (80 ps neighbour skew plus 25 ps U).

**Example: COLL ctl2 v7.** It fails native capture at 197.3 ps on `dest_v[1]`:
- The path is BUFx4f followed by 6 x BUFx2 and has 70 ps of named hold cells at FF.
- That pin keeps +55 ps FF slack even under the current SDC, so the padding is surplus.
- The view exports launch-min 96.5 ps and hold need −70.7 ps: about 167 ps of margin on each link.

## 2. Definitions

All values are at FF unless stated otherwise. Times are relative to the tile's clock reference.

| Symbol | Meaning |
|---|---|
| `L_min` / `L_max` | Propagated FF-min / TT-max clock arrival at the tile's reference pin register. The reference is the median input pin flop, chosen as in `io_ref_skew.sdc` PINFLOP-REF. In the die it corresponds to φ − R. |
| `C` = **25 ps** | Guaranteed sender launch at FF: the earliest data change at an output pin after `L_min`. ASAP7 DFFHQNx1 clk→QN at FF is 32.2 ps at minimum load and 5 ps slew (TT 45.4 ps), plus INV/driver. 25 ps leaves about 7 ps for pin flops clocked earlier than the median reference. |
| `U` = 25 ps | Sign-off hold uncertainty. |
| `Δ` | Capture-flop clock arrival minus launch-flop clock arrival for a communicating pair. Neighbour budget \|Δ\| ≤ 80 ps at TT and FF (owner, die_clock_check pair mode). |
| `H(i)` | Exported ETM hold constraint at input pin i, relative to the tile clock pin. `H(i) − R` is the pin's hold need. |
| `w_min` | Minimum die wire / relay delay between two pins. |

## 3. Tile contract (qualifying tiles, `hold_budget: die`)

**T-OUT (sender, tile-level check).**
- SDC: `set_output_delay -min [U - (L_min + C)]`.
- Effect: the tile proves at FF sign-off that every output launch is at or after `L_min + C`.
- A pin register meets this unpadded (32 ps or more), so no output pad is inserted.

**T-IN (receiver, tile-level check).**
- SDC: `set_input_delay -min [L_min + C + U]`.
- Effect: the receiver credits the sender's guaranteed launch C with zero wire. The `+U` cancels the tile's own hold uncertainty on input→register paths only; die STA applies U once per link instead.
- Remaining requirement: input-to-D delay ≥ `(c_flop − L_min) + t_hold − C`. That is ≤ 0 for a pin register, so no input pad is inserted.

**Flop-first pins (coordinator 2026-10-16, after H-REACH).**
- Every input lands on its capture flop first: pin → (wire) → D, with no cell between them. `inhold` is false, so the flop is anchored at the pin by `io_flop_at_pins`.
- Every output leaves its launch flop (Q / INV / driver) directly.

H-REACH measured why this matters (`tools/s81/relay_native_pair.py`, claude/sdie-reach-1016 fb66c63c8; ~50 S81 hop classes, both CLOSED native netlists + routed SPEF + GRT die wire):
- The first slew violation is always at the receiver's `ot_inhold_*/A` (HB2xp67), never in the driver.
- At the 260 ps max-transition limit, reach is 175–200 um for stations, 100–150 um for rly_536, and 50–100 um for sstn.
- Setup slack is still +180–380 ps there, and FF hold passes from 25 um including the 80 ps neighbour skew.
- So the pad also caps die reach electrically. A flop D pin is the slew-tolerant first stage.

This study adds a second mechanism (IMPACT.md class B_pinflop_wire):
- The recipe-2/3 inhold structure (pad at the pin, strong driver, long wire to the flop) puts 100–150 ps TT of buffered wire before the flop.
- That drives 8 of the 25 probed in-die native-FAIL views over 190 ps.

**Pin pads and route margin.**
- No structural pin hold pads: `inhold` and `outhold` are off, and `hold_pad` is unset.
- The boundary is repaired at margin 0: `io_hold_margin_ns = 0`. The route-time FF repair SDC relieves the boundary by HM through `OT_BH_ROUTE_RELIEF_PS`. Register-to-register paths keep HM, and sign-off keeps relief 0.

**Unchanged.**
- Setup: input max = `0.2T + L_max + skew`, output max = `0.2T − L_max + skew`, inter-region 150, TT, 60 ps U.
- The tile's internal hold (register-to-register, FF ≥ 0 at U = 25 with HM repair).

**Mixed links are safe.**
- A legacy (tile-mode) sender still launches at `L_min + 75` or later, which is above C, so a die-mode receiver is covered.
- A die-mode sender feeding a legacy receiver is also covered: the legacy receiver credits 0 and pads itself.

## 4. Qualification (which tiles may use it)

A tile may use the die budget only if all of the following hold:

1. It is a leaf tile (`kind: tile`). Clusters and parents compose children and keep the tile rule.
2. Every data pin is registered, in either of two ways:
   - recipe-3 `pin_regs` is enabled with no per-port `exclude`; or
   - `pin_regs` is off with a recorded reason, because the RTL already registers every pin (for example hcoll_v5_ctl2).
3. No combinational pin-to-pin arc. The native audit already fails such a view, so it is never bound to a die.
4. It has a single synchronous data clock (`io_ref_skew.sdc`), or clock entries handled per domain (`clock_entry_constraints.py`, same lines per domain).

Forwarded-clock relays (F1) and async/PHY families keep their own constraints.

`ref_tile.py` refuses a spec that sets `hold_budget: die` together with `inhold`/`outhold`, a pin exclusion, or a missing pin-register basis.

## 5. Die obligations (the matching die-level checks)

For every boundary link (sender pin o, optional relay chain, receiver pin i), die FF STA must show:

```
launch_min(o) + w_min + [relay stages] - Δ(send,recv) - H(i) - U  >= 0     (FF, U = 25 ps once per link)
```

**D1. Die FF STA ≥ 0.**
- Inputs: the tiles' ETMs, relay views, propagated regional clocks (or measured arrivals from DIE-CLOCK `arrivals_ff.tsv`), and `set_clock_uncertainty -hold 25`.
- This is item 5 of the five mandatory die rules, so it is already a gate. It now also carries the boundary hold budget.
- **Verified 2026-10-16:** an ETM written from the routed ctl2 v7 under the old SDC and with input min-delay set to +300 ps and output min-delay to −300 ps is byte-identical. The pin hold arcs `H(i)` therefore do not depend on the tile's boundary min delays, and die STA sees the true requirement.

**D2. Neighbour skew.**
- die_clock_check pair mode gives |Δ| ≤ 80 at TT and FF for every communicating pair. This is already mandatory item 3.
- A die result containing `SYNTH_IDEAL_R0` masters is diagnostic for hold. Its hold verdict on those links is not accepted.

**D3. The shortfall is fixed at die level, never by re-padding the tile.**
- Per-link demand: `max(0, Δ + U + (H(i) − R_i) − (launch_min(o) − R_o) − w_min)`, with at most `80 + 25 + h − 25` = 80 + h ps when the pins sit at C.
- Where the fix goes:
  - **Relay stations (preferred).** A station already launches through Q plus matched buffers. A station feeding a short neighbour-matched hop gets a hold-delay variant (relay output launch-min raised, as the existing rly kits' BUF-HB4-BUF already does at 65 ps).
  - **Die-net hold cells,** for direct tile-to-tile hops with no station: `hbm_die_relay_sta.py --hold-pads` / `s81/die_sta.py` HOLD_PAD (already implemented, sized at FF, costed at TT/SS).
- **Forwarded-clock F1 hops** have Δ matched by construction (clock and data out-buffers equal), so hold per hop ≈ clk2q − t_hold (METHOD §3). The die STA confirms it and relays pad only where it fails.

**D4. Die-level setup carries the pads' TT cost.** It goes into the same die STA (TT ≥ 0). Hold cells sit on die links, which have their own cycle, not inside the tile's 190/220 ps native windows.

## 6. No-masking ledger

| Relaxed at tile level | Matching die-level check |
|---|---|
| Input min `L_min` → `L_min + C + U` | D1: die FF STA on the ETM hold arc `H(i)` with the real sender launch, wire, Δ and U = 25 |
| Output min `−L_min − 50` → `U − L_min − C` | T-OUT keeps a tile-level guarantee (launch ≥ C). The removed 50 ps die-skew term is D2 (measured Δ ≤ 80) plus D1 |
| Boundary route repair margin HM → 0 | D1 (die STA on routed parasitics with U = 25) |
| inhold/outhold structural pads removed | D1 + D3 (pads move to relays / die nets, sized by measurement) |

Nothing else is relaxed. Setup, the tile's internal hold, DRC and the native launch/capture budgets are unchanged.

## 7. Exact SDC / flow changes (branch claude/flowhold-1016)

- **`physical/qwen_die_masters/io_ref_skew.sdc`.** New block fenced `# OT_BH begin` … `# OT_BH end`, after the H1 lines:
  ```
  if {$::env(OT_IO_HOLD_BUDGET) eq "die"} {
    set_input_delay  [expr $qdm_lmin + C + U + relief] -min -clock core_clk [all_inputs -no_clocks]
    set_output_delay [expr U + relief - $qdm_lmin - C] -min -clock core_clk [all_outputs]
  }
  ```
  - C = `OT_BH_LAUNCH_MIN_PS` (25), U = `OT_BH_TILE_HOLD_UNC_PS` (25), relief = `OT_BH_ROUTE_RELIEF_PS` (sign-off 0; route = HM − io_hold_margin).
  - The block is inert without the env variable. `ref_tile.gen_signoff` strips it from non-die kits, so their signoff.sdc stays byte-identical.
- **`tools/ref_tile/clock_entry_constraints.py`.** The same two lines per IO domain, using `dlmin` (fenced; stripped unless die).
- **`tools/ref_tile/ref_tile.py`.**
  - Spec `hold_budget` (`tile` | `die`).
  - `check_hold_budget` qualification.
  - Die defaults: `inhold`/`outhold` false and `io_hold_margin_ns` 0.
  - Route ORFS vars: `OT_IO_HOLD_BUDGET`, `OT_BH_*`.
  - Sign-off env lines and `signoff_ffrepair.sdc` relief.
- **`tools/hier_contract/native_pin_audit.py`.**
  - New per-view fields `ff_launch_min_ps` (sender guarantee) and `ff_hold_need_ps` (receiver need), read from `<cell>_ff.lib`.
  - Informational: the die-budget inputs. The native verdict is unchanged.
- **Tests:** `tools/ref_tile/tests/test_hold_budget.py` covers default byte-identity, die kit content, the refusals and the strip helper.

## 8. Closure-loop, recipe and native-audit interaction

- **Closed tiles stand.**
  - The rule only relaxes hold (measured below). No closed tile changes verdict, and none needs re-STA to stay closed.
  - A re-route under the new rule is justified only for a native-FAIL view in class A (padding only) and needs a `reroute_reason`, kind `pin_register`, citing this study.
- **Recipe.**
  - `RECIPE_LATEST` stays 3 until the coordinator approves.
  - On approval, recipe 4 = recipe 3 + `hold_budget: die` for new leaf kits. Existing kits keep their recipe.
- **Native audit.**
  - The definitions are unchanged: TT launch O − R ≤ 220, capture S + R ≤ 190, no combinational pin, spread ≤ 80.
  - A die-mode tile passes the capture budget more easily because S loses the pad delay.
- **Hold ECO (`hold_eco.sh`).** It reads the merged sign-off SDC, so a die-mode tile's boundary is judged against the credited min delays. No ECO change is needed.
- **Die flows** (`hbm_die_relay_sta.py`, `s81/die_sta.py`, Qwen die STA) must time hold on ETMs with U = 25 and real/measured clocks (D1, D2).
  - **Placeholder senders:** the S81 die_sta placeholders currently assume a contract launch-min of 65 ps at FF. A die-mode real tile guarantees only 25 ps.
  - The die flows must therefore read launch-min from the bound view's ETM (`ff_launch_min_ps`), not from the placeholder contract. Owner: DIE-CLOCK / S-DIE / H-DIE.

## 9. Impact (STA only, no re-routes)

See IMPACT.md and impact.json in this directory.
