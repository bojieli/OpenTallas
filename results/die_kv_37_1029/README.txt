DIE-KV-37 (2026-10-29 17:32- PDT) KV die owner receipts. Runs intel1 /srv/opentallas-scratch2/claude/die-kv-37-1029, E0 intel2 same path.

KV-023 (+ KV-024 apply)  eB3b = KV bind candidate of record
 1. eB3 (recipe_kv27f_eB3.json = DIE-KV-37-RC: eB2 + land_r8_extra pv_col_pads_28b.json [TRUNK_D 63, FLAG_D 78, C 9, 1178
    members, 141,684 pad FF] + param hook r8/kv_pv_col_regen.py) on the die-kv-35 bindroot: strict 0 errors; regen PV OK
    63/78; D2D_TXDP_K MISMATCH (stale pair image). INVALID: kv_pv_col_pads.py sys.path.insert(resolve().parents[4]/tools/
    die_plan) resolves through the symlinked bindroot to wt/codex-kv-0822/tools/die_plan, so the bind's later lazy
    `import landing_collector` loads the pre-DIE-KV-32 copy -> 49 raw pre-START reset face copies dropped on 25 types
    (DIE-KV-37-FACE, CHECKED: 3 reruns deterministic; pre-import keeps them). Fix proposal kv_pv_col_pads_noshadow.patch
    (importlib spec, no sys.path mutation; same line on origin/main) + test_proposal.txt -> shared, needs ROOT-MERGE.
 2. eB3b (recipe_kv27f_eB3b.json, bindB3b.sh) = eB3 on bindroot37 (PATCH37.txt): die-kv-35 bindroot with tools/ and
    kv35/36/37 as real copies, physical/ as a symlink tree, real copies of r8/kv_pv_col_regen.py + kv_pv_col_pads.py
    (== fee96ecff02), and TOK-KV-4 fee96ecff02 regen_kv_2350.py + pair_image_txdp.json [169,157,3,3] + regen_constants.py.
    Strict bind 0 errors / unbound / undriven / multiply_bound 0 (bindB3b_bind_report.json) [CHECKED].
    regen_constants qwen_kvsys PASS: 40 OK, 2 WARN (vport VPORT_DQ/CFG_FIA, as on eB2), 0 MISMATCH: TRUNK_D 63, FLAG_D 78,
    D2D_HOST_REC_RT 153, D2D_TXDP_K 32'h03039da9 bound in kv3_sys_c [CHECKED regen_constants_bindB3b.log].
    vs eB2 (bindB2r = eB2 rerun, byte-identical to die-kv-36 bindB2 -> bind deterministic): bind_clock_landings.json
    IDENTICAL (2626 collector instances, 83 face copies); bind_latency buses identical, only +1058 pvw landing_pads;
    count-strap / r8pad-strap / tie / reset / POR audits byte-identical -> CA crossings + R8 unchanged [CHECKED].
 KV-024: closed on eB3b by the TOK-KV-4 image (K0 169 / K1 157).

HG / PC / PV kits: main gen.py phys (01ddd2e80) on event28b + bindB2 kit_rtl: every core-bearing type rc=1 'internal core
 CTS requires explicit SIGNED TT/FF mean metadata' (ROOT-MERGE-115; event26a core_taps internal). hg cores: head_eighth
 e0/e1/e2/e5/e6 + qkd_ectlk_q0..q3 (signed: e1/e2/e5/e6 only); pv: kv3_pv_pair (KV-012) + pv_join_t (KV-011); pc: qkd_kvs_pc
 (no view). kv3_hroot gen rc 0, kit RTL md5-identical to kits_gen5 -> existing hroot kit valid; event28b carries UNRESIZED
 landing bands (ring types need clock_landing_plan.py resize-bands before any re-kit).

E0: e0_iopad (FLOW-CLOCK-R6) GRT_R6 rc=0 17:58; old unit oth-ubuntu-2828389 stopped 18:03; e0_route.sh (route + do-finish,
 then run_kit_kv.sh post) LIVE intel2 unit oth-ubuntu-1492212-1793322234.
