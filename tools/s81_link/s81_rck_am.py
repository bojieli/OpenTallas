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
        if DECL not in rtl or (CONNECTION not in rtl and not transport4_present(rtl)):
            raise ValueError("AM face option is incomplete or has different phase bindings")
        return rtl
    declaration = "wire [543:0] face_p_d;\n"
    connection = ".n_relock(face_n_relock));"
    if rtl.count(declaration) != 1 or rtl.count(connection) != 1 or ".p_d(face_p_d)" not in rtl:
        raise ValueError("native face data/valid/clock template changed; review the cut")
    return rtl.replace(declaration, declaration + DECL).replace(connection, CONNECTION)


TRANSPORT_FLAG = "OT_S81_RCK_RELAY4"
TRANSPORT_DECL = """`ifdef OT_S81_RCK_RELAY4
`ifndef OT_S81_KP4_AM_FACE3
initial $error("RCK relay4 requires the joint AM face3 source option");
`endif
// A whole cohort, one word/edge. The reset root takes the SAME four edges.
wire [543:0] rck_p_d;
wire rck_p_v;
wire [8:0] rck_am_parts;
wire rck_reset_calendar;
ot_pl_pad #(.W(554), .N(4)) u_rck_transport4 (.ck(ck_syn),
    .d({face_am_parts, face_p_v, face_p_d}), .q({rck_am_parts, rck_p_v, rck_p_d}));
ot_pl_pad #(.W(1), .N(4)) u_rck_reset4 (.ck(ck_syn), .d(rst_n), .q(rck_reset_calendar));
`endif
"""

def arg4(new, old):
    return "\n`ifdef OT_S81_RCK_RELAY4\n" + new + "\n`else\n" + old + "\n`endif\n"

TRANSPORT_BINDS = {
    "u_lpr_root (.ck(ck_syn), .d(rst_n), .q(lpr_root))":
        "u_lpr_root (.ck(ck_syn), .d(" + arg4("rck_reset_calendar", "rst_n") + "), .q(lpr_root))",
    ".p_v(face_p_v), .p_d(face_p_d)":
        ".p_v(" + arg4("rck_p_v", "face_p_v") + "), .p_d(" + arg4("rck_p_d", "face_p_d") + ")",
    ".am_face3(face_am_parts)": ".am_face3(" + arg4("rck_am_parts", "face_am_parts") + ")",
}

def transport4_present(rtl):
    if TRANSPORT_FLAG not in rtl:
        return False
    if TRANSPORT_DECL not in rtl or any(rtl.count(v) != 1 for v in TRANSPORT_BINDS.values()):
        raise ValueError("incomplete transport cohort/reset calendar; no phase substitution")
    return True


def add_transport4_option(rtl):
    add_face3_option(rtl)  # verifies the literal one-edge data/valid face
    if transport4_present(rtl):
        return rtl
    for old in TRANSPORT_BINDS:
        if rtl.count(old) != 1:
            raise ValueError("native transport binding changed: " + old)
    rtl = rtl.replace(DECL, DECL + TRANSPORT_DECL)
    for old, new in TRANSPORT_BINDS.items():
        rtl = rtl.replace(old, new)
    return rtl
