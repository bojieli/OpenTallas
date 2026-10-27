# HEAD-RTL 2026-10-26: missing s81_head content providers

The canonical plan (`physical/die_plan/s81_head/die_plan.json`, frozen) has 4 content modules with no provider
(`module_check_canonical.json`, tool `tools/s81_head/head_module_check.py`): hd_mesh, hd_lep0N, hd_ctl and hd_host.

| type | status after this lane |
|---|---|
| hd_lep0N | Provider exists: `ot_s81hd_lep0N_core` (Codex, source closure `results/arch/head_lep_source_1026`). The plan names a nested module (`dsdv_slice_lepw_mu.LP`), so it needs Codex's `head_lep_plan_delta.py`, which adds u_core plus the +1 live fault return lep0N.fault_o0 -> ctl.lep_fault_i. |
| hd_mesh | NEW `ot_s81hd_mesh_ep_core` (rtl/dsrom_sys/s81_head/ot_s81hd_mesh_ep_core.sv). The plan gave the wrapper and the core the same name, so the core needs its own name. It has exactly the plan buses: no extra IO, and the endpoint fault is carried in-band. Bench: `tools/s81_head/mesh_ep_bench.sh`. |
| hd_ctl | NOT written: ASK. The contracts are open; see lanes/HEAD-RTL.md. |
| hd_host | NOT written: ASK. `dsdv_hostb_stage_hbc` needs compiled dates plus job_active/starter_armed, which have no plan bus. |

`tools/s81_head/head_rtl_plan_delta.py` writes the candidate plan as a copy; it never adopts it. On that candidate the
module check gives missing 2 (ctl, host) and 0 unresolved instances (`module_check_candidate.json`). `gen.py rtl --rtl-root
--types hd_mesh,hd_lep0N` leaf port binding: rc 0, i.e. no unbound or unknown ports (`leaf_bind_mesh_lep0N.log`).

mesh bench (Verilator 5.050, ot-run on epyc1, `mesh_bench.log`): two endpoints with their SerDes pairs cross-connected.
Production run: 400/401 records arrive at each ctl as copy A AND copy B, bit-exact, 0 faults. A forced bad m_tx beat
shows up in-band (ep_fault[8]) at ctl X, and Y stays clean. Mutants 1-4 (copy id stuck, copy-B identity flip, lane b
silent, fault not carried) all FAIL as required. Max record latency: 40 edges (A) / 42 edges (B). The CRC-impairment
windows produced no replay-visible latency, so the bench does not show that the replay path was exercised.
