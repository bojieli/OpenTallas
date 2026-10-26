# S81 die c6p (v16, pathfinding, gates off) three-corner STA: failing endpoints by path class

Source: `codex-s81-grt-collected-1013-pm/sta_reports.tar.gz` (sha256 b9fefda6...), end_{tt,ss,ff}.rpt = 5,469,265 endpoints per corner
(`-group_path_count 100000`: the stream trunk group is capped at its worst 100,000). Launch end of every endpoint from the
plan hop list (g17/b0, same v16 options). Tool `tools/s81/sta_path_classes.py`; rows in `classes_<corner>.json`.
Kit of the case: 21 relay masters CLOSED + q element + ROM macro real, 150 masters interim (pin = flop, K: FF cq 32 / hold 15,
TT cq 55 / setup 18), `dsfd_ctrl` / `dsfd_sp_vm` partitioned; clock delivery already insertion-compensated (balance_latency,
clock_delivery.json: 174 common, 1 early tap). `dsfd_cfifo` is NOT in the binding table, so the kit dropped its colck view.

## Setup (TT sign-off corner): −1,426.8 ps, 9,071 violators, TNS −2.69 s

| class | endpoints | violators | worst ps | TNS ns | cause | real? |
|---|---|---|---|---|---|---|
| `cfifo.co -> cfifo.cr` (col_clock, 1 um) | 128 | 111 | −1,426.8 | −24.6 | the interim cfifo has ONE clock (`ck`): the column clock return `cr` is timed as DATA against it | placeholder lib |
| `rly_2_NS.o -> cfifo.st` (stat, 224 um) | 256 | 256 | −381.5 | −92.5 | launched on ck_col_N, captured by the interim cfifo on the stream trunk `ck` (the real colck view captures on `cr`) | placeholder lib |
| `rly_68_EW.o -> cfifo.ri` (col_ret, 63 um) | 8,704 | 8,704 | −311.6 | −2,574.5 | same | placeholder lib |
| closed -> closed (20 classes, 882,944 endpoints) | 882,944 | 0 | +169.3 | 0 | real relay views, real wire | REAL: passes |
| interim -> closed / macro (47 classes) | 1,281,676 | 0 | +285.5 | 0 | | passes |

All of −1.4 ns is the single-clock interim `dsfd_cfifo`. Real-to-real setup is +169.3 ps at TT.
SS (information only; sign-off is TT setup / FF hold): the same three classes (−1,413.4 / −886.9 / −800.1) plus one REAL
class: `rly_63_WS.o -> rly_63_NS.i` (ret_leaf, up to 374 um) 4,213 of 153,216 endpoints, worst −56.4 ps, TNS −66.1 ns, and
`rly_2_ES.o -> rly_2_NS.i` 7 endpoints −1.7 ps.

## Hold (FF): −576.9 ps, 1,196,439 violators, TNS −62.59 s

| class | endpoints | violators | worst ps | TNS ns | cause | real? |
|---|---|---|---|---|---|---|
| `cfifo.xa / xb -> rly_283_SN / 266_SN.i` (x_lane, 60–80 um) | 70,272 | 70,272 | −576.9 | −40,152 | interim cfifo launches the column side from the trunk `ck`; the relay is on ck_col_N = `ck` + co pass + column tree (548 ps later). The real colck view launches from `cr` | placeholder lib |
| `cfifo.cc -> rly_15_EN.i` (x_ctl, 93 um) | 1,920 | 1,920 | −519.2 | −978 | same | placeholder lib |
| interim / partitioned -> interim / partitioned, 189 classes (ret_tree nodes, sstn -> relays, hub stations, slabs, ctrl <-> svc) | 2,763,318 | 1,010,469 | −33.3 | −21,185 | lib constant: cq 32 + wire − (hold 15 + uncertainty 50) = −33 at zero wire; fails on every hop below ~45 ps of wire (longest failing 469 um at −11.5) | placeholder lib |
| interim -> ROM macro `ce_in / addr_in` and q element `xs_q0 / xs_q1 / xs_p / cfg_*` | 911,899 | 113,778 | −28.7 (ROM) / −8.5 (q element) | −259 | interim launch (cq 32) into a REAL capture pin: hold requirement of the real pin against a 32-ps launch | launch side placeholder |
| closed -> closed (20 classes) | 882,944 | 0 | +131.1 | 0 | | REAL: passes |
| closed -> interim (36), macro -> closed / interim | 541,312 | 0 | +73.9 | 0 | | passes |

None of −577 ps is real and none is common-phase clocking: 72,192 endpoints (TNS −41.1 s of −62.6 s) are the single-clock
interim cfifo; the other 1.12 M sit at ≥ −33.3 ps and are the interim cq constant against the 50-ps die hold uncertainty.

## Netlist / route warnings

- `rd_out size 72 does not match net size 48`: 12,544 cfg ROMs `c<0..1791>_<0..6>` + 3 `pqrom*` (ot_rom_4096x72_m8). The die
  connects the 48 used bits; 24 outputs per macro float (301,128 bits). No timing endpoint; make the unused slice explicit in die.v.
- GRT-0241 `does not have global route`: nets whose two pins share one 9.6-um gcell (abutted qbank / node / rstg pins);
  6,136,530 nets routed, congestion 0. They carry 0 wire in the SPEF (true to < 10 um).

## What it decides

1. Bind the colck `dsfd_cfifo` view in the timing kit (after its capture-edge re-route: the pair check measures a REAL
   FF hold −206 ps on `station.do0 -> cfifo.xd` and −94..−164 on 8 m221pq end relays; those are the real hold defects, and
   they are not in this STA because both ends were interim here).
2. Interim lib: an FF cq of 32 ps against hold 15 + 50 can never pass a short hop; a placeholder must carry the pin-registered
   contract minimum (clk -> pin ≥ 65 ps FF) or the hop is reported as `placeholder` and not as a die hold failure.
3. The 4,213 SS endpoints `rly_63_WS -> rly_63_NS` (374 um) are the only real-view misses, at the non-sign-off corner.
