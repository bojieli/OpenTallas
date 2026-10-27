"""Declared pushdown feed-through ports (METHODOLOGY 12.2a1; COORD 2026-10-26 12:55 ruling QC-SU-BTAB ASK).

The master plan's pushdown islands give a core dedicated ft ports (ft_ck_i -> fixed BUF -> ft_ck_o,
ft_rst_i -> fixed BUF -> ft_rst_o, clock-repeater pairs).  They are DIE-TIMED, not core IO:

  1  the core kit SDC carries NO input/output delay (and no load/driving cell) on a declared ft port;
  2  a clock ft arc is a clock pass-through: characterised (TT/FF delay) into the kit interface model
     ft_interface.json; the die clock STA propagates through it, the core never times it as data;
  3  a reset ft arc is reported as an interface arc the same way, timed in die STA against the reset wavefront plan.

Declaration = core_infra_plan.json (compile_slice: ports + arcs) -> kit ft_ports.json {ports, arcs, sha256}.
sdc_lint allows exactly the declared ports (hash checked), still bans set_false_path, and fails if an arc is
missing from the interface model; signoff characterises the arcs and fails on a missing / uncharacterised arc or
any undeclared unconstrained endpoint (signoff.py ft_char_tcl / ft_fill_model).  No declaration (no pushdown) = nothing here runs: kits are byte-identical.

    python3 tools/die_plan/ft_ports.py declare KITDIR --arc CELL:IN:OUT[:KIND] ...  # kits without core_infra_plan.json
    python3 tools/die_plan/ft_ports.py install KITDIR                               # SDC + sdc_lint.json + model
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sdc_lint import FT_SCHEMA as SCHEMA, FT_MODEL_SCHEMA as MODEL_SCHEMA, ft_digest as digest, \
    ft_verify as verify, ft_model_errors as model_errors, FT_KINDS as KINDS  # noqa: E402  (kept in sdc_lint: standalone kits)
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
# the kit IO environment the arcs are characterised under (same as every other core IO port)
CHAR_ENV = dict(driving_cell="BUFx4_ASAP7_75t_R", load_ff=2.0)
_ALL_IN = "[all_inputs -no_clocks]"
_ALL_OUT = "[all_outputs]"


class FtError(ValueError):
    pass


def _kind(src, dst, given=None, cell=""):
    if given:
        if given not in KINDS:
            raise FtError(f"ft arc {src}->{dst}: kind {given!r} not in {KINDS}")
        return given
    m = re.search(r"_(ck|rst)[0-9]+\Z", cell or "")        # core_infra island driver cells mp_<island>_ck<k> / _rst<k>
    if m:
        return "clock" if m.group(1) == "ck" else "reset"
    if re.search(r"(^|_)(ck|clk)(_|$)", src) or "_ck_" in src:
        return "clock"
    if re.search(r"(^|_)rst(_|$)", src) or "_rst_" in src:
        return "reset"
    raise FtError(f"ft arc {src}->{dst}: kind not derivable from the port name; declare clock or reset")


def declaration(arcs, source):
    """arcs: [{cell, source, sink, kind?}] -> the kit declaration (ports derived from the arcs, one pair per arc
    direction-checked).  Several parallel cells on one port pair (island driver parallel > 1) are one arc."""
    pairs, ports, cells = {}, {}, {}
    for a in arcs:
        s, d = a["source"], a["sink"]
        for n in (s, d):
            if not IDENT.fullmatch(n):
                raise FtError(f"invalid ft port name {n!r}")
        if s == d:
            raise FtError(f"ft arc {s}->{d}: source = sink")
        for n, dr in ((s, "INPUT"), (d, "OUTPUT")):
            if ports.get(n, dr) != dr:
                raise FtError(f"ft port {n} used as both input and output")
            ports[n] = dr
        k = _kind(s, d, a.get("kind"), a.get("cell", ""))
        if pairs.get((s, d), k) != k:
            raise FtError(f"ft arc {s}->{d}: conflicting kinds")
        pairs[(s, d)] = k
        cells.setdefault((s, d), []).append(a["cell"])
    if not pairs:
        raise FtError("empty ft declaration")
    srcs = [s for s, _ in pairs]
    sinks = [d for _, d in pairs]
    if len(set(sinks)) != len(sinks):
        raise FtError("an ft output is driven by two declared arcs")
    if len(set(srcs)) != len(srcs):
        raise FtError("an ft input feeds two declared arcs (one in/out pair per arc)")
    P = [dict(name=n, direction=d) for n, d in sorted(ports.items())]
    A = [dict(source=s, sink=d, kind=k, cells=sorted(cells[(s, d)])) for (s, d), k in sorted(pairs.items())]
    return dict(schema=SCHEMA, source=source, ports=P, arcs=A, sha256=digest(P, A))


def from_core_infra_plan(plan, source="core_infra_plan.json"):
    return declaration(plan.get("arcs", []), source)


def model_skeleton(decl):
    """kit interface model (declared, not yet characterised): one entry per declared arc."""
    return dict(schema=MODEL_SCHEMA, ft_sha256=decl["sha256"], status="declared", env=CHAR_ENV,
                note="12.2a1 die-owned ft arcs: clock = pass-through propagated by die clock STA; reset = interface arc "
                     "timed in die STA vs the reset wavefront plan; never core IO. delays ps, filled by signoff.",
                arcs=[dict(source=a["source"], sink=a["sink"], kind=a["kind"], tt_ps=None, ff_ps=None) for a in decl["arcs"]])


def lint_ctx(decl):
    """sdc_lint context fields for a declared kit."""
    return dict(ft_ports=decl)


def apply_sdc(text, inputs, outputs, clock_ports=()):
    """generator SDC form -> FT-safe form: the port sets all_inputs -no_clocks / all_outputs (which in the built
    core include the pushdown ft ports) become the explicit core IO port lists, so no IO delay, load or driving
    cell reaches a declared ft port.  Fail-closed on any other all_inputs/all_outputs form."""
    if not inputs and _ALL_IN in text or not outputs and _ALL_OUT in text:
        raise FtError("cannot make the SDC ft-safe: empty core IO list")
    t = text.replace(_ALL_IN, "[get_ports {%s}]" % " ".join(inputs)) if inputs else text
    t = t.replace(_ALL_OUT, "[get_ports {%s}]" % " ".join(outputs)) if outputs else t
    for c in _commands(t):
        if re.search(r"\[\s*all_(inputs|outputs)\b", c):
            raise FtError(f"SDC still selects ports by all_inputs/all_outputs (would time ft ports): {c}")
    return t


def _commands(text):
    return [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def install(kd, decl=None):
    """kit dir with constraint.sdc + sdc_lint.json (+ core_infra_plan.json or a given declaration) ->
    ft_ports.json, ft_interface.json, ft-safe constraint.sdc, sdc_lint.json ft context; re-lints.  No
    declaration -> False and nothing is touched (byte-identical kits)."""
    kd = Path(kd)
    if decl is None:
        p = kd / "core_infra_plan.json"
        if not p.is_file():
            return False
        plan = json.loads(p.read_text())
        if not plan.get("arcs"):
            return False
        decl = from_core_infra_plan(plan)
    e = verify(decl)
    if e:
        raise FtError("; ".join(e))
    ctx = json.loads((kd / "sdc_lint.json").read_text())
    names = {p["name"] for p in decl["ports"]}
    clash = names & set(ctx.get("inputs", []) + ctx.get("outputs", []) + ctx.get("clock_ports", []))
    if clash:
        raise FtError(f"declared ft ports are also core IO / clock ports: {sorted(clash)}")
    sdc = (kd / "constraint.sdc").read_text()
    new = apply_sdc(sdc, ctx["inputs"], ctx["outputs"], ctx.get("clock_ports", []))
    ctx.update(lint_ctx(decl))
    mp = kd / "ft_interface.json"
    model = json.loads(mp.read_text()) if mp.is_file() else None
    if model is None or model_errors(decl, model):
        model = model_skeleton(decl)
    import sdc_lint
    err = sdc_lint.lint(new, **ctx, ft_interface=model)      # lint BEFORE any kit file is written (fail = untouched)
    if err:
        raise FtError(f"{kd}: ft-safe constraint.sdc fails sdc_lint ({len(err)}): " + "; ".join(err[:8]))
    (kd / "ft_ports.json").write_text(json.dumps(decl, indent=1) + "\n")
    mp.write_text(json.dumps(model, indent=1) + "\n")
    (kd / "constraint.sdc").write_text(new)
    (kd / "sdc_lint.json").write_text(json.dumps(ctx, indent=1) + "\n")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("declare")
    d.add_argument("kitdir")
    d.add_argument("--arc", action="append", required=True, help="CELL:IN:OUT[:clock|reset]")
    d.add_argument("--source", required=True, help="where the plan declares these ports (file@sha)")
    i = sub.add_parser("install")
    i.add_argument("kitdir")
    a = ap.parse_args(argv)
    if a.cmd == "declare":
        arcs = []
        for s in a.arc:
            f = s.split(":")
            if len(f) not in (3, 4):
                raise SystemExit(f"--arc {s}: CELL:IN:OUT[:KIND]")
            arcs.append(dict(cell=f[0], source=f[1], sink=f[2], **({"kind": f[3]} if len(f) == 4 else {})))
        decl = declaration(arcs, a.source)
        install(a.kitdir, decl)
    else:
        kd = Path(a.kitdir)
        decl = json.loads((kd / "ft_ports.json").read_text()) if (kd / "ft_ports.json").is_file() else None
        if not install(kd, decl):
            raise SystemExit(f"{kd}: no ft declaration (core_infra_plan.json arcs / ft_ports.json)")
    print(f"FT_PORTS installed {a.kitdir}")


if __name__ == "__main__":
    main()
