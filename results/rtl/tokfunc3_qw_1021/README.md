# TOK-FUNC3-QW 10-21: Qwen ROM chained token (RTL-functional)

One command: `tools/qwen_tokfunc/run_tok_func_qw.sh --asm c0f8097f3 --collect-only --stages stg,xt1,xdie,tp8,ovl4u,ctx4u,head,kv,chain --stage-dir stg=stg3 --stage-dir ovl4u=ovl4u_rel --stage-local kv=results/rtl/tokfunc2_qw_1021/kv`.
Without `--collect-only` it launches the stages, and `--die-netlist C:K` reruns it on the GEN netlists.

**Stage chain: PASS.** Grade: RTL-functional, source-bound KV vehicle 0e597ed1c. Of its 54 non-bench sources, 53 are byte-identical to the c0f8097f3 assembly; the 54th only adds default-0 parameters. The run uses the real token: the TP4 ISA-golden prompt at position 8191, ctx 8192.
- Each of the 36 layers runs through the KV-die attention RTL (the preserved `tb_kvattn_rel` binary, sha 5d0e1cab…, not rebuilt).
  - Inputs: q, plus the P row of K/V, are the values the compute-die RTL produced bit-exact in stg/qk. The KV window comes from the TP4 golden prefill.
  - Results: 36/36 runs PASS. All 512 output words, the maxima/denominators and STATUS are bit-exact against the TP8-native attention golden, and every fault flag is 0.
  - Cycles, identical on every layer: CMD at the face to the last RESULT beat = 1,782; CMD to STATUS = 1,997; work span = 1,746. The 36-layer sum is 71,892 cycles.
- Four users: 9 runs, each using four layers' real data as its four users. All PASS with a command period of 2,025.
- Control: `CTL_L35_goldflip` FAILs as required (MISMATCH on word 0).
- Hand-off checks: 288 of 288 edges are bit-exact.
  - Compute die: x_in for L0..L35 equals the previous layer's recorded X, which equals resid2's output. Also resid1 → resid2 and gu.x; qkv → qk; gu → silu; silu → down.x.
  - Attention: the TP4 (PV512) attention of the RTL's q/k/v equals the od stage's input `o_x` on all 36 layers.
- Golden-family split: the KV RTL computes TP8 attention (PV256), but the only 36-layer token golden is TP4 (PV512). The two differ in about 319–340 of 512 words per layer, by at most 1,977 ulp. The od/resid stages were fed the TP4 ATTN, so a 36-layer TP8 token golden is still owed.

**Composed token** (`compose/report.json`):
- Every stage PASS except stg. Gives 1u = 279,731 cycles = 4,291.6 tok/s (−2.53% vs the 272,641-cycle model); 4u = 11,750.6.
- REL terms: XT1 tile edges, XDIE link, chain kv_service 1,782, TP8 all-reduce E 286 / LS 378, head 3,135 and the OVL 4u frame.
- The price is HELD for two reasons:
  - The normalized stg verdict is FAIL because of the original pos MAT calibration.
  - The MAT VM-delivery ages are UNKNOWN because tb_qfd_dv2 had no VM-write probe.
- Both are fixed in the STG4 rerun (branch claude/tok-func3-qw-stg4-1021, gold1 RUNROOT/stg4). Collect it with `--stage-dir stg=stg4`.

## STG4 collected (STEWARD-TOKb-QW 10-21 19:55)

Command: the one above with `--stage-dir stg=stg4` (gold1 RUNROOT/stg4, unit oth-ubuntu-3860252, exit 0).
- **stg: PASS**, ISA 1,032,336/1,032,336, 527/527 numeric cases, calibration gate PASS (rel + pos nominal, mut diagnostic), delivery ages qualified (0 unknown). Evidence `stg4/`.
- **Grade now "RTL-functional (source assembly)"**: `normalize_collected_stg.py` verifies the build receipt it now fetches (`collect_files.py`).
  - Per config (rel / pos = ARF1 RP1 release / mut): identity log SNAPSHOT + BIND OK, `build_identity.json` source == `<cfg>.build_source.json`, its binary sha == the run binary (`vtb.sha256`), flags == `vflags.txt`.
  - All 36 inputs equal the c0f8097f3 assembly except `rtl/qwen_dv/qfd_dv_redstn2.sv` (== origin/main, the merged LM-head tail fix a4cf9a360) and the bench `tb_qfd_dv2.sv` (VM-write probe + cal prearm).
- Composed token (`compose/report.json`): 1u 279,731 cycles = 4,291.6 tok/s (-2.53% vs model), 4u 11,750.6 tok/s. **Price still HELD** on two diagnostic stages only: `kv` and `chain` ran on the historical KV vehicle 0e597ed1c, not the assembly.
- NEXT: stage kv rerun on the assembly (launched 19:47, ot-run --mem 700), then chain with `--kv-obj` = that build, then re-collect.
