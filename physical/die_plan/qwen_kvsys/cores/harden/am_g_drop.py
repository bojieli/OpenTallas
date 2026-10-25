#!/usr/bin/env python3
"""COORD ruling 2 (2026-10-25; KV-TOK 05:36 PDT: g == 0 for every scheduled op): drop the constant LMAX head-group
bit g = am[1] from the four ahub -> ASTK am buses (36 -> 35 b) and the ASTK qo copy of it (qo[537] -> the head-group ep
qi; 572 -> 571 b).  Kit-level transforms for gen_core_kit_kv.py --am-g-drop.

Bit map (every dropped port): old 0 -> new 0, old b -> new b-1 for b > DROP (DROP = 1 for am, 537 for qo); the old
DROP bit is gone.  The ASTK ctl leaf gets AM_G_PIN=0, G_CONST=0 (repo qkd_astk_static_leaves.sv) in place of the pin.

  qkd_ahub:    outputs am0..am3 [35:0] -> [34:0] (the leaf still computes the 36-b word; its constant g output is unloaded)
  kv3_astk_*:  input  u_strip_u_strip_u_ctl__am [35:0] -> [34:0], output u_strip_u_strip_u_ctl__qo [571:0] -> [570:0]

0 added cycles, 0 added flops (the dropped g pin / qo pin flops become constants and are swept).  The plan pin side
(same compact rename of the plan pins) is KV-PLAN3's batched delta; until it lands, plan_pins() applies the identical
rename to the plan pins in memory so the kit geometry is the post-delta one (pin of old bit b carries new bit b-1).
"""
import re

AHUB_DROPS = {f"am{s}": 1 for s in range(4)}
ASTK_AM = "u_strip_u_strip_u_ctl__am"
ASTK_QO = "u_strip_u_strip_u_ctl__qo"
ASTK_DROPS = {ASTK_AM: 1, ASTK_QO: 537}


def drops_for(mod):
    if mod == "qkd_ahub":
        return dict(AHUB_DROPS)
    if mod.startswith("kv3_astk_"):
        return dict(ASTK_DROPS)
    raise SystemExit(f"--am-g-drop does not apply to {mod}")


def _bit(name):
    m = re.fullmatch(r"(.+)\[(\d+)\]", name)
    return (m.group(1), int(m.group(2))) if m else (name, None)


def rename(name, drops):
    """new pin/bit name, or None when it is the dropped bit; unchanged names pass through"""
    base, b = _bit(name)
    if base not in drops or b is None:
        return name
    d = drops[base]
    if b == d:
        return None
    return f"{base}[{b - 1}]" if b > d else name


def _port_decl(text, port, direction, old_hi):
    old = f"{direction} wire [{old_hi}:0] {port},"
    if text.count(old) != 1:
        old = f"{direction} wire [{old_hi}:0] {port}\n"
        if text.count(old) != 1:
            raise SystemExit(f"am-g-drop: expected one '{direction} wire [{old_hi}:0] {port}' declaration")
    return text.replace(old, old.replace(f"[{old_hi}:0]", f"[{old_hi - 1}:0]"), 1)


def _assigns(text, port, drop, width, mutant=False):
    """rewrite the per-bit output aliases `assign port[b] = rhs;` with the compact map"""
    pat = re.compile(rf"^(\s*)assign {re.escape(port)}\[(\d+)\] = ([^;]+);\n", re.M)
    seen = set()

    def sub(m):
        b = int(m.group(2))
        seen.add(b)
        if b == drop:
            return ""
        nb = b - 1 if b > drop else b
        if mutant and b == drop + 1:          # miter mutant: carry the dropped bit instead of its successor
            return f"{m.group(1)}assign {port}[{nb}] = {m.group(3).replace(f'[{b}]', f'[{drop}]')};\n"
        return f"{m.group(1)}assign {port}[{nb}] = {m.group(3)};\n"
    text = pat.sub(sub, text)
    if seen != set(range(width)):
        raise SystemExit(f"am-g-drop: {port}: expected {width} bit aliases, found {len(seen)}")
    return text


def transform_ahub(text, mutant=False):
    if "am-g-drop" in text:
        raise SystemExit("qkd_ahub already am-g-drop transformed")
    for s in range(4):
        text = _port_decl(text, f"am{s}", "output", 35)
        text = _assigns(text, f"am{s}", 1, 36, mutant and s == 0)
    return text.replace("`default_nettype none", "`default_nettype none\n// am-g-drop (COORD ruling 2, 10-25): am0..3 g bit "
                        "(old am[1], hub constant 0) removed, old b -> new b-1 (b >= 2)", 1)


def transform_astk(text, mutant=False):
    if "AM_G_PIN" in text:
        raise SystemExit("ASTK core already am-g-drop transformed")
    text = _port_decl(text, ASTK_AM, "input", 35)
    old = f".am({ASTK_AM}[35:0])"
    if text.count(old) != 1:
        raise SystemExit("am-g-drop: expected one ctl .am binding")
    text = text.replace(old, f".am({ASTK_AM}[34:0])", 1)
    m = re.search(r"qkd_astk_ctl_s #\(([^\n]*)\) (\w+) \(", text)
    if not m or text.count(m.group(0)) != 1:
        raise SystemExit("am-g-drop: expected one parameterised qkd_astk_ctl_s instance")
    gc = "1'b1" if mutant == "gconst" else "1'b0"
    text = text.replace(m.group(0), f"qkd_astk_ctl_s #({m.group(1)}, .AM_G_PIN(0), .G_CONST({gc})) {m.group(2)} (", 1)
    text = _port_decl(text, ASTK_QO, "output", 571)
    text = _assigns(text, ASTK_QO, 537, 572, mutant == "map")
    return text


def transform(text, mod, mutant=False):
    return transform_ahub(text, mutant) if mod == "qkd_ahub" else transform_astk(text, mutant)


def core_json(cj):
    """apply the compact rename to the core json (pin_class keys, port_decl widths) in place"""
    drops = drops_for(cj["module"])
    for port in drops:
        d = cj["port_decl"][port]
        if d[1] != {1: 35, 537: 571}[drops[port]] or d[2] != 0:
            raise SystemExit(f"am-g-drop: {port} declared {d}, expected the legacy width")
        cj["port_decl"][port] = [d[0], d[1] - 1, 0]
    pc = {}
    for n, c in cj["pin_class"].items():
        nn = rename(n, drops)
        if nn is not None:
            pc[nn] = c
    cj["pin_class"] = pc
    return cj


def plan_pins(pins, mod):
    """the plan pin rename (KV-PLAN3 delta) applied in memory; a plan that already carries it passes unchanged"""
    drops = drops_for(mod)
    names = {p["name"] for p in pins}
    legacy = [p for p in drops if f"{p}[{ {1: 35, 537: 571}[drops[p]] }]" in names]
    if not legacy:
        return pins, []
    if len(legacy) != len(drops):
        raise SystemExit(f"am-g-drop: plan pins half-renamed ({legacy})")
    out, dropped = [], []
    for p in pins:
        nn = rename(p["name"], drops)
        if nn is None:
            dropped.append(p["name"])
            continue
        q = dict(p)
        q["name"] = nn
        out.append(q)
    return out, dropped
