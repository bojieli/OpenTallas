"""Keep S81's default-off AM metadata cut when its landed parent is regenerated."""
import re

FLAG = "OT_S81_KP4_AM_FACE3"
TOP = "ot_s81_kp4_dec_native_flat_lp"
DECL = """`ifdef OT_S81_KP4_AM_FACE3
// Partial counts share the existing data-face edge: no extra word/calendar edge.
wire [8:0] face_am_parts;
ot_s81_kp4_am_face3 u_face_am3 (.clk(ck_syn), .p_d(p_d), .parts(face_am_parts));
`endif
"""
CONNECTION = """.n_relock(face_n_relock)
`ifdef OT_S81_KP4_AM_FACE3
        , .am_face3(face_am_parts)
`endif
    );"""

def add_face3_option(rtl):
    if not re.search(r"\bmodule\s+" + TOP + r"\s*#", rtl):
        raise ValueError("AM face option requires the exact native landed parent")
    tokens = re.sub(r"\s+", "", rtl)
    data_face = "ot_pl_pad#(.W(((543)-(0)+1)),.N(1))u_face_p_d(.ck(ck_syn),.d(p_d),.q(face_p_d));"
    valid_face = "ot_pl_pad#(.W(1),.N(1))u_face_p_v(.ck(ck_syn),.d(p_v),.q(face_p_v));"
    if data_face not in tokens or valid_face not in tokens:
        raise ValueError("AM metadata must share the exact one-edge payload/valid face clock")
    if FLAG in rtl:
        if DECL not in rtl or CONNECTION not in rtl:
            raise ValueError("AM face option is incomplete or has different phase bindings")
        return rtl
    declaration = "wire [543:0] face_p_d;\n"
    connection = ".n_relock(face_n_relock));"
    if rtl.count(declaration) != 1 or rtl.count(connection) != 1 or ".p_d(face_p_d)" not in rtl:
        raise ValueError("native face data/valid/clock template changed; review the cut")
    return rtl.replace(declaration, declaration + DECL).replace(connection, CONNECTION)
