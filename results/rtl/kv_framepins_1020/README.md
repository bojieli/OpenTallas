# KV-FRAMEPINS 10-20: frame pin groups + real readers for the dcal / d2d status outputs (OBSX)

Branch `claude/kv-framepins-1019` (from GEN9 `claude/kv-gen9-1019` 3332a9408).  Die flag `OT_KV_HOST_OBSX=1` (needs
`OT_KV_MU=1 OT_KV_HOST_OBS=1 OT_KV_DCAL_BC=1 OT_KV_DCAL_BC4=1` and the static die; default off, so runs without the flag
are byte-identical).

## Problem
After KV-BIND5-OBS (the 43 HOST-root outputs -> HOST CSR window 0x1800-0x19FF) the GEN9 bind still had five open outputs
with NO frame pin group: dcal (`qkd_d2d_cal_seq_pin_bc4`) `adm_done / cal_ready / running / layer` and the D2D end's
`recovery_cycles`.  The KV-BIND5 classification marks them OBSERVATION-ONLY (no reader inside their masters).

## Architectural choice: HOST window, not the health plane
These are status VALUES (levels, a 6-b run index, a 32-b counter), not faults.  The health plane (kv_health_plane.py) is a
1-bit sticky OR fold into STATUS; folding values into it is wrong and would cost STATUS edges.  The HOST already reads
die observations through the window: the five join the window snapshot.  `dcal.fault` stays on the health plane (KV-BIND4).

## Design
* `gen_host_root_obs.py --ext` -> `rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obsx.sv` (+ `host_obs_map_x.json`):
  the OBS root plus inputs `obs_dcal_adm_done / cal_ready / running / layer[5:0]`, `obs_d2d_recovery_cycles[31:0]`, added to
  the window bus above the 1,335 HOST bits (LSB 1335..1375).  NB 1376 + NF 71 = 46 words (0x1900-0x19B4, still in the
  window).  Module names end in `_obsx`; the OBS file is unchanged (`--check` UP TO DATE).
* Frame pin groups (kv_die `HOST_RT_OBSX`): dcal `dob` = {adm_done, cal_ready, running} (new) + `lay` = layer (existing
  group, had no bus); d2ds `rcy` = recovery_cycles (new); HOST `odc / odl / odr`.  The producers are the closed views
  (bc4 LEF has adm_done / cal_ready / running / layer[5:0]; r7w_sfm2 LEF has recovery_cycles[31:0]): no view change.
* Die buses (kv_static_die OBSX): `ks_obs_dcal` 3 b, `ks_obs_dlay` 6 b, `ks_obs_rcy` 32 b, class `kv_oneway` (the
  same as the ks_host_* joins): the relay pass gives them registered qkd_rlys stations at <= 405 um a hop.  All three
  are on `n_clk_core_c`, the same clock as the HOST and dcal / d2d_kv in the gen9d netlist.  No tie, no stub; producers unchanged.
* `kv_open_tail_roles.py`: GENERATOR SHA re-pinned for the kv_static_die edit (the OBSX block only; no PC / GRP chain text).

## Cycle price
0 token edges, 0 die-calendar edges, 0 STATUS edges (off every token path; read by the host).  The snapshot sees each
source `relay_stages(bus)` edges late.  Equal stage counts give equal edge ages in the common-edge RTL model. They do not prove physical multi-bit coherence across regional clock trees.
`relay_stages` comes from the relay plan of the next GEN9 prep.  The bench is parameterised by it (3 / 3 / 4 here).  Window read latency unchanged
(fixed 3 edges after AR).  Area: +41 window pin-register flops in the HOST cluster plus the relay stations.

## Evidence
* Bench `tools/qwen_kv_die/obsx_path_bench.sh MUT OUT` (tb `rtl/test/qwen_host/tb_kv_obsx_path.sv`): sources -> chains of
  the closed `qkd_rlys_36` relay standard -> `qkd_host_obs_csr` at the OBSX shape, read from `host_obs_map_x.json`.
  Verilator 5.050 (ot-epyc5): `bench_m0.log` PASS (12 captures, 46 words; each ext field equals its source exactly
  relay-stages edges before the snapshot edge; HOST bits intact; fixed 3-edge reads; CSR pass-through).
  Mutants FAIL: m1 capture dead, m2 word i+1, m4 pass-through data replaced, m5 ext wired 1 bit low (wrong map), m6 one
  relay stage more than priced (`bench_m{1,2,4,5,6}.log`).  m3 (flt not sticky) PASSES here by design: this bench drives no
  fault pulses.  Sticky flt stays covered by the KV-BIND5 window bench (results/rtl/kv_bind5_obs_1019/bench_m3.log FAIL).
* Verilator 5.050 elaboration lint of `qkd_host_root_admission_obsx` with the die parameters (host_obs_lint.sh): 0 errors.
* Bind A/B (`ab.sh`, `patch_b.py`, `summ.py`): die_port_bind v2 on the KV-BIND3 bound gen9d netlist (ep5
  kv-bind3-1019/bind_try4, sha 9822db17).  a = HOST master `_obs` (the KV-BIND5 state); b = master `_obsx` plus the three
  OBSX buses as direct nets.  In the die these are relayed buses whose qkd_rlys stations bind separately; the
  producer-pin -> reader-pin connectivity is the same.
  a: OBSX-target opens **5** (dcal adm_done/cal_ready/layer/running, d2d recovery_cycles), total OUTPUT_OPEN 26.
  b: OBSX-target opens **0**, total 21; `qkd_host_root_admission_obsx` PASS (0 unconnected, 0 width mismatch, 0
  not-in-RTL); dcal residue = `fault` only (the health plane reads it in the KV-BIND4 netlists, which are newer than this one).
  Other residue unchanged (the tail roles, plus d2d att_rx_slot / kvn_word_* of this older netlist).
* Owed: a full GEN9 prep with `OT_KV_HOST_OBSX=1` (relay plan stage counts, die_top_lint, strict bind on a freshly laned die).

## SAFE-DESIGN checklist (die buses + window growth)
1 pins: sources are registered outputs of closed views, and the window pin registers take the bits (PASS).  2 reach:
kv_oneway relay plan, <= 405 um a hop (PASS by construction; stage counts come from prep).  3 fanout: the capture enable is
already sliced per 32 b (+2 slices) (PASS).  4 depth: the read mux is unchanged (64-word padded) (PASS).  5 storage: +41
flops (PASS).  6/7 floorplan / clock: same core clock, regional relay stations (host cluster owner, KV-HOST).
8 schedule: static, off the token schedule; observation lag priced above (PASS).

## CODEX sticky coverage completion

The updated actual OBSX-shape path bench now injects one-edge fault pulses, removes them before capture, and checks every sticky fault bit in the window against an independent accumulated vector. Fleet Verilator 5.050: positive PASS (46 words, 12 captures); all six mutants m1 through m6 FAIL, including m3 (12 sticky errors). Exact witnesses and source hashes are in `sticky/`. The earlier m3 PASS remains historical evidence of the prior coverage gap. Production source is unchanged from d8221c4bf; this completion changes the bench only. No native census or physical qualification is claimed.

## Physical coherence HOLD

OBSX remains diagnostic. Its current bench drives sources, relay clocks and HOST sampling from one ideal edge. It proves RTL connectivity, fixed edge lag and CSR snapshot/read behavior in that model. It does not establish the actual source-to-relay-to-HOST phase relationship, a stable sampling aperture, or atomic landing across regional clock trees. No completed fresh GEN9 manifest or native clock/landing receipt currently supplies those facts. Before adoption, each of the three buses needs source and receiver clock ownership, measured or bounded phase/skew at the flops, a legal stable window including data transitions at the boundary, and an atomic landed transfer if the clocks differ. CSR capture copies also need actual clock/timing qualification. Equal relay-stage counts and observer status do not waive these requirements.

The generator default-output check passes against the GEN9 baseline (3332a9408). The current origin/main snapshot has no OBS root artifact, so equality to a main-existing OBS output is not claimed. ROOT must compose the prerequisite OBS generator/root first, preserve its default bytes, and recompute kv_open_tail_roles.GENERATOR against the actual composed kv_static_die.py; the GEN9 hash 79939e3d is not a transferable main receipt.
