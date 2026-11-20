#!/usr/bin/env python3
"""SETUP-TO-STAGE (CBC rule 11, OWNER 11-20 "fix setup misses with more pipeline stages; fix hold structurally, never by
changing the clock"): turn the failing setup paths of routed / GRT builds into plan rows for the die's next daily event.

  setup_to_stage.py harvest HARVEST.tsv --out DIR [--die D] [--slack-max PS]
        list the setup misses (HARVEST class b_setup, plus any routed row with DRC 0 and TT < -42 whose class names no
        other cause) -> DIR/jobs.tsv (die, type, host, kit, odb) and DIR/dump_<die>_<type>.sh, one dump per kit, to run
        through ot-run on the kit's host (the commands are printed, never run here).
  setup_to_stage.py dump-cmd KIT OUTDIR [--slack-max PS] [--nmax N]
        write OUTDIR/sts_session.tcl (the kit's own sign-off TT session, signoff/tt/session.tcl, cut before its first
        report, + one report_checks -format json of every failing endpoint) and OUTDIR/sts_dump.sh (the sign-off docker
        command with /out pointed at OUTDIR).  Same libraries, SPEF, SDC and uncertainty policy as the sign-off.
  setup_to_stage.py harvest-rows HARVEST-SETUP.tsv --out DIR [--die D] [--plans die=PLAN.json,...]
        rows from the harvested STA LOGS (endpoint groups + worst paths, names only, no wire length): the same classes from
        the pin names, n = 1 stage per failing hop (OWNER: +1 stage per hop), sites left to the generator; marked
        length "unmeasured" until the read-only STA dump of that kit (dump-cmd + rows) replaces the row with a sized one.
  setup_to_stage.py rows --paths sts_paths.json --type T --die D --out DIR [--plan PLAN.json] [--kit KIT]
        classify every failing path and write DIR/rows.json, DIR/rtl_requests.tsv, DIR/summary.md:
          PORT / BUS  a path that starts or ends at a type port or a boundary / station register of a bus
                      (u_bin_ / u_bout_ / u_lpad_ / u_ist_ / u_fl_ / u_fx_ / u_y_ ...): +n station registers on that bus
                      (internal_stations conn bus:<bus>), n = ceil(flight / cap) - 1, at least 1; cap 300 um
                      (half-cycle path: 200 um).  Sites evenly spaced on the worst path's launch -> capture line.
          CORE        a path that leaves or enters a hard core pin over soft wire only: relay_depth +n on the core pin
                      (side source when the core launches, sink when it captures); the whole valid / data bundle of
                      that pin takes the same D (BUNDLE-DEPTH, bind error otherwise).
          LOGIC       a soft register -> register path: an RTL pipeline request to the owning lane (module = common
                      hierarchy of launch and capture), with levels, cell ps, wire ps and flight.  Not a plan row.
        Every row is +cycles (pre-approved, OWNER 11-20); LATCHECK reprices the lanes at bind.

Hold is NOT handled here: hold residue goes to rule 2 (shared tap or launch-side lockup latch) and rule 7 (CTS subtree
balance, cross-tap guard).  The setup guard stays -42 ps; no clock-period fallback.
Estimator + row writer only (owner r703 / r704): it never edits a plan, never holds or gates.
"""
import argparse
import collections
import csv
import json
import math
import re
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cbc_rules as RULES  # noqa: E402

# OWNER 11-20 #6: placed-hop cap 300 um (half-cycle hops 200 um).  cbc_rules.hop_cap_um(die) wins once it exists
# (S81-DIE-R3 makes the knob die-scoped); until then the owner value.
HOP_CAP_UM = float(getattr(RULES, "PLACED_HOP_CAP_UM", 300.0))
HALF_HOP_CAP_UM = float(getattr(RULES, "HALF_CYCLE_HOP_CAP_UM", 200.0))
GUARD_PS = -42.0                     # R-MINIMAL setup gate at 833 ps (no period fallback for hold)
STD_CELL = re.compile(r"_ASAP7_|^(TAPCELL|FILLER|DECAP)")
BUF = re.compile(r"^(BUF|HB\d|INVx|CKINV|CKBUF)")
BOUNDARY = re.compile(r"(?:^|[._])u_(?:bin|bout|lpad|ist|fl|fx|lk|land|xland|cland|pin|pout)_(?P<bus>[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z][A-Za-z0-9]*)*?(?:_[io]\d+)?)(?:_\d+)?(?:[./$\[]|$)")


def hop_cap(die, half=False):
    f = getattr(RULES, "hop_cap_um", None)
    cap = float(f(die)) if callable(f) else HOP_CAP_UM
    return min(cap, HALF_HOP_CAP_UM) if half else cap


def _ps(v):
    return float(v) * 1e12


def _um(v):
    return float(v) * 1e6


def strip_top(name):
    return re.sub(r"^u_bound\.", "", name or "")


def port_bus(port, buses):
    """plan bus of a type port pin name (longest bus name that prefixes the port stem), else the stem"""
    stem = re.sub(r"\[\d+\]$", "", port or "")
    best = max((b for b in buses if stem == b or stem.startswith(b + "_") or stem.startswith(b)), key=len, default=None)
    return best or stem


def path_record(c):
    """one report_checks json check -> dict (ps, um)"""
    sp = c.get("source_path") or []
    if not sp:
        return None
    cell = wire = flight = 0.0
    lv = nb = 0
    for a, b in zip(sp, sp[1:]):
        d = _ps(b["arrival"] - a["arrival"])
        if a.get("instance") and a.get("instance") == b.get("instance"):
            cell += d
            if BUF.match(b.get("cell", "")):
                nb += 1
            else:
                lv += 1
        else:
            wire += d
            flight += _um(abs(a["x"] - b["x"]) + abs(a["y"] - b["y"]))
    s, e = sp[0], sp[-1]
    return dict(slack=_ps(c["slack"]), start=c.get("startpoint", ""), end=c.get("endpoint", ""),
                s_inst=s.get("instance", ""), s_cell=s.get("cell", ""), s_pin=s.get("pin", ""),
                e_inst=e.get("instance", ""), e_cell=e.get("cell", ""), e_pin=e.get("pin", ""),
                sxy=(_um(s["x"]), _um(s["y"])), exy=(_um(e["x"]), _um(e["y"])),
                straight=_um(abs(s["x"] - e["x"]) + abs(s["y"] - e["y"])), flight=flight,
                cell_ps=cell, wire_ps=wire, levels=lv, bufs=nb,
                half=(c.get("source_clock_edge") or "rise") != (c.get("target_clock_edge") or "rise"))


def is_core(inst, cell):
    return bool(inst) and bool(cell) and not STD_CELL.search(cell)


def common_module(a, b):
    if a in ("?", "") or b in ("?", ""):        # one end unknown (an endpoint group row): the known end's parent
        k = strip_top(b if a in ("?", "") else a).replace("/", ".")
        return k.rsplit(".", 1)[0] if "." in k else "<type top>"
    pa, pb = strip_top(a).replace("/", ".").split("."), strip_top(b).replace("/", ".").split(".")
    out = []
    for x, y in zip(pa, pb):
        if x != y:
            break
        out.append(x)
    return ".".join(out) or "<type top>"


def classify(p, buses=()):
    """-> (class, key, detail) for one path record"""
    for side in ("s", "e"):
        inst, pin = p[f"{side}_inst"], p[f"{side}_pin"]
        if not inst:                                   # a type port
            return "BUS", port_bus(pin, buses), f"port {pin}"
    for side in ("s", "e"):
        m = BOUNDARY.search(strip_top(p[f"{side}_inst"]))
        if m:
            b = port_bus(m.group("bus"), buses)
            # a bus only when the plan names it (or, without a plan, a lane-style name ..._i / _o<k>); control landings
            # (cland origin / rstart_tx) are fixed-latency contracts: an RTL / landing request, not a station row
            if (buses and b in buses) or (not buses and BUS_NAME.search(b)):
                return "BUS", b, f"boundary {p[side + '_inst']}"
    sc, ec = is_core(p["s_inst"], p["s_cell"]), is_core(p["e_inst"], p["e_cell"])
    if sc or ec:
        side = "source" if sc else "sink"
        inst = p["s_inst"] if sc else p["e_inst"]
        pin = (p["s_pin"] if sc else p["e_pin"]).rsplit("/", 1)[-1]
        if p["levels"] <= 2:                          # wire (+ buffers) only: a relay stage moves the hop
            if pin == "?":
                return "SKIP", strip_top(inst), "core pin unknown (covered by its endpoint group row)"
            return "CORE", (strip_top(inst), re.sub(r"\[\d+\]$", "", pin), side), f"{side} core {inst}"
    return "LOGIC", common_module(p["s_inst"], p["e_inst"]), "soft register path"


def stages_for(p, die):
    cap = hop_cap(die, p["half"])
    n = max(1, math.ceil(max(p["straight"], p["flight"] * 0.0) / cap) - 1)
    return n, cap


def sites(a, b, n):
    return [[round(a[0] + (b[0] - a[0]) * k / (n + 1), 3), round(a[1] + (b[1] - a[1]) * k / (n + 1), 3)] for k in range(1, n + 1)]


BUNDLE_PORT = re.compile(r"^(?P<stem>.+?)_(?P<sfx>v|d|c|a|m|s|sv|si)$")
BUS_NAME = re.compile(r"_(i|o)\d*$")


def rows_from_paths(paths, die, tn, plan_type=None, slack_max=0.0):
    t = plan_type or {}
    buses = [b.get("name") for b in t.get("buses") or [] if b.get("name")]
    have = {(r.get("inst"), r.get("port"), r.get("side", "source")): int(r.get("D", 0)) for r in t.get("relay_depth") or []}
    groups = collections.defaultdict(list)
    for p in paths:
        if p["slack"] >= slack_max:
            continue
        cls, key, _ = classify(p, buses)
        groups[(cls, json.dumps(key))].append(p)
    rows, rtl = [], []
    for (cls, key), ps in sorted(groups.items(), key=lambda kv: min(p["slack"] for p in kv[1])):
        key = json.loads(key)
        w = min(ps, key=lambda p: p["slack"])
        n, cap = stages_for(max(ps, key=lambda p: p["straight"]), die)
        base = dict(rule="R11", type=tn, paths=len(ps), worst_slack_ps=round(w["slack"], 1),
                    worst_start=w["start"], worst_end=w["end"], max_straight_um=round(max(p["straight"] for p in ps), 1),
                    hop_cap_um=cap, half_cycle=any(p["half"] for p in ps))
        if cls == "SKIP":
            continue
        if cls == "BUS":
            conn = f"bus:{key}"
            have_st = [e for e in t.get("internal_stations") or [] if e.get("conn") == conn]
            rows.append(dict(base, kind="internal_stations_add", conn=conn, add_regs=n, cycles=n,
                             sites_um=sites(w["sxy"], w["exy"], n), existing_entries=len(have_st),
                             note=f"+{n} station register(s) on {conn} (+{n} cycle on its lanes, LATCHECK reprices)"))
        elif cls == "CORE":
            inst, port, side = key
            ports = [port]
            m = BUNDLE_PORT.match(port)
            if m:      # the whole bundle takes one D (bind --strict BUNDLE-DEPTH)
                ports = sorted({port} | {pp for (i, pp, sd) in have if i == inst and sd == side and BUNDLE_PORT.match(pp or "")
                                         and BUNDLE_PORT.match(pp)["stem"] == m["stem"]})
            d0 = max([have.get((inst, pp, side), 0) for pp in ports] + [0])
            for pp in ports:
                r = dict(base, kind="relay_depth", inst=inst, port=pp, D=d0 + n, cycles=n,
                         note=f"relay_depth {inst}.{pp} D{d0} -> D{d0 + n} ({side}); bundle {','.join(ports)} one D")
                if side == "sink":
                    r["side"] = "sink"
                rows.append(r)
        else:
            rtl.append(dict(base, kind="rtl_pipeline", module=key,
                            levels=max(p["levels"] for p in ps), cell_ps=round(max(p["cell_ps"] for p in ps), 1),
                            wire_ps=round(max(p["wire_ps"] for p in ps), 1),
                            ask=("split the cone: +1 pipeline register (levels %d, cells %.0f ps)" % (w["levels"], w["cell_ps"])
                                 if w["cell_ps"] >= RULES.LOGIC_PS_MAX * 0.75 or w["levels"] > RULES.DEPTH_LEVELS_MAX
                                 else "wire-bound soft path (%.0f um): +1 register mid-path or co-locate the cone" % w["straight"])))
    return rows, rtl


FLOP_PIN = re.compile(r"/(D|Q|QN|CLK|SE|SI|RESETN|SETN)$")


def name_record(start, end, slack):
    """a path record from names only (STA log rows): ports have no hierarchy, a pin that is not a flop pin on an
    instance without a yosys cell suffix ($_DFF..) is a hard-core pin"""
    def side(n):
        n = n or ""
        if "/" not in n and "." not in n and "$" not in n:
            return "", "", n                                   # a type port
        if "/" not in n and "$" not in n:                     # an instance with no pin (STA log row): a hard core
            return n, "HARDCORE", n + "/?"
        inst, _, pin = n.rpartition("/") if "/" in n else (n, "", "")
        core = bool(pin) and "$_" not in inst and not FLOP_PIN.search("/" + pin)
        return inst or n, ("HARDCORE" if core else "DFF_ASAP7_"), n
    si, sc, sp = side(start)
    ei, ec, ep = side(end)
    return dict(slack=float(slack), start=start, end=end, s_inst=si, s_cell=sc, s_pin=sp, e_inst=ei, e_cell=ec, e_pin=ep,
                sxy=(0.0, 0.0), exy=(0.0, 0.0), straight=0.0, flight=0.0, cell_ps=0.0, wire_ps=0.0, levels=0, bufs=0,
                half=False, unmeasured=True)


def cmd_harvest_rows(a):
    rows = list(csv.DictReader(open(a.harvest), delimiter="\t"))
    plans = {}
    for kv in [x for x in (a.plans or "").split(",") if "=" in x]:
        d, p = kv.split("=", 1)
        plans[d] = json.loads(Path(p).read_text())
    by = collections.defaultdict(list)
    for r in rows:
        if a.die and r.get("die") != a.die:
            continue
        kind = r.get("kind", "")
        try:
            sl = float(r.get("worst_ps") or r.get("n_or_slack_ps") or 0) if kind == "endpoint_group" else float(r.get("n_or_slack_ps") or 0)
        except ValueError:
            continue
        if kind == "endpoint_group":
            end = r.get("end", "")
            p = name_record(end.rsplit("/", 1)[0] + "/Q" if "$_" in end else end, end, sl)
            p["s_inst"], p["s_cell"], p["s_pin"] = "?", "DFF_ASAP7_", "?"     # launch unknown in a group row
        elif kind.startswith("worst_path"):
            p = name_record(r.get("bus_or_port_or_start", ""), r.get("end", ""), sl)
            try:
                p["levels"] = int(r.get("logic_cells") or 0)
                p["bufs"] = int(r.get("buf_wire_cells") or 0)
            except ValueError:
                pass
        else:
            continue
        by[(r["die"], r["type"])].append(p)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    alls = collections.defaultdict(lambda: dict(rows=[], rtl_requests=[]))
    for (die, tn), ps in sorted(by.items()):
        t = ((plans.get(die) or {}).get("partition_types") or {}).get(tn)
        rr, rtl = rows_from_paths(ps, die, tn, t, GUARD_PS)
        for r in rtl:
            r["ask"] = (f"unmeasured cause (STA log names only, {r['levels']} logic cells on the worst path): the read-only "
                        f"dump decides cone split (+1 RTL pipeline register) vs wire (+1 register mid-path); owner lane please "
                        f"name the register boundary in {r['module']}")
        for r in rr + rtl:
            r["length"] = "unmeasured (STA log names only; sized by the read-only dump of this kit)"
            if r["kind"] == "internal_stations_add":
                r["sites_um"] = None
                r["add_regs"] = r["cycles"] = 1
        alls[die]["rows"] += rr
        alls[die]["rtl_requests"] += rtl
    for die, rec in alls.items():
        rec.update(tool="setup_to_stage harvest-rows", rule="R11", die=die, source=str(a.harvest), guard_ps=GUARD_PS)
        (out / f"rows_{die}.json").write_text(json.dumps(rec, indent=1))
        print(f"SETUP-TO-STAGE {die}: {len(rec['rows'])} plan rows, {len(rec['rtl_requests'])} RTL requests -> {out / f'rows_{die}.json'}")
    return 0


def load_paths(path):
    J = json.loads(Path(path).read_text())
    return [r for r in (path_record(c) for c in J.get("checks") or []) if r]


# ---------------------------------------------------------------- dump command (kit sign-off session reuse)

def session_cut(text, slack_max=0.0, nmax=20000):
    """the sign-off session up to (not incl.) its first max-path report, + the json dump of every failing endpoint"""
    lines = text.splitlines()
    cut = next((i for i, ln in enumerate(lines) if ln.startswith("report_checks -path_delay max")), None)
    if cut is None:
        raise ValueError("session.tcl has no 'report_checks -path_delay max' line")
    tail = [
        "# SETUP-TO-STAGE (CBC rule 11): failing setup endpoints, one path each, json",
        f"report_checks -path_delay max -group_path_count {int(nmax)} -endpoint_path_count 1 -slack_max {slack_max:.1f} "
        "-sort_by_slack -format json > /out/sts_paths.json",
        'puts "STS_DONE"',
    ]
    return "\n".join(lines[:cut] + tail) + "\n"


def dump_cmd(cmd_sh, outdir, name="sts_dump"):
    """the kit's sign-off docker command with /out -> outdir, session -> /out/sts_session.tcl, its own container name"""
    s = cmd_sh.strip().splitlines()[-1]
    s = re.sub(r"-v\s+\S+:/out(\s)", f"-v {shlex.quote(str(outdir))}:/out\\1", s, count=1)
    s = re.sub(r"--name\s+\S+", f"--name {name}_$$", s, count=1)
    s = re.sub(r"/out/session\.tcl", "/out/sts_session.tcl", s)
    if "/out/sts_session.tcl" not in s:
        raise ValueError("sign-off command does not run /out/session.tcl")
    return s


def cmd_dump(a):
    k = Path(a.kit)
    so = k / "signoff" / "tt"
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "sts_session.tcl").write_text(session_cut((so / "session.tcl").read_text(), a.slack_max, a.nmax))
    sh = "#!/bin/bash\nset -eu\n" + dump_cmd((so / "cmd.sh").read_text(), out) + " > " + shlex.quote(str(out / "sts.log")) + " 2>&1\n"
    (out / "sts_dump.sh").write_text(sh)
    print(out / "sts_dump.sh")
    return 0


def cmd_harvest(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(a.harvest), delimiter="\t"))
    jobs = []
    for r in rows:
        if a.die and r.get("die") != a.die:
            continue
        try:
            tt = float(r.get("tt_setup_ps") or 0)
        except ValueError:
            continue
        cls = r.get("class", "")
        routed = r.get("6_final.odb") == "1" or r.get("5_2_route.odb") == "1"
        if cls.startswith("b") or (routed and tt < GUARD_PS and cls in ("", "b_setup")):
            jobs.append(r)
    with open(out / "jobs.tsv", "w") as fh:
        fh.write("die\ttype\thost\tkit\ttt_setup_ps\tdump_dir\tcommand\n")
        for r in jobs:
            dd = f"{a.lane_dir}/sts/{r['die']}/{r['type']}"
            cmd = (f"timeout 600 ssh -n -o ControlPath=none {r['host']} 'python3 -I {a.tool} dump-cmd {shlex.quote(r['kit'])} {dd}' && "
                   f"ot-run --mem 24 --threads 8 --hosts {r['host']} --dir {dd} -- bash {dd}/sts_dump.sh")
            fh.write("\t".join([r["die"], r["type"], r["host"], r["kit"], r["tt_setup_ps"], dd, cmd]) + "\n")
    print(f"SETUP-TO-STAGE harvest: {len(jobs)} setup-miss kits -> {out / 'jobs.tsv'}")
    return 0


def cmd_rows(a):
    paths = load_paths(a.paths)
    t = None
    if a.plan:
        raw = json.loads(Path(a.plan).read_text())
        t = (raw.get("partition_types") or {}).get(a.type)
    rows, rtl = rows_from_paths(paths, a.die, a.type, t, a.slack_max)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rec = dict(tool="setup_to_stage", rule="R11", die=a.die, type=a.type, kit=a.kit, plan=a.plan, paths_file=a.paths,
               failing_paths=sum(1 for p in paths if p["slack"] < a.slack_max), rows=rows, rtl_requests=rtl)
    (out / "rows.json").write_text(json.dumps(rec, indent=1))
    with open(out / "rtl_requests.tsv", "w") as fh:
        fh.write("die\ttype\tmodule\tpaths\tworst_slack_ps\tlevels\tcell_ps\twire_ps\tmax_straight_um\task\tworst_start\tworst_end\n")
        for r in rtl:
            fh.write("\t".join(str(x) for x in (a.die, a.type, r["module"], r["paths"], r["worst_slack_ps"], r["levels"], r["cell_ps"],
                                                r["wire_ps"], r["max_straight_um"], r["ask"], r["worst_start"], r["worst_end"])) + "\n")
    cyc = collections.Counter(r["kind"] for r in rows)
    L = [f"# SETUP-TO-STAGE {a.die} {a.type}", "", f"{rec['failing_paths']} failing paths -> {len(rows)} plan rows {dict(cyc)}, "
         f"{len(rtl)} RTL pipeline requests.  Hop cap {hop_cap(a.die)} um (half-cycle {hop_cap(a.die, True)} um).", "",
         "| kind | key | paths | worst ps | +cycles | note |", "|---|---|---|---|---|---|"]
    for r in rows:
        k = r.get("conn") or f"{r.get('inst')}.{r.get('port')}"
        L.append(f"| {r['kind']} | {k} | {r['paths']} | {r['worst_slack_ps']} | {r['cycles']} | {r['note']} |")
    for r in rtl:
        L.append(f"| rtl_pipeline | {r['module']} | {r['paths']} | {r['worst_slack_ps']} | +1 (RTL) | {r['ask']} |")
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print(f"SETUP-TO-STAGE {a.die} {a.type}: {rec['failing_paths']} paths -> {len(rows)} rows, {len(rtl)} RTL requests -> {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("harvest")
    h.add_argument("harvest")
    h.add_argument("--out", required=True)
    h.add_argument("--die", default="")
    h.add_argument("--lane-dir", default="/srv/opentallas-scratch2/claude/cbc-all-0200")
    h.add_argument("--tool", default="/srv/opentallas-scratch2/claude/rt/current/tools/die_plan/setup_to_stage.py")
    h.set_defaults(fn=cmd_harvest)
    hr = sub.add_parser("harvest-rows")
    hr.add_argument("harvest")
    hr.add_argument("--out", required=True)
    hr.add_argument("--die", default="")
    hr.add_argument("--plans", default="", help="die=PLAN.json,... (bus names, existing relay_depth rows)")
    hr.set_defaults(fn=cmd_harvest_rows)
    d = sub.add_parser("dump-cmd")
    d.add_argument("kit")
    d.add_argument("outdir")
    d.add_argument("--slack-max", type=float, default=0.0, help="ps; paths with slack below this")
    d.add_argument("--nmax", type=int, default=20000)
    d.set_defaults(fn=cmd_dump)
    r = sub.add_parser("rows")
    r.add_argument("--paths", required=True)
    r.add_argument("--type", required=True)
    r.add_argument("--die", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--plan", default="")
    r.add_argument("--kit", default="")
    r.add_argument("--slack-max", type=float, default=0.0)
    r.set_defaults(fn=cmd_rows)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
