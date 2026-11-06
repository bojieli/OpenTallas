# h9b STKREG / ENQREG form (HBM-FORM-TIMING-11-H9B, 2026-11-06)

Candidate only: no plan, recipe or POR change. Base = the captured h9b source
(`ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv` sha256 5fe6d24d..., Codex capture 27119ff709,
kit epyc6 codex-h9b-pg6-full-1106/kit). Routed limiter after the Codex data ECO:
TT -28.21 / 124 endpoints, ofs[1] -> |ofs (sticky) -> enqueue -> controller per-slot
wq_bank/wq_col enables (~350 loads).

* STKREG=1 (default here): `sticky` is a flop loaded with its exact next value
  (sticky | any fault-class set condition this edge; cleared with ofs by reset_regions[3]).
* ENQREG=1 (vB kit): `enqueue` is a flop loaded from the exact next values of its terms
  (EREG state_n/unposted_n/read_reserved_n, push_q next, sticky next).
* STKREG=0 / ENQREG=0 = the captured form exactly. PIN CYCLES 0. Same edges, same decisions.

Proof (proof/, yosys 0.x in openroad/orfs:asap7lock, SRAM macros everted to shared ports):
equiv_make gold vs new + async2sync + equiv_struct/simple/induct -seq 2, `equiv_status -assert`:
vA (STKREG=1) 13871/13871 proven, vB (STKREG=1, ENQREG=1) 13868/13868 proven.
Mutant controls FAIL as required: mutA (ofs_set[5] drops kq_fault) 40 unproven;
mutB (enq_q uses current sticky instead of sticky next) 35 unproven. See proof/result.txt.
