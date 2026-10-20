#!/usr/bin/env python3
"""Add the die fault-OR observation input `obs_fault` to the bounded SYSFACE32 source.

Semantics (QW-ORPHANS 2026-10-20, LEAD decision 05:20; consumer = Q.BIND.1 fault-OR tree,
rtl/qwen_split/qfd_fault_or.sv on claude/qw-grt5-1020):
  obs_fault  : 1-bit input, the (already sticky) root of the die fault-OR tree.
  It is captured by its own face pin register (posedge ck, no reset, like every other
  captured pin register in this source) and ORed into the D input of the existing
  registered `fault` output FF:  fault(t+1) = face_fault(t) | obs_q(t),  obs_q(t+1) = obs_fault(t).
  Observation only: it does not gate admit_ready, t_go, result_* or any schedule edge.
  Latency obs_fault -> fault = 2 edges. Cost = 1 FF + 1 OR2; obs_q fanout 1; face_fault net
  gains no load (the OR replaces the output FF's D load). No tie, no reset path change.

Modes:
  --source IN OUT        patch the physical bounded source (or a protocol_bounded.sv copy)
  --bench IN OUT         patch a prepared protocol bench (tb_qfd_sys_face_n32.sv):
                         u_shadow_new.obs_fault <- tb_obs_fault; tb_obs_fault = 0 unless MUT==40,
                         where it pulses high from ep_cyc+50 and the wrapper comparison stays ON,
                         so a connected port MUST produce SYSFACE32_WRAPPER_MISMATCH port=fault.
"""
import argparse
import re
from pathlib import Path

FACE_FAULT = "n_2741"      # face_fault cone (input of the registered fault output FF u_1233)
FAULT_FF = "qfd_bmath_dff_p #(.ID(0)) u_1233(.C(n_2),.D(n_2741),.Q(n_2486));"


def patch_source(text):
    def once(old, new):
        nonlocal text
        assert text.count(old) == 1, old[:80]
        text = text.replace(old, new, 1)
    assert "obs_fault" not in text
    assert "assign n_2 = ck;" in text and "assign fault = n_2486;" in text
    once(",io_shared_fault,fault);", ",io_shared_fault,obs_fault,fault);")
    once("input wire [0:0] io_shared_fault;\n",
         "input wire [0:0] io_shared_fault;\ninput wire [0:0] obs_fault;\n")
    once("assign fault = n_2486;\n",
         "assign fault = n_2486;\n"
         "// obs_fault (die fault-OR root): face pin register + OR into the registered fault output.\n"
         "wire n_obs_raw, n_obs_q, n_obs_d;\n"
         "assign n_obs_raw = obs_fault;\n")
    once(FAULT_FF,
         "qfd_bmath_dff_p #(.ID(0)) u_1233(.C(n_2),.D(n_obs_d),.Q(n_2486));\n"
         "(* keep=1, keep_hierarchy=\"yes\" *) qfd_bmath_dff_p #(.ID(0)) u_obs_pin(.C(n_2),.D(n_obs_raw),.Q(n_obs_q));\n"
         "(* keep=1, keep_hierarchy=\"yes\" *) qfd_bmath_or #(.ID(0)) u_obs_or(.A(n_2741),.B(n_obs_q),.Y(n_obs_d));")
    # Scalar 1-bit ports: the generator declared every 1-bit port [0:0] (never indexed); the closed qfd_sys_face view,
    # its pin plan and SDC (get_ports ck) use scalar names, so declare them scalar (no functional change).
    for name in re.findall(r"^(?:input|output) wire \[0:0\] (\w+);$", text, re.M):
        assert not re.search(rf"\b{name}\[0\]", text), name
    text = re.sub(r"^(input|output) wire \[0:0\] (\w+);$", r"\1 wire \2;", text, flags=re.M)
    return text


def patch_bench(text):
    m = re.search(r"    qfd_sys_face_n32_bounded u_shadow_new\(", text)
    assert m and text.count("u_shadow_new(") == 1
    text = text.replace("qfd_sys_face_n32_bounded u_shadow_new(",
                        "qfd_sys_face_n32_bounded u_shadow_new(.obs_fault(tb_obs_fault),", 1)
    decl = ("    reg tb_obs_fault = 1'b0;\n"
            "    // MUT 40 (obs_fault causal negative): pulse the die fault-OR root after the epoch anchor;\n"
            "    // the paired wrapper comparison stays on, so the port must flip `fault` 2 edges later.\n"
            "    always @(negedge ck) if (MUT == 40 && ep_cyc >= 0 && cyc >= ep_cyc + 50) tb_obs_fault <= 1'b1;\n")
    text = text.replace("    qfd_sys_face_n32_bounded u_shadow_new(", decl + "    qfd_sys_face_n32_bounded u_shadow_new(", 1)
    old = "      if(MUT==0 && ep_cyc>=0) begin"
    assert text.count(old) == 1
    text = text.replace(old, "      if((MUT==0 || MUT==40) && ep_cyc>=0) begin", 1)
    return text


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--source", nargs=2)
    g.add_argument("--bench", nargs=2)
    a = p.parse_args()
    src, dst = a.source or a.bench
    t = Path(src).read_text()
    Path(dst).write_text(patch_source(t) if a.source else patch_bench(t))
    print("OBS_FAULT_PATCH_PASS", "source" if a.source else "bench", dst)
