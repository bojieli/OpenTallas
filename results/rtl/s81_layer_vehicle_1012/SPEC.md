# S81 layer vehicle (DeepSeek-V4.1 ROM die, one layer per type + head at P 1,048,575)

Owner: el1011-s81lv (2026-10-12). Log: `/home/ubuntu/claude-takeover-20261007/el1011-s81die.log` (`[s81lv]` lines).
Owner rules this implements: full-system RTL (control, data loading, collective, MTP all real, nothing tied off);
one layer per type + head at the target context on the smallest vehicle; simulate the minimum component;
transaction-level exactness at the boundary.

## 0. Starting point (correction to `die_sim_inventory_1012`)

The inventory (main 99bc88ae4) found no S81 layer vehicle. One exists, unmerged, on `claude/el1011-s81dbench`
(s81die-1011, 6aeabf19e, merged here): `rtl/dsrom_sys/s81_ctrl/test/tb_s81_die_layer.sv` +
`tools/s81_ctrl/die_layer_stim.py` + `run_die_layer.sh`. Gate3 (EPYC3 `/srv/opentallas-scratch/claude/s81die-bench/gate3`):
base L0 PASS (11,168 layer cycles), base L2 PASS (20,360), seqc L2 PASS (3 jobs), 6/6 mutants FAIL, **seqc L0 FAIL**
(peers 1-3 issue an engine-0 command at cycle 1513, done tags off by one). This vehicle is the base; the work below
replaces its behavioural engines with the closed element RTL, adds the missing seams and layer types, and fixes seqc L0.

## 1. Elements of one S81 layer (die contract `results/arch/hier_contract_1011/s81.json`)

| Slot | Element RTL (main) | In gate3 | Target in the vehicle |
|---|---|---|---|
| sp_wfc (control) | `dsfd_stage_seq_c` (decision A, WFC kit) / `dsfd_sp_ctrl_e` | real | real; seqc L0 fixed; kit is the production controller |
| sp_gather, sp_capture | `dsfd_sp_gather_c`, `dsfd_sp_capture_c` | real | real |
| rep/q_elem (1,898 inst) | `ot_v41_rom_elem_q_*` | reference roots (`ot_v41_ret_root`) | 1 real column of q_elem per field phase on rank 0, rest replayed from the golden (TLM) |
| rep/pqc | `ot_v41_pqc_spine_screen`, `ot_pqc_t_*`, `ot_s81_pq_ret_root_cam_p` | absent | 1 real PQC chain on the field return path of the indexer/score phase |
| rep/bf (519) | `dsfd_bf` | absent | 1 real instance on its field phase |
| sp_su_s | `dsfd_sp_su_c` (gate closed 28e66b4d4) | behavioural (port 1) | real |
| sp_hc_s | `dsfd_sp_hc_c` | real | real (+ hcx coefficient producers behavioural until their RTL masters exist; listed as an open gap) |
| sp_collective | `dsfd_sp_collective_c` 4-die TP4, `ot_dsrom_link_chan` | real | real |
| sp_vm | `dsfd_sp_vm_m` (`dsfd_vm_fe` + `dsfd_vm_bgq28` + `dsfd_vm_be_sl`) | bench VM array | real VM: FE + one bgq28 bank group + BE slices; remaining bank groups as an address-checked TLM |
| svc (HBM service) | `dsfd_svc_c` | behavioural (port 4) | real; HBM side = TLM (below) |
| rep/engram_c | `dsfd_engram_lkp` (+ `ot_dsrom_engram_lead_producer`) | absent | real on L1 (and L14 if run) |
| rep/hrow + MTP | `ot_dsrom_mtp_hrow*`, `dsfd_mtp_seq_rtt`, `dsfd_vm_wfc_ep`, `dsfd_coll_mtp_ep` | absent | real: hrow capture of the layer's h + MTP sequencer handshake on the head run |

## 2. Seams (each gets a mutant that must FAIL)

| # | Seam | Check | Mutant |
|---|---|---|---|
| S1 | controller -> masters (c_cmd / c_done / c_st, `ot_s81_slab_ep`) | done order, once, dataflow | `MUT=2` wrong done tag (exists) |
| S2 | VM -> gather -> field (q_elem / bf / pqc) -> capture -> VM | capture writes = golden rows | `MUT=4` dropped done (exists); new: real q_elem column operand slip |
| S3 | VM <-> SU (QN/KV/QB/SW/SE/SO) | SU output rows = CPU golden bit-exact | SU `m1` early done |
| S4 | VM <-> HC (GAIN/H_LOAD/COEF/NORM/POST/H_STORE) | NORM + H_STORE rows exact | `HMUT=1` (exists), `INP1` (exists) |
| S5 | collective <-> link chan (TP4) and -> HC y bus | 4-die outputs = C8 ref, y exact | `OT_S81PH_MUT_TREP` (exists) |
| S6 | HBM (TLM) -> svc -> VM: KV / index rows at 1M | rows landed = exporter rows, tag order | svc response tag / beat slip |
| S7 | engram lookup -> VM (L1) | engram rows = golden | wrong bucket index |
| S8 | layer h -> hrow / MTP sequencer (head) | hrow row = golden h; MTP draft seed handshake | hrow write dropped |
| S9 | field -> PQC -> capture | screened set / quant row exact | PQC compare off by one |

## 3. Boundary models (transaction-level, the only non-RTL parts)

- **HBM die (KV, compressed-KV, indexer rows at P 1,048,575)**: a replay model on `dsfd_svc_c`'s HBM request/response
  ports. It answers each request with the exporter's bytes for that address (`hbm.bin` / per-record `hbmw.bin` of
  `python3 -m hgi_e2e.export ds --refs <1M refs> --layer N`, rank-0 view, EPYC1 `/srv/opentallas-scratch/claude/diesim-1012`
  exports), and fails on any request outside the recorded ranges. Latency: fixed + jitter (seeded), credit-limited.
- **Cross-die links**: TP4 peers are real collective slabs (unchanged from gate3). The pipeline-stage hop to the next
  stage die (`ot_s81_hop_tx` out / HIDDEN payload in) is a TLM sink/source: it checks the layer output h against the
  golden and supplies the next job's HIDDEN rows.
- **ROM field beyond the representative real instances**: replay of the golden partial sums at the same field
  phase timing (reference roots, as gate3), cross-checked against the real instance on its rows.
- **Host**: program writes (pw_*), doorbell; no data path.

## 4. Vectors and golden

- Data golden: the 1M-token chain (`tools/dshbm_baseline_measure.py` `build_chains(..., 1048575, ...)`, snapshots
  sha256 cd0fc866...; pinned `su_cases_v2_ildr.pkl` 8c18c065 = L0, L2, head). Extend the dump layers to L1, L20,
  L37 (same tool, `LAYERS`/`exec_layers`, refs only on EPYC1) -> `su_cases_v3_lv.pkl`, sha pinned in this record.
- HBM-side feed: the HGI exporter per-layer directories (L0 L1 L2 L20 L37, L39 + head) already exported for the
  HBM die campaign; the S81 replay reads only the KV / index records of rank 0.
- Layer types run: L0, L1 (engram), L2, L20, L37, head (final norm + argmax + MTP seed). Each base run must PASS and
  each seam mutant FAIL on L0 (S7 on L1, S8 on head).

## 5. Run plan

Verilator 5.050 on ot-epyc3 (or ot-epyc1tb when below load ~200) via `ot-heavy --mem <GB>`, scratch
`/srv/opentallas-scratch/claude/s81lv/`. Cap 24 h per run (gate3 L2 ran ~20k cycles in minutes; the real VM/SU add
cycles, not hours). Record: `results/rtl/s81_layer_vehicle_1012/bench_record.json` (per layer: PASS/FAIL, layer
cycles, rows checked; per mutant: FAIL reason; source sha256s; commit).

## 6. Open gaps (stated, not hidden)

- hcx coefficient producers (fn / sumsq / rsqrt / pre_post / sinkhorn) have no S81 master RTL in the HC slab yet;
  they stay behavioural ports writing golden rows until the HC owner adds them.
- `dsfd_sp_pq` / `dsfd_pq_root` (PQC slab masters) are unowned in the die contract (`rep/pqc` assembly pending_owner).
- PQC claim checked (2026-10-12): every closed PQC element has a bit-exact element bench + failing mutant on main
  (`tools/s81/pqc_xrv_bench.py` for `ot_v41_pqc_spine_screen` = 9 `ot_pqc_t_*` tiles + `ot_dsrom_aq12t`;
  `physical/s81_pq_tiles/bench_aq12t.sh`; `tools/s81/pq_root_cam_p_gate.py` for `ot_s81_pq_ret_root_cam_p`). Their
  vectors are seeded synthetic, not the 1M token: S9 in this vehicle is the first PQC run on production data.
  Tiles prom / srom / xin have no in-tile mutant (only the bench-level legacy-read negative).
