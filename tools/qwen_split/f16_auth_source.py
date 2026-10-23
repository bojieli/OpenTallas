"""Restore the real SYSFACE join authentication export without altering the frozen default.

The transport does not authenticate: it captures BEGIN and the existing two-sink
join receipt as one 83-bit word. The receiving witness must still withdraw on
BEGIN. No raw HOST AUTH event or transmitted program word can replace join.ready.
"""
import hashlib
from pathlib import Path

CORE = "rtl/qwen_split/qfd_sys_face_lctx3_core.sv"
WRAPPER = "rtl/qwen_split/qfd_sys_face_lctx3_wrapped.sv"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("F16 source anchor differs: " + old[:90])
    return text.replace(old, new, 1)


def generate(root, output):
    root, output = Path(root), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    core = (root / CORE).read_text()
    wrap = (root / WRAPPER).read_text()
    core = replace_once(core, "module qfd_sys_face_lctx3_core", "module qfd_sys_face_lctx3_core_f16")
    core = replace_once(core, "    input  wire          ck,", "    output wire [82:0] f16_auth,\n    input  wire          ck,")
    anchor = "    wire [10:0] rp_expected_pw; wire [3:0] rp_expected_dw; wire [63:0] rp_auth_digest, rp_program_digest;"
    export = """
    // Existing joined receipt only; BEGIN accompanies ready withdrawal atomically.
    assign f16_auth = {begin_v, rp_program_ready, rp_cap, rp_program_digest, rp_program_epoch};
"""
    core = replace_once(core, anchor, anchor + export)
    wrap = replace_once(wrap, "module qfd_sys_face_lctx3_wrapped", "module qfd_sys_face_lctx3_wrapped_f16")
    wrap = replace_once(wrap, ") (ck, rst_n,", ") (f16_auth, ck, rst_n,")
    wrap = replace_once(wrap, "  input ck;", """  output [82:0] f16_auth;
  wire [82:0] f16_auth__ot_pr;
  (* keep = "true" *) reg [82:0] f16_auth__ot_q;
  always @(posedge ck) begin
    if (!rst_n__ot_rl1) f16_auth__ot_q <= 83'd0;
    else f16_auth__ot_q <= f16_auth__ot_pr;
  end
  assign f16_auth = f16_auth__ot_q;
  input ck;""")
    wrap = replace_once(wrap, "qfd_sys_face_lctx3_core #", "qfd_sys_face_lctx3_core_f16 #")
    wrap = replace_once(wrap, "u_ot_pr_core (.input_source_copies", "u_ot_pr_core (.f16_auth(f16_auth__ot_pr), .input_source_copies")
    result = {}
    for name, text in (("qfd_sys_face_lctx3_core_f16.sv", core), ("qfd_sys_face_lctx3_wrapped_f16.sv", wrap)):
        (output / name).write_text(text)
        result[name] = hashlib.sha256(text.encode()).hexdigest()
    return result


if __name__ == "__main__":
    import argparse, json
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(generate(a.root, a.output), sort_keys=True))
