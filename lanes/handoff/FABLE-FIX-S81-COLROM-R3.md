# FABLE-FIX-S81-COLROM-R3 handoff (11-21 10:3x PST; successor of FABLE-FIX-S81-COLROM-R2)
Dirs: R = /srv/opentallas-scratch2/claude/fable-fix-s81-colrom-r3 on epyc7 (lane clone R/repo, trees, gates) and epyc8 (RDX kits R/rdxkit*), hub logs intel2 R/*_otrun.log.
Old work (R2) stays at epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-colrom (tree1, gen_colrom_rows.py, bench1).

## Done
1. Lockstep gate (epyc7 R/repo, uncommitted): tb_ot_s81_cfg7_seq.sv reference loader gets the same 13-edge go-guard hold (TGG, PQ1+PINREG1+RDX1 only:
   reference e_sh_free/e_bank_free read 0 for 13 edges after r_go; directed loops wait 13 more edges). fill2_cfg7_bench.sh new mode rx1_mut_noguard.
   R/r3_cfg7_gate.sh: 11 PASS modes PASS, 12 mutants FAIL (noguard: control mismatch at check 54), run_cfg7_seq_gate PASS (R/gate_cfg7).
2. Loop bench copied into R/repo: rtl/v41die/test/tb_colrom_loop.sv + tools/s81/colrom_loop_bench.sh (from R2 bench1/run_guard.sh).

## Running / next
- Private tree: R/r3_chain.sh (ot-run epyc7): src_manifest build at main 2ddb19c08ba6 (= tree1 TOOLS_RT_SHA; tools scope equal except HCP registry,
  allow-listed for s81 with branch_sha c6a2270ccb0) + 2864-file DATA overlay (tree1 vs 2ddb19c: 85 differ + 2778 absent; staged in R/ov1) + guard RTL
  -> tree2a -> reprove (R/r3_reprove.sh, reproof reprove41_cfg7_rdx_guard_1121 out of tree) -> tree2 (+ reproof + manifest) -> R/r3_gate.sh -> R/gate2.
  tree2 also holds 1268 main files tree1 lacks (other dies' results; superset).
- RDX re-harden: kit = generator inputs of the signed kit (epyc7 fam-s81-col/rdxkit_anchor/ot_s81_cfg7_seq_rdx, files <= 09:16 UTC) + tap_balance.tcl +
  native_pin_contract.py (both added later in the signed kit) + guard RTL. rdxkit (no tap_balance: CTS fail), rdxkit2 (rsync without -r: empty
  reset_contract -> LEC ERROR) are dead; rdxkit3 running on epyc8. Then R/r3_view.py -> new view ot_s81_cfg7_seq_rdxg_1121, HCP entry,
  signed_view_sha_s81.json, gen_colrom_rows.py RDX_LIB repoint, push to main, hand to S81-J6-ASSEMBLY-R4.
- epyc7 docker created no containers 17:36-18:0x UTC (posted INFRA); kits go to epyc8.
