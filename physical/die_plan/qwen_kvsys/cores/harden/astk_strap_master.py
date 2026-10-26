"""ASTK strap master (OWNER option B, COORD 2026-10-25 07:01): ONE hardened kv3_astk for the four hub corners.

The four planned ASTK cores (kv3_astk_EN / ES / WN / WS) carry the same leaves; they differ only in two constant ID
bindings of the corner (side E/W, half N/S):
    ctl  .st(2'b{E}{N})              -> st_q, base slot of the corner
    zn_k .zc(4'b{k}{E}{N}), k = 1..3 -> zc_q[1:0] = S, zc_q[3:2] = L (zn_0 = qkd_astk_zn_head_p has no zc)
EN = 2'b11, ES = 2'b10, WN = 2'b01, WS = 2'b00.  The master takes them from one ID strap input `strap_corner[1:0]`
(tied TIEHI/TIELO at the parent), lands it in one kept 2-b register (the guard's pin register; false path from the
port, quasi-static: +1 settle edge after power-up, before reset release) and binds st / zc[1:0] to that register.
The block works for every strap value (no case analysis).  Everything else is the corner kit (face ports, timing regs,
rep-split, am g drop) unchanged.
"""
import re

MASTER = "kv3_astk"
STRAP = "strap_corner"
CORNER_STRAP = {"EN": 0b11, "ES": 0b10, "WN": 0b01, "WS": 0b00}


def transform(text, mod, mut=None):
    """mod: the corner wrapper module (kv3_astk_XX).  mut (tb only): 'swap' binds zc[1:0] to the bit-swapped strap."""
    c = mod.rsplit("_", 1)[1]
    s = CORNER_STRAP[c]
    sb = f"2'b{s:02b}"
    n0 = text.count(f".st({sb})")
    if n0 != 1:
        raise SystemExit(f"strap master: expected one .st({sb}) in {mod}, found {n0}")
    text = text.replace(f".st({sb})", ".st(strap_q)")
    zre = re.compile(r"\.zc\(4'b([01]{2})" + f"{s:02b}" + r"\)")
    ks = zre.findall(text)
    if sorted(ks) != ["01", "10", "11"]:
        raise SystemExit(f"strap master: expected zc of zn_1..3 with S={s:02b} in {mod}, found {ks}")
    zs = "{strap_q[0], strap_q[1]}" if mut == "swap" else "strap_q"
    text = zre.sub(lambda m: f".zc({{2'b{m.group(1)}, {zs}}})", text)
    left = re.findall(r"\.(st|zc)\(\d+'b[01]+\)", text)
    if left:
        raise SystemExit(f"strap master: constant {left} left in {mod}")
    n1 = len(re.findall(rf"^module {mod} \(", text, re.M))
    if n1 != 1:
        raise SystemExit(f"strap master: module header {mod} not found")
    text = re.sub(rf"^module {mod} \(", f"module {MASTER} (\n    input wire [1:0] {STRAP},", text, flags=re.M)
    text = text.replace(f"// = member leaves of astk_{c} ",
                        f"// STRAP MASTER (OWNER option B 10-25) from corner {c}: {STRAP} = EN 11 / ES 10 / WN 01 / WS 00.\n"
                        f"// = member leaves of astk_{c} ", 1)
    anchor = "    // ASTK face fix:"
    if text.count(anchor) != 1:
        raise SystemExit("strap master: wrapper body anchor not found")
    text = text.replace(anchor, (
        f"    // ID strap landing (quasi-static, false path from the port): one kept register for the 5 leaf bindings\n"
        f"    (* keep *) reg [1:0] strap_q;\n"
        f"    always @(posedge ck) strap_q <= {STRAP};\n") + anchor, 1)
    return text


def core_json(cj):
    """add the strap port to the core json (in place)"""
    cj["port_decl"][STRAP] = ["input", 1, 0]
    for b in (0, 1):
        cj["pin_class"][f"{STRAP}[{b}]"] = "in"
    rep = cj.setdefault("report", {})
    rep.setdefault("straps", [])
    rep["straps"] = list(rep["straps"]) + [dict(port=STRAP, width=2, kind="id_strap", values=CORNER_STRAP,
                                                 rule="OWNER option B COORD 2026-10-25 07:01")]
    rep["added"] = list(rep.get("added", [])) + [dict(pin=STRAP, bit=b, why="ID strap (OWNER option B 10-25): corner {E/W, N/S}",
                                                       leaf_bits=5, strap=True) for b in (0, 1)]
    cj["module"] = MASTER
