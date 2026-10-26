"""Bound START wrapper regression from the native59 STN kit."""
import re
import kit_rsync as K


def test_bound_one_bit_last_start_is_canonical_and_idempotent():
    # Exact native59 generator forms: [0:0] last port and no-comma connection.
    src = """module native59 (
    input wire clk,
    input wire arst_n,
    output wire [7:0] data_o,
    input wire [0:0] start_i // bound-only pin (die IO / reset spine / clock role): not a plan bus
);
    child u_bound (
        .clk(clk),
        .arst_n(arst_n),
        .data_o(data_o),
        .start_i(start_i)
    );
endmodule
"""
    out, nd, nc = K.add_reset_outs(src.splitlines(True), [], conn=True, start=True)
    txt = "".join(out)
    assert nd == nc == 1
    assert len(re.findall(r"input\s+wire(?:\s+\[0:0\])?\s+start_i", txt)) == 1
    assert txt.count(".start_i(start_i)") == 1
    assert not re.search(r",\s*(?://[^\n]*)?\n\s*\);", txt)
    assert K.add_reset_outs(out, [], conn=True, start=True)[0] == out


def test_normal_wrapper_without_start_is_unchanged():
    src = ["module m (\n", " input wire arst_n,\n", " output wire q\n", ");\n",
           " child c (\n", " .arst_n(arst_n),\n", " .q(q)\n", ");\n", "endmodule\n"]
    assert K.add_reset_outs(src, [], conn=True, start=False)[0] == src


def test_scalar_start_with_comment_preserves_other_ports():
    src = [" input wire arst_n,\n", " input wire start_i, // original\n",
           " input wire [3:0] payload\n", ");\n"]
    out, nd, nc = K.add_reset_outs(src, [], start=True)
    assert nd == 1 and nc == 0
    assert sum("input  wire start_i" in x for x in out) == 1
    assert " input wire [3:0] payload\n" in out
