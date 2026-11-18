# Regenerated svc closure reference ref_1116 (S81-SVCMEM-1116, 2026-11-16)

**Why.** The S81 B6 plan events (B6gE, B6gG3b) bind the svc types with `-DOT_SVC_ATT_MEM_MACRO`, so the sw and qmem
memories are the dsdv_svc_mem_* form A macros instead of native helpers. The bound moved off ref_1112 and the
closure refused every svc kit (`numbered net 724 maps to 676: renumbered plain net not supported`). Without the
closure, pmem 512x512, land 640x256, pvq 8x2120 and the 4 x 160x265 attn_staging lanes stay native memories, which
fail the 16,384-bit memory check, or become ~440k flops under mem2reg.

**What changed in the tools.**
- `s81_svc_memory_closure.py`: `CUR_REF` -> ref_1116. The four T7 transforms and their proofs are unchanged.
- `s81_svc_ref_regen.py`: the token check (a) also accepts a `src_<hash>` register token whose every residual
  occurrence is a read of its output `<tok>_Q[..]` and whose driver lines (reg, always, Q assign) are not in the
  residual, so the register is the same on both sides. Here that token is the 512-bit job word
  (`src_c1d48dc2410de14d235c`, 4 lines: the removed sw/qmem native instances and the two new dsdv_svc_mem `.wd` ports).
  Every other use still refuses, and proof (b) still decides.

**Proof (`ref_map.json`).**
- Reference: canonical form of the svc_lo_dsdv_svc_rs__t7 bound from `bind.py kit-rtl` on plan ev/B6gG3b.json
  (bind out run/b/B6gG3b/out, wave source 7073a6b4a59 tree; the closure tools there equal main).
- Pairing 5645 nets; residual 1192 / 2086 lines; tokens_in_residual empty; read_only_in_residual = the one token above.
- T7 self-check PASS 12605dc2; the ported chain on the current T7 leaves the same residual as its preimage
  (`same_as_preimage: true`, closure 6a66e49e).

**Per-type check.** `kit_rtl_post.d/s81_svc_memory.sh` (v2 form) on fresh kit-rtl dirs of all 16 B6gG3b svc types
(svc_hi rs t1-t6, pvso_entry t1/t2, svc_lo rs t1-t7, rs_w t1): 16/16 `S81_KIT_RTL_POST PASS ... memory_closure
APPLIED`. Each closed bound holds ot_t7_{pmem,pvq,land}_capture_v2 and 2 x ot_hdc_v41x_attn_staging_fit with
SRAM_MACRO 1 (one 160x265 macro per lane), no SRAM_MACRO 0 staging left. 0 added cycles; macro instance paths are
the ones the plan places (`...g_stage2_u_stageN.g_macro.g_fit.g_lane[l].u_mem`).

**EQ basis.** As for ref_1112: native helpers keep their content-hash names; the MEM v2 children are unchanged and
gated (`../gate.out`, positive plus 5/5 mutants, staging checked against native SRAM_MACRO=0); the bound integration
is proved by the structural obligations, re-checked per type.

**Reproduce.**

    git show 1ec013265f^:rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv > old/dsdv_svc_att.sv   # and dsdv_svc_rs.sv
    cp <B6gG3b src>/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_{att,rs}.sv new/
    python3 -I tools/die_plan/s81_svc_ref_regen2.py <svc_lo t7 kit-rtl bound> OUT --old-src old --new-src new \
        --drop-loc ot_hdc_v41x_attn_s.sv
