"""leaf_pinreg: the LEAF-REGISTERED crossing proof on a kit's synthesized netlist (DIE-KV-64 11-03, option 2).

    python3 tools/die_plan/leaf_pinreg.py NETLIST.v --decl leaf_pinreg.json [--top MOD] [--libs a.lib ...]
                                          [--spare spare_out.json] [--out leaf_pinreg_result.json]   # exit 1 = FAIL

A plan lane marked registered "leaves" binds with NO ot_dp_st boundary station on either side (bind.py, 0 added
cycles): the sending and receiving leaf flops ARE the boundary registers, and the kit SDC gives each side half the
period.  That holds only if synthesis (incl. retiming) kept a register at every bit, so this check runs on every kit
netlist (face_guard.py calls it when the kit carries leaf_pinreg.json) and FAILS CLOSED:
  - an input data bit: every load, through at most MAX_CHAIN single-input buffers / inverters, is the D pin of a flop
    or a registered input pin of a hard macro (liberty: setup AND hold to a clock pin).  Any other load (logic, a flop
    clock / reset / enable pin, an output port, an unknown macro pin) fails.  A bit with no load is recorded (unread).
  - an output data bit: its driver, back through at most MAX_CHAIN single-input buffers / inverters, is the Q / QN of a
    flop or a registered output pin of a hard macro (liberty clock-to-q).  Logic, another port (feedthrough), several
    drivers, or a constant fails -- a constant only passes on a declared spare bit (kit spare_out.json).
The epoch bit (index data_bits when the bus carries one) has no register on such a lane and is not checked.
Fan-out of a leaf flop to internal logic is allowed (the flop is a leaf register, not a dedicated face flop).
Data-driven, no names: the declared buses come from the plan (gen_phys.regleaf_buses).
"""
import argparse
import gzip
import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_guard as FG          # noqa: E402  (netlist parser / flattener shared with the face-register guard)

SCHEMA = "opentallas.kit_leaf_pinreg.v1"
MAX_CHAIN = 3
Q_PINS = {"Q", "QN"}
TIE_RE = re.compile(r"^TIE(HI|LO)", re.I)


def load_decl(path):
    """{port: dict(dir, data_bits, epoch)} from a kit leaf_pinreg.json; fail closed on a malformed declaration."""
    doc = json.loads(Path(path).read_text())
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema must be {SCHEMA}")
    buses = doc.get("buses")
    if not isinstance(buses, dict) or not buses:
        raise ValueError(f"{path}: buses must be a non-empty object")
    for n, v in buses.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n) or not isinstance(v, dict) or v.get("dir") not in ("in", "out") \
                or not isinstance(v.get("data_bits"), int) or v["data_bits"] < 1 or not isinstance(v.get("epoch"), bool):
            raise ValueError(f"{path}: bus {n!r}: want {{dir: in|out, data_bits: int >= 1, epoch: bool}}, got {v}")
    return buses


def lib_cells(files):
    """{cell: {pin: dict(dir, clock, arcs)}} over liberty files (.lib or .lib.gz), hard_pinreg.parse_lib."""
    import hard_pinreg as HP
    cells = {}
    for f in files or ():
        f = Path(f)
        if f.suffix == ".gz":
            with tempfile.NamedTemporaryFile("w", suffix=".lib", delete=False) as t:
                t.write(gzip.open(f, "rt", errors="replace").read())
            cells.update(HP.parse_lib(t.name))
            Path(t.name).unlink()
        else:
            cells.update(HP.parse_lib(f))
    return cells


def _macro_pin(cells, master, pin):
    """'in_reg' / 'out_reg' when the liberty view registers that macro pin, 'in' / 'out' when it does not, None when
    the macro or pin is unknown."""
    import hard_pinreg as HP
    pins = cells.get(master)
    if pins is None:
        return None
    d = pins.get(pin) or pins.get(re.sub(r"\[\d+\]$", "", pin))
    if d is None:
        return None
    clocks = {n for n, x in pins.items() if x["clock"]}
    arcs = [t for r, t in d["arcs"] if r in clocks]
    if d["dir"] == "input":
        return "in_reg" if any(t.startswith("setup_") for t in arcs) and any(t.startswith("hold_") for t in arcs) \
            else "in"
    if d["dir"] == "output":
        return "out_reg" if any(t in HP.CLOCK_TO_Q for t in arcs) else "out"
    return None


def check(text, decl, top=None, libs=(), spare=(), max_chain=MAX_CHAIN):
    """-> dict(verdict PASS/FAIL, top, checked, ok, unread, ends{flop, macro, spare}, fails{class: [..]})"""
    cells = lib_cells(libs)
    spare = set(spare or ())                     # exact port bit names (spare_out.json bits)
    mods = FG.parse(text)
    if top is None:
        used = {typ for M in mods.values() for typ, _, _ in M.cells}
        tops = [m for m in mods if m not in used]
        if len(tops) != 1:
            raise ValueError(f"cannot pick the top module: {tops}")
        top = tops[0]
    T = mods[top]
    F = FG.Flat(mods, top)
    # pin directions: the liberty view for a known macro (its output pins are not in face_guard's OUT_PINS)
    drv, loads = defaultdict(list), defaultdict(list)
    for ci, (m, path, pp) in enumerate(F.cells):
        for p, (d, bits) in pp.items():
            if m in cells and (p in cells[m] or any(re.sub(r"\[\d+\]$", "", k) == p for k in cells[m])):
                lp = cells[m].get(p) or {}
                d = "out" if lp.get("dir") == "output" else "in"
            for b in bits:
                (drv if d == "out" else loads)[F.find(b)].append((ci, p))
    port_of = defaultdict(list)
    for p in T.ports:
        for b in FG._bits_of(T, p):
            port_of[F.find(b)].append((p, T.dirs.get(p)))
    res = dict(top=top, checked=0, ok=0, unread=[], ends=dict(flop=0, macro=0, spare=0), fails=defaultdict(list))

    def fail(cls, b, why):
        res["fails"][cls].append(f"{b}: {why}")

    def single_in(pp):
        ins = [v for _k, (dd, v) in pp.items() if dd == "in"]
        return F.find(ins[0][0]) if len(ins) == 1 and len(ins[0]) == 1 else None

    def fwd(net, b, depth, port):
        """True when every load of net ends at a registered input; failures are recorded."""
        ok = True
        if any(d == "output" for _p, d in port_of.get(net, ())):
            fail("feedthrough", b, f"reaches output port {[p for p, d in port_of[net] if d == 'output'][:2]}")
            return False
        for cj, pin in loads[net]:
            m, path, pp = F.cells[cj]
            if FG.is_ff(m):
                if pin == "D":
                    res["ends"]["flop"] += 1
                    continue
                fail("flop_pin", b, f"loads {m} {path}/{pin} (not the D pin)")
                ok = False
            elif not FG._std_cell(m):
                kind = _macro_pin(cells, m, pin)
                if kind == "in_reg":
                    res["ends"]["macro"] += 1
                    continue
                fail("macro", b, f"loads {m} {path}/{pin}: " + ("no liberty view" if kind is None else
                                                                 "pin without setup+hold to a clock"))
                ok = False
            elif FG.is_buf(m) and depth < max_chain and single_in(pp) == net:
                outs = [v for _k, (dd, v) in pp.items() if dd == "out"]
                if len(outs) != 1 or len(outs[0]) != 1:
                    fail("comb_end", b, f"loads {m} {path} (not a single-output buffer)")
                    ok = False
                    continue
                ok &= fwd(F.find(outs[0][0]), b, depth + 1, port)
            else:
                fail("comb_end", b, f"loads {m} {path}/{pin} (logic, or a buffer chain deeper than {max_chain})")
                ok = False
        return ok

    def back(net, b, depth):
        ds = drv[net]
        if net.startswith("CONST_"):
            if b in spare:
                res["ends"]["spare"] += 1
                return True
            fail("const", b, f"constant {net}")
            return False
        ins = [p for p, d in port_of.get(net, ()) if d == "input"]
        if ins:
            fail("feedthrough", b, f"wired from input port {ins[0]}")
            return False
        if len(ds) != 1:
            fail("undriven" if not ds else "multi", b, f"{len(ds)} drivers")
            return False
        ci, pin = ds[0]
        m, path, pp = F.cells[ci]
        if FG.is_ff(m):
            if pin in Q_PINS:
                res["ends"]["flop"] += 1
                return True
            fail("flop_pin", b, f"driven by {m} {path}/{pin}")
            return False
        if not FG._std_cell(m):
            kind = _macro_pin(cells, m, pin)
            if kind == "out_reg":
                res["ends"]["macro"] += 1
                return True
            fail("macro", b, f"driven by {m} {path}/{pin}: " + ("no liberty view" if kind is None else
                                                                "pin without a clock-to-q arc"))
            return False
        if TIE_RE.match(m):
            if b in spare:
                res["ends"]["spare"] += 1
                return True
            fail("const", b, f"driven by {m} {path}")
            return False
        nxt = single_in(pp)
        if FG.is_buf(m) and depth < max_chain and nxt is not None:
            return back(nxt, b, depth + 1)
        fail("comb_end", b, f"driven by {m} {path} (logic, or a buffer chain deeper than {max_chain})")
        return False

    for n, v in sorted(decl.items()):
        want = "input" if v["dir"] == "in" else "output"
        if T.dirs.get(n) != want:
            fail("port", n, f"declared {want} bus is {T.dirs.get(n)} in {top}")
            continue
        bits = FG._bits_of(T, n)
        need = v["data_bits"] + int(v["epoch"])
        if len(bits) != need:
            fail("port", n, f"{len(bits)} bits, declared {v['data_bits']} data + {int(v['epoch'])} epoch")
            continue
        for i in range(v["data_bits"]):
            b = f"{n}[{i}]" if n in T.wires else n
            net = F.find(b)
            res["checked"] += 1
            if want == "input":
                if len(drv[net]):
                    fail("multi", b, f"input port net also driven by {len(drv[net])} cell(s)")
                    continue
                if not loads[net] and not any(d == "output" for _p, d in port_of.get(net, ())):
                    res["unread"].append(b)
                    res["ok"] += 1
                    continue
                if fwd(net, b, 0, n):
                    res["ok"] += 1
            elif back(net, b, 0):
                res["ok"] += 1
    res["fails"] = {k: v for k, v in sorted(res["fails"].items())}
    res["fail_counts"] = {k: len(v) for k, v in res["fails"].items()}
    res["unread"] = res["unread"][:200]
    res["verdict"] = "PASS" if not res["fails"] and res["checked"] == res["ok"] else "FAIL"
    return res


def kit_check(kitdir, netlist_text, top=None):
    """the kit-level run face_guard makes when the kit carries leaf_pinreg.json: libs from kit macros/, spare bits
    from spare_out.json.  None when the kit declares no leaf-registered bus."""
    kd = Path(kitdir)
    f = kd / "leaf_pinreg.json"
    if not f.is_file():
        return None
    decl = load_decl(f)
    libs = sorted(p for p in (kd / "macros").glob("*.lib*") if re.search(r"\.lib(\.gz)?$", p.name)) \
        if (kd / "macros").is_dir() else []
    sp = kd / "spare_out.json"
    spare = FG.kit_spare_list(kd) if sp.is_file() else []
    return check(netlist_text, decl, top, libs=libs, spare=spare)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("netlist")
    ap.add_argument("--decl", required=True, help="kit leaf_pinreg.json")
    ap.add_argument("--top")
    ap.add_argument("--libs", nargs="*", default=[], help="liberty views of the hard macros in the netlist")
    ap.add_argument("--spare", help="kit spare_out.json (declared constant output bits)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    spare = FG.spare_out_list(json.loads(Path(a.spare).read_text())) if a.spare else []
    r = check(Path(a.netlist).read_text(), load_decl(a.decl), a.top, libs=a.libs, spare=spare)
    r["netlist"] = a.netlist
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + "\n")
    print(f"LEAF_PINREG {r['verdict']} top {r['top']} bits {r['checked']} ok {r['ok']} ends {r['ends']} "
          f"fails {r['fail_counts']}")
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
