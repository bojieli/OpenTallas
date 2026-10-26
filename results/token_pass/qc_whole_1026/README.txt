QC v7 functional source closure (source 5832e672235d955164c31991b09f3cee96ee4de2)

The emitted bind.f names opaque leaves, rather than a functional simulation closure. Reading it directly in Verilator fails with 51 missing-module diagnostics. stage_qc.py resolves their implementation dependencies at the source commit, preserves every selected first-level leaf by SHA256, applies the established S8 profile and the selected A0/native implementation families, and rejects ambiguous or duplicate declarations. All output file lists are relative to the staged root. The bound generated RTL is unchanged.

v7_bound.tar.gz contains only the generated bound RTL and the 39 pinned first-level leaf identities. It does not include the old absolute bind.f. The top digest is 740eaf8280fa4914d6b894dd489f04ed58ab0cf1a15012b61b2bd8b4750ca6a9. The implementation closure contains 248 files and 496 modules; this is source staging, not a token pass.

Reproduce from the branch checkout:
  mkdir -p /scratch/qc/input
  tar -xzf results/token_pass/qc_whole_1026/v7_bound.tar.gz -C /scratch/qc/input
  CAL_SMOKE_CACHE_ROOT=/scratch/qc/cache python3 tools/qwen_tokfunc/current_path/stage_qc.py --bound /scratch/qc/input --recipe physical/die_plan/qwen_compute/bind/asbuilt_meth_fixed_su.json --revision 5832e672235d955164c31991b09f3cee96ee4de2 --out /scratch/qc/staged
  cp results/token_pass/qc_whole_1026/run_lint.sh /scratch/qc/staged/
  # Use ot-run admission for the actual lint. run_lint.sh runs from its own directory.

Selected physical A0 wrappers expose optional clocks not used by this configuration: ck_rqr2/3 are consumed only when GLUE_HARD!=0 (here 0), and me-array u_top ck_reg is consumed only when REGROOT!=0 (here 0). No floating active clock is waived or connected by the staging tool.

Whole-top elaboration is running on intel2 unit oth-ubuntu-1675607-1793005939. No whole-layer or G5 verdict has been earned. The next native-pair token step depends on KV native E boot/HOST replay and the QC infrastructure-first plan rebind.
