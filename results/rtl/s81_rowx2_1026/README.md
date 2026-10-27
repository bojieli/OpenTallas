# S81-ROWX2 (2026-10-26): rank-order export slots + B = 80 fallback in dsdv_svc_att

OWNER 18:4x: rank-order export slots APPROVED to build; B = 80 is the temporary fallback; S81 performance ACCEPTED
(~18 % ledger while the fallback is in use). Base claude/s81-rowx-1026@ee24aba28 (spec ~/coord/lanes/S81-ROWX.md).

## RTL (rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv, ROWX = 1 only; ROWX = 0 unchanged)

The ROWX frame (type 11) gains [30] RO. Both modes live in the same ROWX = 1 hardware, so the mode is a frame field
chosen by the compiler.

- **RO = 0: the fallback.** This is the held-list export of ee24aba28, unchanged. The fallback config is B = 2 NXW = 80,
  meaning one pass with NXW 40 and LAST. The ingress is 60 B + 1 = 4,801 q cycles per half. Fault 26 fires when the
  list holds more than 80 rows. Fault 24 has changed: it now means a held-list export after the list overflowed
  XN = 128. It is raised at the RO = 0 frame and no longer at the scan, because an RO job never reads the list.
- **RO = 1: rank-order slots.** The frame fields are [15:0] XO, [21:16] NXW, [34:31] NP - 1 and [46:35] XP (the pass
  period, which must be greater than NXW).
  - Word i of pass p leaves pv_od in share cycle XO + pvs + 1 + p XP + i.
  - It carries the ranks 2 (p NXW + i) and that rank + 1.
  - A half is valid iff its rank is below nsel and `x_own[rank]` is set. x_own is a new 512-b mask that the SEL_IDS
    scanner writes on every scanned rank (g_own), like sel_held.
  - Every rank therefore has one fixed slot on every die, whichever die holds it. The schedule does not depend on the
    data, there is no count to overflow, and nothing has a credit or ready (owner rule).
  - The die config is NP 7, NXW 40 and XP 320. 320 is the half's 8 tile windows of 40 cycles (rs_pvslot_all), so the
    passes reuse the P.V drain windows. pvrd nw = 160 divides 8 x 40.
  - Fault 26 (RO) means 2 NP NXW < nsel. It is a static frame error. Fault 25 adds XP <= NXW.
  - Area added on top of ROWX: 512 FF for x_own, a 512:1 1-b mux for each half, and about 40 FF of pass state.
    UNCHECKED, not synthesized.
- **Ingress.** The existing PK2 ingress (type 6, spec [0] = 1) is unchanged. In RO mode it receives 512 ranks x 8 tiles
  / 2 = 2,048 words + 1 header per half, whatever the selection.
- **Transport (TOK-DS compiler / xr; NOT in this RTL).** The 15 peer dies' RO streams are slot-aligned and disjoint,
  because each rank has exactly one holder. The ingress is their slot-wise OR merge, re-paired into PK2 words in rank
  order. The receiver's own stream must not be merged into its own ingress: those halves would hit fault 29.

## Bench (rtl/dsrom_sys/s81_dv/svc_rs/test/run_svc_rowx.sh, tb_dsdv_svc_rowx.sv)

Variants:
- `base` must PASS every run:
  - ro0 / ro1 on seeds 1-3.
  - The 8 fixture layers in both modes. `fix/gid_LNN.hex` holds the 1M golden token's top-512. ex is the layer's
    max-held (die, stack), 41-49 rows (`fix/manifest.json`).
  - Stress: ro1 with ex holding 150 and 300 rows (no overflow). ro0 with 100 and 150 rows, where faults 26 and 24 must
    flag the overflow.
- `miter`: lockstep ROWX 1 vs ROWX 0 on legacy traffic.
- `mut6`: rank ^ 1. `mut7`: PK2 lands the other tile's half. `mut8`: the RO valid bit comes from the stack-only
  sel_held. Every mutant must FAIL.

The RO ingress check builds rx's whole rank-order stream. It is the OR of ex's ACTUAL RTL export and a synthetic stream
from the 14 other peers; disjointness is asserted, and the other 7 tiles' halves are decoys. The 2,049 words are sent
back to back. For PASS, all 512 rx slots must be landed with the right piece: rx's own fetch, ex's export, or the peer
data.

## Price (price_rowx2.py, TOK-DS-6b composition = results/rowx_budget_1026/price_options.py; price_rowx2.json)

The baseline reproduces AR 1,259.6 / MTP 3,655.3 (CHECKED: the same tool output as ROWX-BUDGET). The ledger % is the
table total 17.045 plus this config's A + B e2e % minus the 3809 A + B e2e %, all from the same compute. That column is
UNCHECKED. The stored A/B rows were priced AR-binding at 1.322 + 1.326, but compute now binds MTP at 3.404.

| config | ingress per half | export entry cycles | AR tok/s | MTP tok/s | AR / MTP + export (serial) | S81 ledger % (+export) |
|---|---|---|---|---|---|---|
| ledger now (pair format) | 3,809 | - | 1,259.6 | 3,655.3 | - | 17.05 |
| **B = 80 fallback** | 4,801 | 320 | 1,249.2 | 3,621.1 | 1,245.9 / 3,610.2 | 18.23 (18.61) |
| **RO rank-order slots** | 2,049 | 2,240 | 1,278.5 | 3,717.6 | 1,254.5 / 3,638.6 | 14.90 (17.62) |

Neither config prices the cross-die transport, just as the 3809 row does not. The RO export takes 2,240 tree cycles
because the per-tile export rate (2 ranks a cycle a tile, 8 tiles in disjoint windows) matches the ingress rate. The
export overlaps the ingress only if the transport streams cut-through; the serial "+export" column is the upper bound.
