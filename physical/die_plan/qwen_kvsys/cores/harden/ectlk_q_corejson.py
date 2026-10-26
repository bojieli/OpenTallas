#!/usr/bin/env python3
"""CORES-KITS/KVX 10-26: runnable core.json for the ECTLK quarter cores qkd_ectlk_q0..q3 (COORD KV ruling 10-25 (c)).

Input: the Codex quarter producer output (codex/kv-cores-1713@a1841bc785 ectlk_quarter_cores.py, 'physical macro
metadata pending'): <gen>/qkd_ectlk_q<k>_core.json + qkd_ectlk_columns.sv (committed beside this script, sha256 in
the output).  This script fixes the three defects Codex listed, nothing else:
  * files: the RTL closure of qkd_ectlk_q<k> from the REPO tree (not the out-of-repo snapshot; the snapshot's
    ot_qkd_ectl_parts.sv predates dae8a0aacb, the c_started/c_fin implicit-net fix) + ectlk_q/qkd_ectlk_columns.sv;
    the SRAM ot_sram_1r1w_128x256_m1_r2c2 is NOT a file: gen_core_kit_kv.py takes it from kit_rtl.json hard_macros
    of kv3_hg (black box + LEF/LIB);
  * pin_class: the kv_core_rtl classes (in / out / clk) from port_decl direction (Codex wrote data/rst);
  * ports = the port_decl names (Codex cloned a stale 30-port list; port_decl has the real header).
    python3 ectlk_q_corejson.py <codex gen dir> <repo> <out dir> <bb_v>
"""
import hashlib, json, re, sys
from pathlib import Path

gen, repo, out, bb = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
here = Path(__file__).resolve().parent
cols = here / "ectlk_q" / "qkd_ectlk_columns.sv"
CLOSURE = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv", "rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv",
           "rtl/lib/ot_rst_relay.sv", "rtl/qwen_sys/static_kv_20261014/qkd_ectl_c_st.sv",
           "rtl/qwen_sys/split_20261014/qkd_ectl_native_direct_tp8.sv", "rtl/qwen_sys/static_kv_20261014/qkd_static_ectl_st.sv",
           "rtl/qwen_sys/static_kv_20261014/qkd_static_ectla_kiss.sv", "rtl/qwen_sys/static_kv_20261014/qkd_static_k_issuer.sv"]
out.mkdir(parents=True, exist_ok=True)
for q in range(4):
    cj = json.loads((gen / f"qkd_ectlk_q{q}_core.json").read_text())
    pd = cj["port_decl"]
    pc = {}
    for n in cj["pin_class"]:
        b = re.sub(r"\[\d+\]$", "", n)
        d = pd[b][0]
        pc[n] = "clk" if b == "ck" else ("in" if d == "input" else "out")
    cj["pin_class"] = pc
    cj["classes"] = {c: sum(1 for v in pc.values() if v == c) for c in ("in", "out", "clk")}
    cj["ports"] = list(pd)
    cj["files"] = [str(repo / f) for f in CLOSURE] + [str(cols)]
    for f in cj["files"]:
        assert Path(f).is_file(), f
    cj["report"]["clock_nets"] = {"clk": "ck[0]"}
    cj["kvx_fixup"] = dict(by="CORES-KITS/KVX 2026-10-26", source="codex/kv-cores-1713@a1841bc785 ectlk_generated",
                           columns_sha256=hashlib.sha256(cols.read_bytes()).hexdigest(), sram="kit_rtl.json hard_macros (kv3_hg)",
                           files_repo_relative=CLOSURE + [str(cols.relative_to(repo))])
    (out / f"qkd_ectlk_q{q}_core.json").write_text(json.dumps(cj, indent=1) + "\n")
    print(q, cj["classes"], len(cj["files"]))
