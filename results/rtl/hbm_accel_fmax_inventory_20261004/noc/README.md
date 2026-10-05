# noc family: 1.2 GHz closure of the DS HBM collective path (2026-10-04)

Sign-off: 0.833 ns, SS setup with 60 ps uncertainty, FF hold with 25 ps (`tools/w18/corner_sta.py`). The rows are in `closure.json`, built by `build_closure.py` from `closure_spec.json` and the small route copies in `routes/`.

## On the path
| block | result |
|---|---|
| `ot_gpu_bd_line` | **closed** as built: SS +154.07 ps, FF +7.47 ps, no false path |
| `ot_gpu_mreq_cdc` → `ot_gpu_mreq_cdc_oh` | **closed**: SS +121.55 r2r / +22.98 worst, FF +11.23. Before: output port -110.75 ps. Zero cycles added |
| `ot_gpu_coll_endpoint` + `ot_gpu_coll_mux` → `_f12` successors | **not closed**: before -1.70 ns (HA3 ctx); f12 revisions -242 → -96 → **-4.23 ps** (r6, XREG=1; FF +4.13). Last cone (TX lane mask) fixed in r7 (source in `routes/collctx_f12x_r7_src/`, exact) and in Codex's `ot_gpu_coll_endpoint_f12_txmask`; route loop handed to Codex. +2 clk_sm per collective, 0 per record |
| `ot_ha2_owner_reduce` (the HA2 reducer, priced by TU `reducer_cycles`) | lockstep-exact (768 results, 0 mismatches). The full-shape flat route is still in placement (`ha2red_sr1_r4`) |

Handed to Codex: `/tmp/claude-review-20261003/handoff_to_codex_20261004/hbm_fmax_noc.md`.

## Off the path (with evidence in `closure.json`)
- HA2 direct-link fabric.
- W15 NVLS switch: screen 301 MHz.
- `ot_gpu_coll_fabric`: a stand-in for links and the switch.
- gpu_sys memsys:
  - xbar screen -1,087 ps;
  - the L2 needs a macro array;
  - the partition is behavioural.
  - Not closed; the blocker is listed.

## Collective term
- **Endpoint:** +2 × 0.833 ns × 265 collectives per token = +0.44 µs. The collective term goes from 201.92 to 202.36 µs, and the rate from 2,225.7 to 2,223.5 tok/s. Expressed through the W15 leg constants, this is `leg_delta_ns` +0.833 per leg.
- **Reducer, if SLOTREG=1:** goes from 22 to 23 cycles, adding +0.83 ns per all-reduce (×40 all-reduces per token).

## Replay (compute hosts only)
```
# exactness (EPYC): endpoint/mux successors on the unmodified collective bench, CDC FIFO bench, mux lockstep
python3 results/rtl/hbm_accel_fmax_inventory_20261004/noc/coll/run_coll_f12.py --xreg 1 --out coll_f12_r7.json --work W --seeds 1,2,3
python3 results/rtl/hbm_accel_fmax_inventory_20261004/noc/coll/run_cdc_fifo_oh.py --out cdc.json --build-dir W --wdup 8
verilator --binary --timing --top-module tb_coll_mux_ls rtl/gpu_sys/ot_gpu_coll_mux{,_f12}.sv rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv noc/coll/tb_coll_mux_ls.sv
# HA2 reducer lockstep (DS shape, 96 dies, ~35 min a seed)
results/rtl/hbm_accel_fmax_inventory_20261004/noc/ha2/ls_campaign.sh WORKDIR 1 1 2 3
# routes: jobs/route.sh <label> <top> "<sources/params>" ; e.g. the endpoint in the HA3-style registered context:
jobs/route.sh collctx_f12x_r7 noc_tw_coll_ctx_f12x "--source rtl/link/ot_link_afifo.sv --source rtl/gpu_sys/ot_gpu_cdc_fifo.sv \
  --source rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv --source rtl/gpu_sys/ot_gpu_coll_mux.sv --source rtl/gpu_sys/ot_gpu_coll_mux_f12.sv \
  --source rtl/gpu_sys/ot_gpu_coll_endpoint.sv --source rtl/gpu_sys/ot_gpu_coll_endpoint_f12.sv \
  --source results/rtl/hbm_accel_fmax_inventory_20261004/noc/wrappers/noc_tw_coll_ctx.sv --false-path-io \
  --die-area 0 0 540 540 --core-area 2.16 2.16 538.84 538.84"
python3 results/rtl/hbm_accel_fmax_inventory_20261004/noc/build_closure.py
```

## Notes
- **Context wrapper (`--false-path-io`):** every port is registered on both sides, as in HA3's `ot_hbm_accel_coll_port_ctx`. `clk_link` is tied to `clk_sm`, which is pessimistic for the Gray pointers.
- **Route copies of earlier RTL revisions** (`collctx_f12_r0`, `_r2`, `_f12x_r2`, `_r6`, `_f12x_r6`) are progression evidence only.
- **Bench verdict:** `run_cdc_fifo_oh` reports FAIL only on lint DECLFILENAME (two modules share one file). The bench itself passes.
