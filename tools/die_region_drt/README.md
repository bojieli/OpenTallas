# Die-region detailed route (GRT-vs-DRT error bar)

Dies are closed at the die level by a full-die global route (GRT) and STA on GRT parasitics; no flat full-die detailed
route is run. This tool measures how far that global route is from a real detailed route by cutting windows out of the
die's own GRT checkpoint and detail-routing them. It works on any die odb that carries GRT guides (Qwen ROM / KV,
S81, HBM).

## Use

```
# 1. windows from the die GRT (host, plain python + numpy; ~20 s KV, ~2 min S81)
python3 tools/die_region_drt/region_drt.py pick --guide grt/route.guide --def <placed DEF or components dump> \
    --lef <element LEFs...> [--congestion-rpt grt/grt_congestion.rpt] --out windows.json
# 2. one run dir per window
python3 tools/die_region_drt/region_drt.py stage --ckpt grt/ckpt_grt.odb --spef grt/die_grt.spef \
    --libs <dir of *_<c>.lib | kit/libs_{c}.txt> --clock-lat <dir of clock_lat_<c>.tcl | kit/latency_{c}.tcl> \
    --out <run>/<window> --win x0,y0,x1,y1 [--threads 16 --mem 120 --drt-iters 64]
nohup <run>/<window>/start_region.sh &      # STATUS.log; compare.json at the end
```

`start_region.sh`: cut (openroad -python) -> filter the die GRT SPEF to the window's internal nets -> DRT on the clipped
die guides (+ write_def, RCX) -> STA TT setup / FF hold on GRT SPEF and on RCX SPEF -> `compare`.

## Windows (`pick`)

| name | rule |
|---|---|
| cong | most GRT overflow gcells (congestion report) in a window; without a report, the highest mean max-layer guide utilisation (guide tracks / layer capacity after the die GRT's layer adjustments and block OBS) |
| relay | the longest relay-hop net (`__r` in its name; otherwise the longest non-clock/reset net) by guide HPWL, the window grown to hold it |
| ioedge | the IO macro (`phy|serdes|ucie`) face window against its die edge with the most guide demand |
| column | the full-height column with the most guide demand, then its densest window |

Windows never overlap.

## Cut semantics

- Instances fully inside the window are kept as FIXED real abstracts (their LEF OBS and pins).
- An instance crossing the window edge (e.g. a 12 mm KV column) is an *intruder*: its in-window body becomes obstructions
  on its OBS layers and its in-window signal pins become fixed terminals of their nets. (The earlier
  `tools/qwen_die_region_guided.py` grew the region box to every kept instance; with die-height columns that is the
  whole die height.)
- Every die net that leaves the window gets a terminal where its die guide crosses the edge, on that guide's layer, on a
  free track clear of the window's same-layer blockers; nets with no crossing guide get a projected M8/M9 terminal.
  Die IO terminals inside the window are kept.
- Guides are clipped to the window; pieces not connected to a pin are dropped; a net in several pinned pieces gets a
  bounding-box guide. The PDN special wires are clipped (no PDN re-run). Clock / reset nets (special in the die GRT
  checkpoint; built by the die clock tree) are not routed.
- Layer contract: die nets route M4-M9. Block abstracts own M1-M7 (tile signals <= M6, tile PG M7), so over a block
  body only M8/M9 carry die nets; `compare` counts die metal on a block's OBS layers inside its body (must be 0).
- Pin keepout is ABOVE ONLY: the tool never obstructs the layer below a block pin; `cut` audits that the layer above
  every kept face pin is not covered by the die's own shapes (PDN, intruder obstructions) (`pin_access_above_only`).

## Error bar (`compare.json`)

- DRC: total and classes (type@layer) from `drt_drc.rpt`; DRT iteration trace.
- Wire length: per-net DRT / GRT (`report_wire_length` on the clipped guides vs the detailed route), total ratio,
  median, p95 |delta| (nets >= 20 um); per-layer length guides vs DRT.
- Vias: GRT layer changes (touching adjacent-layer guide pairs) vs DRT via instances.
- STA: per-endpoint slack RCX - GRT on identical libs / clocks, TT setup and FF hold, all and relay endpoints only.
  GRT side = the die GRT SPEF of record filtered to the window's internal nets (every endpoint kept); clocks = the die
  clock plan's per-sink latencies applied at the sink pins (the die clock tree is outside the window).

## Flow problems found and fixed (2026-10-12 pilot)

1. `dbTransform.apply(Rect)` has no Python overload in the pinned OpenROAD (26Q3): pin shapes are placed with an
   explicit orientation map.
2. The die GRT SPEF is written by the resizer without a `*NAME_MAP`; the filter handles both forms (the first version
   copied the whole 950 MB file).
3. Region growth to kept instances (qwen guided cut) does not work with die-height columns -> intruder handling above.
4. GRT products written by root containers (mode 644) cannot be hard-linked by `ubuntu` under
   `fs.protected_hardlinks`; link them from a root container (or copy) so a lead's cleanup cannot pull them away.
5. Two dies with the same window name collided on container names; the name now carries the die dir.
6. On S81 no hop net carries `__r`, and the fallback picked `refclk` (a 14 mm clock net): clock/reset nets are skipped
   and the relay window is capped (`--max-win-um`).
7. Lib and clock-latency inputs differ per die (KV: lib dir + `clock_lat_<c>.tcl` with `get_pins ... set_clock_latency
   V`; S81: `libs_<c>.txt` lists + `latency_<c>.tcl` with `set_clock_latency V [get_pins ...]`); both are accepted.

Results: `results/physical/die_region_drt_1012/`.
