#!/usr/bin/env python3
"""DIE-PROTO-3 (COORD 11-12): ot_clk -> die_sta routed-tree adapter.

die_sta.py run --spine-tree DIR wants DIR/ctree.v with ONE module `die_ctree` (input root, one output
t_<inst>__<port> per partition clock pin) and, for routed evidence, DIR/ctree.spef (the module's own SPEF, read with
-path u_dieclk).  ot_clk (tools/clk/ot_clk.py kit) writes the same port contract under module name `ctree`, and its
routed RC only exists inside the die combo GRT (signal kit + clock tree in one global_route, clock cells/nets renamed
with a prefix, default `ck_`).  This adapter:

  tcl    patch a combo GRT Tcl so `estimate_parasitics -global_routing` also writes the GRT-estimated SPEF
         (OpenROAD `-spef_file`); exactly one estimate_parasitics -global_routing line must be present.
  build  ctree.v + combo SPEF -> DIR/{ctree.v, ctree.spef, adapter.json}: the module renamed to die_ctree (port list
         checked), and the SPEF reduced to the clock tree's nets (prefix stripped, *NAME_MAP resolved, *PORTS = root +
         t_*), *DESIGN die_ctree.  Fails closed when a tree net that drives a cell or a port has no D_NET in the SPEF
         (no silent ideal wires), or when a SPEF instance/net cannot be mapped back to the tree.

The SPEF values are OpenROAD's GRT estimates (setRC layer RC on the global routes), the same RC the die clock readout
(arr_<C>.txt) was timed with, so die_sta's tree arrivals match the clock proof.

usage:
  ot_clk_die_ctree.py tcl  COMBO_TCL SPEF_PATH [--out PATCHED_TCL]
  ot_clk_die_ctree.py build --ctree-v CTREE_V --spef COMBO_SPEF --out DIR [--prefix ck_] [--tree TREE_JSON]
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

MODULE_IN = "ctree"
MODULE_OUT = "die_ctree"
TAP_RE = re.compile(r"^t_[A-Za-z0-9_]+__[A-Za-z0-9_]+$")


class AdapterError(ValueError):
    pass


# ----------------------------------------------------------------------------------------------------------- verilog
def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def read_ctree(text):
    """-> dict(ports, inputs, outputs, cells {inst: master}, nets set, assigns [(lhs, rhs)], drivers set).
    The ot_clk ctree netlist is flat: one module, cell instances with named pin connections, wires, assigns."""
    body = _strip_comments(text)
    mods = re.findall(r"\bmodule\s+(\S+)\s*\(", body)
    if len(mods) != 1:
        raise AdapterError(f"ctree.v must hold exactly one module, found {mods}")
    if mods[0] != MODULE_IN and mods[0] != MODULE_OUT:
        raise AdapterError(f"ctree.v module is {mods[0]!r}, expected {MODULE_IN!r}")
    m = re.search(r"\bmodule\s+\S+\s*\(([^)]*)\)\s*;(.*)\bendmodule\b", body, re.S)
    ports = [p.strip() for p in m.group(1).split(",") if p.strip()]
    inner = m.group(2)
    inputs, outputs, wires = set(), set(), set()
    for kind, names in re.findall(r"\b(input|output|wire)\b([^;]*);", inner):
        for n in names.split(","):
            n = n.strip()
            if not n:
                continue
            {"input": inputs, "output": outputs, "wire": wires}[kind].add(n)
    assigns = re.findall(r"\bassign\s+(\S+)\s*=\s*(\S+?)\s*;", inner)
    cells, drivers, loads = {}, set(), set()
    for master, inst, conns in re.findall(r"^\s*([A-Za-z_][\w$]*)\s+(\S+)\s*\((.*?)\)\s*;", inner, re.M | re.S):
        if master in ("input", "output", "wire", "assign", "module"):
            continue
        cells[inst] = master
        for pin, net in re.findall(r"\.(\w+)\s*\(\s*([^)\s]*)\s*\)", conns):
            if not net:
                continue
            (drivers if pin in ("Y", "Z", "ZN", "Q", "QN") else loads).add(net)
    if set(ports) != inputs | outputs:
        raise AdapterError("port list and input/output declarations differ")
    if inputs != {"root"}:
        raise AdapterError(f"ctree must have exactly one input `root`, found {sorted(inputs)}")
    bad = sorted(p for p in outputs if not TAP_RE.match(p))
    if bad:
        raise AdapterError(f"ctree outputs must be t_<inst>__<port>: {bad[:5]}")
    nets = wires | inputs | outputs | drivers | loads | {x for a in assigns for x in a}
    return dict(module=mods[0], ports=ports, inputs=inputs, outputs=outputs, cells=cells, nets=nets,
                assigns=assigns, drivers=drivers, loads=loads)


def port_aliases(T):
    """{internal net: port} for `assign <port> = <net>` (or reversed): die_ctree carries the port name only, so the
    netlist read by die_sta and the SPEF name the net the same way (no assign-merge naming ambiguity)."""
    portset, out = T["inputs"] | T["outputs"], {}
    for l, r in T["assigns"]:
        if l in portset and r in portset:
            raise AdapterError(f"assign joins two ports ({l} = {r}): not a tree")
        if l in portset:
            out[r] = l
        elif r in portset:
            out[l] = r
    return out


def canonical_verilog(text, T):
    """rename module -> die_ctree; replace every port-aliased internal net by its port and drop those assigns/wires."""
    al = port_aliases(T)
    text = rename_module(text)
    out = []
    for ln in text.splitlines():
        m = re.match(r"^\s*assign\s+(\S+)\s*=\s*(\S+?)\s*;\s*$", ln)
        if m and (al.get(m.group(1)) == m.group(2) or al.get(m.group(2)) == m.group(1)):
            continue
        m = re.match(r"^\s*wire\s+(\S+)\s*;\s*$", ln)
        if m and m.group(1) in al:
            continue
        if "(" in ln and al:
            ln = re.sub(r"\(\s*([^()\s,]+)\s*\)", lambda x: "(" + al.get(x.group(1), x.group(1)) + ")", ln)
        out.append(ln)
    return "\n".join(out) + "\n"


def rename_module(text):
    n = len(re.findall(rf"\bmodule\s+{MODULE_IN}\s*\(", text))
    if n == 0 and re.search(rf"\bmodule\s+{MODULE_OUT}\s*\(", text):
        return text
    if n != 1:
        raise AdapterError(f"expected one `module {MODULE_IN} (`, found {n}")
    return re.sub(rf"\bmodule\s+{MODULE_IN}\s*\(", f"module {MODULE_OUT} (", text, count=1)


# -------------------------------------------------------------------------------------------------------------- tcl
def patch_tcl(text, spef_path):
    pat = re.compile(r"^(\s*estimate_parasitics\s+-global_routing)(\s*)$", re.M)
    hits = pat.findall(text)
    if len(hits) != 1:
        raise AdapterError(f"expected exactly one `estimate_parasitics -global_routing` line, found {len(hits)}")
    if "-spef_file" in text:
        raise AdapterError("combo Tcl already writes a SPEF (-spef_file present)")
    return pat.sub(lambda m: f"{m.group(1)} -spef_file {spef_path}{m.group(2)}", text, count=1)


# ------------------------------------------------------------------------------------------------------------- spef
def _unesc(name):
    return name.replace("\\", "")


def parse_spef(text):
    """-> (header lines, name map {*k: name}, ports [(name, dir, rest)], nets [(name, total, [section lines])]).
    Supports the subset OpenROAD writes: header keywords, *NAME_MAP, *PORTS, *D_NET ... *END blocks."""
    lines = text.splitlines()
    header, nmap, ports, nets = [], {}, [], []
    i, mode = 0, "header"
    while i < len(lines):
        ln = lines[i].strip()
        i += 1
        if not ln or ln.startswith("//"):
            continue
        if ln.startswith("*NAME_MAP"):
            mode = "map"
            continue
        if ln.startswith("*PORTS"):
            mode = "ports"
            continue
        if ln.startswith("*D_NET"):
            p = ln.split()
            name, total, body = p[1], p[2] if len(p) > 2 else "0", []
            while i < len(lines):
                b = lines[i].strip()
                i += 1
                if b.startswith("*END"):
                    break
                if b:
                    body.append(b)
            else:
                raise AdapterError(f"unterminated *D_NET {name}")
            nets.append((name, total, body))
            mode = "nets"
            continue
        if mode == "header":
            header.append(ln)
        elif mode == "map":
            if ln.startswith("*") and len(ln.split(None, 1)) == 2 and re.match(r"^\*\d+$", ln.split()[0]):
                k, v = ln.split(None, 1)
                nmap[k] = _unesc(v.strip())
            else:
                header.append(ln)
                mode = "header"
        elif mode == "ports":
            p = ln.split()
            if p[0].startswith("*") and not re.match(r"^\*\d+$", p[0]) and p[0] not in nmap:
                header.append(ln)
                mode = "header"
                continue
            ports.append((p[0], p[1] if len(p) > 1 else "B", " ".join(p[2:])))
    return header, nmap, ports, nets


def _resolve(tok, nmap):
    """'*12' / '*12:A' / 'name' / 'name:3' -> plain 'name' / 'name:A'."""
    if tok.startswith("*") and re.match(r"^\*\d+", tok):
        k, _, rest = tok.partition(":")
        if k not in nmap:
            raise AdapterError(f"SPEF token {tok} not in *NAME_MAP")
        base = nmap[k]
        return base + (":" + rest if rest else "")
    return _unesc(tok)


def _restore_pin_cap(total, body):
    """OpenROAD `estimate_parasitics -spef_file` writes each D_NET's total capacitance, but the *CAP section omits the
    ground cap of the pin-access segments (the nodes named by *CONN pins): on the HEAD FREG die tree sum(*CAP) is 88 %
    of the D_NET totals, and timing the written SPEF reads 2.5-3.6 % early against the in-flow readout.  Restore the
    difference (total - sum(*CAP)) as ground cap split equally over the net's *CONN pin nodes.  Fleet check (HEAD FREG,
    12985 taps, OpenROAD STA on the adapter output vs the in-flow arr_TT readout): -284 ps worst without it, -1.0 /
    +4.0 ps with it.  -> (new body, cap added fF)."""
    pins, caps, out, sec, n = [], 0.0, [], None, 0
    for b in body:
        if b.startswith("*CONN"):
            sec = "conn"
        elif b.startswith("*CAP"):
            sec = "cap"
        elif b.startswith("*RES") or b.startswith("*INDUC"):
            sec = "res"
        elif sec == "conn" and (b.startswith("*P ") or b.startswith("*I ")):
            pins.append(b.split()[1])
        elif sec == "cap" and b[:1].isdigit():
            p = b.split()
            n = max(n, int(p[0]))
            if len(p) == 3:
                caps += float(p[2])
    gap = float(total) - caps
    if gap <= 1e-6 or not pins:
        return body, 0.0
    share = gap / len(pins)
    for b in body:
        if b.startswith("*RES") or b.startswith("*INDUC"):
            for k, pn in enumerate(pins, 1):
                out.append(f"{n + k} {pn} {share:.6g}")
        out.append(b)
    if not any(b.startswith("*RES") for b in body):
        out += [f"{n + k} {pn} {share:.6g}" for k, pn in enumerate(pins, 1)]
    return out, gap


def build(ctree_v, combo_spef, out, prefix="ck_", tree_json=None, restore_cap="pins"):
    vt = Path(ctree_v).read_text()
    T = read_ctree(vt)
    st = Path(combo_spef).read_text()
    header, nmap, ports, nets = parse_spef(st)
    portset = T["inputs"] | T["outputs"]
    al = port_aliases(T)
    known = T["nets"] | set(T["cells"])

    def to_tree(name):
        """combo name -> canonical tree name (port-aliased nets -> their port), or None outside the tree."""
        if name in portset:
            return name
        if prefix and name.startswith(prefix) and name[len(prefix):] in known:
            n = name[len(prefix):]
        elif not prefix and name in known:
            n = name
        else:
            return None
        return al.get(n, n)

    def node(tok):
        """'net:k' internal node / 'inst:pin' / port -> tree names; None when outside the tree."""
        base, sep, rest = tok.partition(":")
        t = to_tree(base)
        return None if t is None else t + (sep + rest if sep else "")

    kept, dropped, foreign, restored = [], 0, [], 0.0
    for raw, total, body in nets:
        name = _resolve(raw, nmap)
        tn = to_tree(name)
        if tn is None:
            dropped += 1
            continue
        nb = []
        for b in body:
            if b.startswith("*"):
                nb.append(b)
                continue
            p = b.split()
            # *CONN rows: '*P name dir' / '*I inst:pin dir ...' start with '*' -> handled below; numbered rows:
            # 'i node cap' (CAP), 'i node1 node2 cap|res' (CAP coupling / RES)
            out_p = [p[0]]
            for tok in p[1:]:
                if re.match(r"^-?[0-9.]+(e[-+]?\d+)?$", tok, re.I):
                    out_p.append(tok)
                    continue
                t = node(_resolve(tok, nmap))
                if t is None:
                    foreign.append(f"{tn}: {tok}")
                    t = tok
                out_p.append(t)
            nb.append(" ".join(out_p))
        # CONN rows ('*P x I', '*I inst:pin O ...')
        conn = []
        for b in nb:
            if b.startswith("*P ") or b.startswith("*I "):
                p = b.split()
                t = node(_resolve(p[1], nmap))
                if t is None:
                    foreign.append(f"{tn}: {p[1]}")
                    t = p[1]
                conn.append(" ".join([p[0], t] + p[2:]))
            else:
                conn.append(b)
        if restore_cap == "pins":
            conn, add = _restore_pin_cap(total, conn)
            restored += add
        kept.append((tn, total, conn))
    if foreign:
        raise AdapterError(f"{len(foreign)} SPEF references leave the clock tree (shared net?): {foreign[:5]}")
    have = {n for n, _, _ in kept}
    # every net that a tree cell drives or that is a tree port must carry parasitics; assign aliases (t_x = nY) are one
    # net in OpenROAD/OpenSTA, named by either side, so a pair counts once
    cnt = Counter(n for n, _, _ in kept)
    dup = sorted(n for n, k in cnt.items() if k > 1)
    if dup:
        raise AdapterError(f"{len(dup)} tree nets appear twice in the SPEF after aliasing: {dup[:5]}")
    need = {al.get(n, n) for n in (T["drivers"] | T["outputs"] | T["inputs"])}
    missing = sorted(n for n in need if n not in have)
    if missing:
        raise AdapterError(f"{len(missing)} clock-tree nets have no D_NET in {combo_spef}: {missing[:8]}")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ctree.v").write_text(canonical_verilog(vt, T))
    hdr = []
    for h in header:
        if h.startswith("*DESIGN ") and not h.startswith("*DESIGN_FLOW"):
            hdr.append(f'*DESIGN "{MODULE_OUT}"')
        else:
            hdr.append(h)
    pin_dir = {"root": "I"}
    pin_dir.update({p: "O" for p in T["outputs"]})
    with open(out / "ctree.spef", "w") as f:
        f.write("\n".join(hdr) + "\n\n*PORTS\n")
        for p in T["ports"]:
            f.write(f"{p} {pin_dir[p]}\n")
        f.write("\n")
        for n, total, body in kept:
            f.write(f"*D_NET {n} {total}\n" + "\n".join(body) + "\n*END\n\n")
    if tree_json:
        shutil.copy(tree_json, out / "tree.json")
    rec = dict(tool="tools/clk/ot_clk_die_ctree.py", module=MODULE_OUT, prefix=prefix,
               inputs={str(Path(ctree_v).resolve()): hashlib.sha256(vt.encode()).hexdigest(),
                       str(Path(combo_spef).resolve()): hashlib.sha256(st.encode()).hexdigest()},
               tree_cells=len(T["cells"]), tree_ports=len(T["ports"]), spef_nets_kept=len(kept),
               spef_nets_dropped=dropped, restore_cap=restore_cap, restored_cap_ff=round(restored, 3), rc_basis="OpenROAD estimate_parasitics -global_routing (combo die GRT)")
    (out / "adapter.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tcl")
    t.add_argument("combo_tcl")
    t.add_argument("spef_path")
    t.add_argument("--out")
    b = sub.add_parser("build")
    b.add_argument("--ctree-v", required=True)
    b.add_argument("--spef", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--prefix", default="ck_")
    b.add_argument("--tree")
    b.add_argument("--restore-cap", choices=("pins", "none"), default="pins",
                   help="put D_NET total - sum(*CAP) back on the pin nodes (OpenROAD -spef_file omits it); default pins")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "tcl":
            s = patch_tcl(Path(a.combo_tcl).read_text(), a.spef_path)
            Path(a.out or a.combo_tcl).write_text(s)
            print(f"patched {a.out or a.combo_tcl}: estimate_parasitics -global_routing -spef_file {a.spef_path}")
        else:
            print(json.dumps(build(a.ctree_v, a.spef, a.out, a.prefix, a.tree, a.restore_cap), indent=1))
    except AdapterError as e:
        print(f"ot_clk_die_ctree: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
