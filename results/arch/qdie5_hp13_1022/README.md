# QDIE5-HP13 (2026-10-22): HP13 core39 publisher parent — owed ports, wtn RTL, SEGCAL regeneration

Master: `qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1` (tt_ctlm x1 in the release Qwen compute die r48/r49cxc).
Base: main 4b215c0b3, which contains the QW-SEGCAL go port 7ba3786a9.

## 1. wtn hard child: option A (done)

`rtl/qwen_dv/qfd_tt_ctlm_dv_wtn.sv` and `rtl/qwen_dv/qfd_dv_typed_witness_control.sv` are now on this branch. They are
byte-identical to the sources of the closed view `qfd_tt_ctlm_dv_wtn-wtn1-9fa6fd27d` and to the frozen-frontend inventory
(d2c8e45a7). The branch also carries the view's face bench of record (`rtl/test/qwen_dv/run_f16_wtn_face.sh` with its tb,
vectors and PW image).

- yosys 0.68 `hierarchy -check -top cpub39_1`: FAIL without the RTL (`u_gi.g_wtn.u_wtn` is not part of the design), PASS
  with it (`logs/ys_hier_*.summary.txt`).
- Strict die port-bind on r49cxc `die.v`: `unresolved_children` drops from 1 to 0 (`logs/pb_wtn_port_bind.txt`).
- Face bench on Verilator 5.050 (gold1): 28/28 stimuli edge-exact, and BEGIN withdraw PASS. The mutants fail as
  required: fmut1 with BEGIN_NOT_WITHDRAWN, fmut2 and fmut3 with EDGE_MISMATCH.

## 2. SEGCAL regeneration of the HP13 netlists (done; port interface unchanged)

| step | tool | result |
|---|---|---|
| native32 | frozen HP13 frontend `full_generic_hp13.ys` + `construct_hp13_2.py`, yosys 0.68 (`regen_native.sh`) | Frozen parts reproduce main **bit-exact** (66cd44bf). Main parts (SEGCAL) give **22b50590**. Helpers are unchanged (8a1c0d01). |
| aliases / EMB clock evidence | `mk_alias.py` + `extract_clock_units.py` (patched copy, `regen_corepub.py`) | Aliases are identical to the committed ones on the frozen parent.json. Outputs are in `clock_units/`. |
| cpub39_1 / _2 | `hp13_corepub39_1021/generate.py` (patched copy) | Frozen input reproduces **e95e85e7 / 6b6c3fa1** bit-exact. New: **5d45a822 / fc00de4f**. Fanout audit PASS, 768 dead-cone keep removals, 3 protected (same as before). |
| HR source contract | `regen_hr_contract.py` | All 72 ARM HR captures now take D through a one-mux cone. This is SEGCAL's `xpf_hr = xpf_g[0] ? xpf_g : xpf`. Every cone source is a ck_hr register, so the path is still 1 register edge. HR_valid and the head380 bijection are re-proved. `tools/qwen_split/hp13_hr_contract.py` accepts the cone form. |
| clock owners | `regen_clock_owners.py`; `tools/qwen_split/audit_hp13_data_clocks.py` | The cf driver is re-proved on ck_hr. Every port and input clock law is unchanged compared with the old DATA_CLOCK_OWNERS. |
| selectors | `headprep_source.py`, `headprep_corepub_source.py`, frontend `input_source_inventory.json` (parts sha) | Re-pinned. |

Verification of the regenerated netlist:

- Native-vs-RTL lockstep (`realcalendar_native` fixture, V5.050, `run_native_compare.sh`). The fixture first reproduces
  PASS on the frozen base. On SEGCAL: CALR mode 1 is LP_LOCKSTEP PASS (1,198,920 compares). CALR mode 2 is LP_LOCKSTEP
  PASS (4,744,920) and TLOAD_PRODUCER PASS.
- Strict port-bind on r49cxc `die.v` with the regenerated netlist plus wtn: the same result as above
  (`logs/pb_regen_port_bind.txt`). Lane, record and HR audits PASS. DIE_PARAM_AUDIT with the new pins is identical to
  r49's own audit: XPF 21 resolves, and only the 2 pre-existing d2d TXDP/seam-image fails remain.
- HP13 head bench (TOKEN PASS checker c0f8097f3, die form materialized from this branch, V5.050): imgh 131/131 and
  img0 123/123, with trace lockstep vs the dv form PASS (27987 / 24852 cycles). bmut3 gives 129/131, mut37 130/131 and
  seg0 130/131, all FAIL as required. lpseg0 fails LANDED_LOCKSTEP as required. Generated LP bench: MUT0 PASS. MUTs 1, 2,
  4 and 5 do not fail; this weakness predates this branch and is the same on origin/main (TOKc-SEGCAL).

## 3. The 6 owed ports (`PORTS.json`)

| port | choice | why |
|---|---|---|
| mu_fault (in) | **A, die GEN** | Producers exist: mu_dhobs.mu_fault and mu_ctxrx.mu_fault, which today feed only the fault tree. Fix: OR the two with qfd_fault_or_n2, land the result on the ck_hr input region, and drive tt_ctlm.mu_fault. Do not use n_flt_t_mu_dhobs, because it contains tt_ctlm's own cf. |
| init_u0 (in) | **B candidate** (proof in PORTS.json); not applied | No producer anywhere, and no compiler emits it. INIT 52/3 is a fixture; the cold-prefix manifest is still OPEN. 0 = the INIT_U0=0 machine. |
| f16_auth, f16_obs (in), f16_st (out) | **COORD A/B decision** | The release netlist has F16WTN=1. On main there is no SYSFACE auth export, no slice event lane, no consumer, no WTN1 template and no F16 schedule price. The controller faults on the first start when the template is unsealed or unauthenticated, so with the stand-ins the die raises w_fault at the first token start. |
| table_req (out) | **A required** | CALR=1 is required, and CALR refuses TLOAD. The per-layer slice tables need table_req feeding the slice tload loader. The release slice2_w/_e have no such input, so layers 2..36 would run with wrong constants. The slice side (PRIVATE_CALR faces + tload) and GEN (table_req beside cmd with the same lane latency) are owed. |

Strict bind cannot PASS from this master alone. The B rule allows a port removal only if the bind passes afterwards, so
no port was removed here.
