# DIE-HEAD-51 helper st: HEAD START stages re-anchored on the l48c die clock (start-skew rows actually timed)

Data on intel2 `/srv/opentallas-scratch2/claude/die-head-48/st51/`.

## Root cause
- The count-align bind (`die-head-47/sta/bind_l47k.json` = Codex hk5_leaf2 bind + l47k K values) keeps the START tree
  of the hk5 (08-28) clock tree: 1251 virtual stages (`head_source_l48w/start_stages_src25q.json`, unicode paths).
  None of those node keys exist in the l48c die_trial tree (base36), so `virtual_tap()` found no taps: 1607/1607 'no taps'.
- A second, independent block: 1463/1607 start ports sample on the FALL edge, and `proof_l48c` has no fall arrivals
  (its arr files carry only T/N rows; N rows are the raw Y rise, not polarity-resolved). With matching keys those rows
  would still fail closed.
- The l48c die clock does not drive the `t_st_*__clk` ports at all (no t_st taps in the clock kit); the start stages are timed only
  by the virtual model (node arrival + median tap leg), the same model the bind was built with.

## What was built (no RTL change, plan of record untouched)
1. `edge.sh`: the same l48c combo GRT (`clk/out_l48c_<C>/combo.tcl`, deterministic: arr_TT/FF byte-identical to the
   record) plus the FLOW-ONEMODEL-2 readout (`die_trial.py readout ctree.v --cells 'ck_*' --prefix ck_`).
   Merged T rows (with slew) + F/N/M rows -> `trial_tap_arrivals` -> `proof_l48c_e` (tap rise identical to
   proof_l48c, node falls 26465/26465, node rise polarity-resolved, CPPR range diff <= 4.6 ps).
2. `st_remap.py --leaf --radius 700 --any-node --want 25`: every stage keeps its RTL, placement, parent/children and edge;
   its clock pin is re-hung on an l48c tree node within 700 um (hop p50 89 / p90 381 / max 700 um).
   Output `bind_l48w.json` (sha256 5254120ba647); only start_ports launch/capture become `__st__<base36>@<stage id>`,
   map in `start_tree_remap`.

## Die STA (run_single.sh, PLAN head_source_l48w/source_plan.json)
| run | proof | bind | start-skew TT/FF | CA lo TT/FF | contract viol | gate |
|---|---|---|---|---|---|---|
| sta/o_l48w_single (lane) | proof_l48c | bind_l47k | 1607/1607 fail, 1607/1607 fail | 211.9 / 241.6 | 3214 | FAIL |
| st51/o_e_oldbind | proof_l48c_e | bind_l47k | 1607/1607 fail, 1607/1607 fail | 211.7 / 241.6 | 3214 | FAIL |
| st51/o_e_l48w (W 0) | proof_l48c_e | bind_l48w_w0 | 0/1607, 0/1607 | 211.7 / 241.6 | 0 | BLOCKED(kits) |
| st51/o_e_l48w25 | proof_l48c_e | **bind_l48w** | 0/1607, 0/1607 | 211.7 / 241.6 | 0 | BLOCKED(kits) |

TT setup +257.36 in every run; intra/seam rows unchanged by the proof change. The only remaining gate reason is
530106 hold pairs without signed real views (OWNER 12.19). Worst start sync distance by st_remap's own evaluation
(same functions): W25 TT 56.0 / FF 58.7 ps (W0: 27.2 / 30.0) vs aperture 26.5.

## Open
- Physical: the die clock must actually drive the 1251 `t_st_<cell>__clk` ports from the mapped nodes (ot_clk / ctree
  taps), then combo GRT and `start_stage_emit.py proof` measure them instead of the model. Hops up to 700 um on a trunk node are
  modelled as the median leaf leg (UNCHECKED).
- Topology: the hk5 start tree does not follow the l48c clock topology (the topology-preserving remap needs mm hops).
  If the measured stage taps fail, the clean fix is a START re-plan + re-emit on the current proof
  (die-head-33/start/leaf.sh recipe: count_align_plan --start-tree clock -> leaf_bind -> start_stage_emit), which
  changes `ot_die_start_stages` + the t_st top ports + the reset fit (RTL, plan event).

## l48w-st die clock event (2026-10-31 17:22 PDT)
st_ctree.py hangs the 1251 t_st_*__clk stage pins on bind_l48w nodes (start_stage_emit ctree patch form; optional BUFx8 entry buffer per stage).
clk_st*.sh = l48c combo GRT + both-edge readout; mkproof*.sh = trial_tap_arrivals + start_stage_emit proof.
a (direct legs): GRT ovf 0, existing taps moved up to +318 ps, 6 max-slew violators -> rejected.
b (entry buffer at node): existing taps |d| p50 1.0 / max 27.6 ps TT; die STA start-skew fail 12/1607 TT, 8/1607 FF; 20 contract violations; TT setup +199.1.
Fails = long buffer->pin legs (hop 300-700 um, slew 300-570 ps, measured 60-200 ps later than the virtual model).

## l48w-st fix variants (2026-10-31 17:44 PDT); chosen: g
Gate start-skew fail TT/FF, contract violations (= the start-skew fails), TT setup:
c bind_l48w + pin-end BUFx8 (>250 um): 15/10, 25, +241.7 (pin-buffer inputs slew to 585 ps)
d rebind cap 250 + leg model: 0/1, 1, +228.2;  e rebind r700 + leg model: 2/0, 2, +199.5
f = d + BUFx8 chain every 150 um + pin buffer: 1/1, 2, +254.3
g = e + chain (1963 buffers): 0/0, 0, TT setup +254.70, gate BLOCKED(kits) (530106 hold pairs without signed views), worst gate sync 51.9 TT / 105.7 FF
Why: the gate characterises clk->Q at the MAX tap slew; unbuffered stage legs (slew to 565 ps) raised clk->Q of every start port (TT 49/82 -> 108/138 ps). The chain keeps stage slew <=13.4 ps.
g bind: intel2 die-head-48/clk_st51/bind_l48w_dm700.json sha256 782ddc71c537 (st_remap.py --leaf --radius 700 --any-node --want 25 --leg-model 0.09,0.00023, proof base_b);
build: run_v.sh g BIND 0 150; proof clk_st51/proof_l48w_stg; STA clk_st51/o_l48w_stg.
