# KV-BIND5-OBS 10-19: HOST observation window (real reader of the bind-v2 OUTPUT_OPEN observation ports)

Branch `claude/kv-bind5-obs-1019` (from GEN9 `725008993`).  Die flag `OT_KV_HOST_OBS=1` (needs `OT_KV_MU=1`).

## Problem
Bind v2 on the GEN9 KV die (KV-BIND3 replay, `pass2_fixed.json`) leaves 50 OUTPUT_OPEN ports; after KV-BIND4 (KC kf +
dcal fault -> health plane) the residue is: 40 `qkd_host_root_admission(_mu)` outputs, dcal `adm_done / cal_ready /
running / layer`, d2d `recovery_cycles`.  None has a frame pin group: they are observations of the HOST, not die signals.

## Classification (structural, `tools/qwen_kv_die/kv_host_obs_classify.py`: flattened + opt_clean'ed master, readers per bit)
| port(s) | class | reader now |
|---|---|---|
| 31 CSR / trace / certificate outputs (hc 182, native_pr 143, participant_trace 256 / token 144 / pos 144, marker 66 + v, issued / landed 32, program_auth_* / footer / expected_*, local_service_epoch, service_diag_raw, physical_ack_n, accepted_ranks, dispatch_valid / dispatched, engine_result_cr, available, record_tx_v, program_consensus, recovery_complete, host_admission_open / deferred, ingest_permission, service_ready) | observation | HOST CSR window snapshot |
| 9 fault-class (package_abort, service_abort, record_fault, peer_protocol_fault, coordinator_fault, irq, seen 8, service_faults 25, fault_src 32 = 71 b) | host fault / abort / health | window snapshot + STICKY vector (already terminal inside the root: guard raw_faults / CSR FAULT_STATUS) |
| dcal adm_done / cal_ready / running / layer (9 b) | OBS_ONLY (no reader inside the bc4 master) | PENDING: window input reserved (`EXT_PENDING`), needs a dcal frame group + HOST frame group (KV-DCAL2 / KV-GEN9) |
| d2d recovery_cycles (32 b) | OBS_ONLY (no reader inside qkd_d2d_static) | PENDING: same (KV-D2D / KV-GEN9) |
No port is waived, tied or deleted; the producers are unchanged.

## Design
* `rtl/qwen_sys/kv_host_obs_20261019/qkd_host_obs_csr.sv`: AXI4-Lite window on the EXISTING host register path, between the
  packet AXI master (`u_packet.u_axi`) and the control CSR slave (`u_control` -> `qkd_host_sys_csr_service`) inside
  `qkd_host_control_packet_admission`.  Window = free part of the CSR system region:
  `0x1800 OBS_CTRL` (W [0] CAPTURE, [1] CLEAR sticky; R {0x0B, NW, capture count}), `0x1804 OBS_NB` ({NF, NB}),
  `0x1900 + 4 i` snapshot words (i < 43).  Every other address passes through unchanged (combinational split, the CSR's own
  [12] split style; one transaction at a time, ot_host_if handshake).
* Storage: the obs pin registers ARE the snapshot (load-enable = registered CAPTURE replicated per 32-bit slice, 43 kept
  copies, <= 32 loads each); flt = live pin reg + sticky + snapshot.  ~1,301 + 213 + 8x32 + 32 flops; no SRAM (< 2 kb).
* Root successor `qkd_host_root_admission_obs` (generated, `tools/qwen_kv_die/mu_peer/gen_host_root_obs.py` from the
  UNCHANGED MU root): the 40 outputs leave the root port list (internal nets -> `obs_bits` 1,301 b / `obs_flt` 71 b),
  threaded through `qkd_host_rank_services_admission_obs` -> `qkd_host_control_packet_admission_obs` -> `u_obs`.
  Bit map: `host_obs_map.json`.  `--check` verifies the generated file.
* Die: `kv_die.py` `OT_KV_HOST_OBS=1` binds the obs root as the `qkd_host_rt` frame RTL.  Frame pin groups unchanged (none
  of the 40 had a group), so no die netlist / LEF change.

## Cycle price
0 die-calendar edges, 0 STATUS edges (STATUS 1989 <= 1998 unchanged), off every token path: the window is read by the
host.  A window read = 3 ck_csr edges after the AR handshake (fixed), vs 2 for a CSR register; CAPTURE takes effect 1 edge
after its write handshake.

## Evidence
Verilator 5.050 (fleet ep5): `bench_m0.log` PASS (43 words, 6 captures; snapshot exact, later obs changes unseen, 1-cycle
fault pulse sticky until CLEAR, fixed 3-edge latency, 6 pass-through CSR writes + interleaved CSR reads with the slave's own
data); `bench_m0_nb1471_nf97.log` PASS (other shape).  Mutants FAIL: m1 capture dead, m2 word i+1, m3 flt not sticky,
m4 pass-through data replaced (fail witnesses `bench_m{1..4}.log`).
Bench: `tools/qwen_kv_die/host_obs_bench.sh MUT OUT`; elaboration lint: `tools/qwen_kv_die/host_obs_lint.sh MASTER OUT`.

## SAFE-DESIGN checklist (RTL block; physical home = host cluster, see below)
1 pins: obs / flt registered at the pins (PASS); AXI side = combinational pass-through split on existing internal AXI wires
  (WAIVED while it is cluster glue; if hardened as its own child, wrap the 5 channels in `qkd_host_pin_channel` as
  `qkd_host_csr_service_pins` does: +2 edges per CSR transaction, no schedule impact).  2 reach: placement owner (host
  cluster).  3 fanout: capture enable 43 kept copies, read selects 8 kept copies (PASS).  4 depth: two registered 8:1
  stages (PASS).  5 storage: flops < 2 kb, the read mux selects pin registers (PASS).  6/7 floorplan / clock: n/a until
  hardened (ck_csr, core family).  8 schedule: static, off the token schedule (PASS).

## Physical integration (host lanes)
No closed host child changes ports: prompt (`u_control`) and tx (`u_packet.u_axi`) keep theirs.  The window is one new
cluster-level block on the u_axi <-> u_control AXI wires of `qkd_hr_cluster`, fed by 1,301 + 71 bits that are already
cluster-level nets (they were root outputs).  Owner: KV-HOST3 / KV-HOST4 (cluster parent); size ~1.6 k flops.
