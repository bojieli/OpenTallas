# S81 native paired views: qualification (2026-10-13, Claude S81 die stream)

Tool: `tools/s81/native_view_qualify.py` (record `qualification.json`). Input: the 17 legacy-master bundles and 4 HC
half-region leaf bundles of `manifest.json` (2,387 reference instances with the HC leaves flattened: 1,683 legacy +
704 HC), each checked against the closure-loop job state of the route it was exported from, child_lint on the
committed LEF, the ETM contents, the registry throughput gate and the contract clock rules.

**Result: 0 of 21 masters qualify.** No timing or DRC gate fails; the failures are view provenance, pin access and
bench coverage. dsfd_svc_join is the nearest: every gate passes except the open export-side STA comparison.

| gate | failed masters | what it means |
|---|---:|---|
| pair | 8 (+10 open) | FAIL, 8 views (five stations, hx_W, hcol, hsel; 1,547 instances): the TT ETM was committed 10-07, before the LEF + FF/SS ETM of a later route / archive re-route (10-08, 10-11): it is the extraction of an earlier ODB. OPEN, 8 views (cfifo, hx_E, hl x3, hix, hqe, ha): TT written by a separate later extraction with no ODB hash linking it to the LEF. OPEN, ctfn / ctfs: verdict on a hold-ECO pass; the loop installs the ECO ODB in the route directory before re-export, but the export records no ODB hash |
| lint | 15 | child_lint (f): 352-1,058 face pins per master have the tile's own metal on the layer above the pin (no die access: DRT-0073 class); stnh_512 also has one M7 VDD stripe. Only stnv_512x1, svc_join and the four HC leaves are lint-clean |
| bench | 9 | hl_E0/E2/W1, hix_SW, hqe_SW: the `-mm` job carries no bench record; ctpl/ctfx/ctfn/ctfs: lint only (no behavioural pass + failing mutant on the leaf) |
| current | 3 | hix_SW, hqe_SW, hsel: the registry's adopted closure is the later M5 route, the bundle is the older view |
| clock | 1 | cfifo `ck[0]` has no min/max_clock_tree_path in the FF ETM |
| export (open) | 13 | export-side STA differs from the verdict (stations FF +15.7 ps) or does not exist (ref_tile views); the exporter's SDC order is still not the verdict's |
| thr (open) | 4 | HC leaves have no budget row; the HC production bench (286-287 vs <= 124.19 cycles) is itself failing |

14 master classes have no complete bundle at all (dsfd_ctrl, hq_SW, hco_SW, seven hr_*, and HC ctnl x1,024 / ctra /
ctrb / ctrn x64 each).

## Minimum-delay budget measured on the real ETMs (FF)

ETM arcs include the tile's clock insertion. Internal launch L = cq_min(pin) - max insertion, internal hold
H = hold_max(pin) - min insertion; a zero-wire seam needs L(sender) - H(receiver) >= 50 ps (die hold uncertainty) +
skew, which is the ">= 65 ps" budget of the request ledger against the interim 15 ps hold.

| view | L ps | H ps | insertion spread ps | same-master zero-wire margin ps |
|---|---:|---:|---:|---:|
| dsfd_svc_join | 71.1 | 1.4 | 31.7 | +19.7 |
| ot_s81_hc_ctpl | 68.8 | 5.6 | 38.7 | +13.1 |
| ot_s81_hc_ctfx | 67.3 | 2.6 | 35.4 | +14.7 |
| ot_s81_hc_ctfs | 63.9 | -14.4 | 64.4 | +28.3 |
| ot_s81_hc_ctfn | 32.0 | 19.0 | 106.2 | -37.0 |
| hend ck (hx/hl/hix/hqe/ha/hcol/hsel) | 58.5-96.7 | -40.8..-22.7 where an input exists | 19.7-38.2 | +38..+88 |
| dsfd_cfifo cr | -39.1 | -29.3 | 87.6 | -59.8 |

Real pin-registered ref_tile views launch 64-71 ps after their latest clock leaf, not the interim 32 ps; the bound is
conservative (worst leaf on each side). ctfn (106 ps insertion spread over a 576.72 x 25.92 strip) and cfifo do not
meet it. The die verdict is the FF STA on these views with the synthetic pads off, per seam.

## What each failure needs

1. One export per closing ODB: LEF + TT/FF/SS + corner STA from the ODB the verdict was measured on (after ECO), with
   the verdict's SDC sequence. Needs the shared exporter fix (verdict SDC order) first; then re-export, no re-route.
2. Stations, cfifo and hend views (15 masters, 1,673 instances): re-route through tools/ref_tile (above-only pin
   keepout, M5 cap, scalar clocks); the present views cannot be reached by the die router.
3. HC leaves: a behavioural leaf bench + mutant (or the cth composition bench on these exact leaves).
4. Relays (27 masters, 29,184 instances) and the other generated glue have no view at all: relay kits
   `physical/ref_tile/s81_rly_*` (tools/s81/rly_kits.py) are the first real masters.
