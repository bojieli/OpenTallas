"""FABLE-FIX-QC-N N4.1 (D) 11-18: insertion target of a hard clock-landing (cland) WRITE clock.

A hard cland child (hard_landing.emit row form 'hard_child': u_cland_<bus>, clock pin fclk <- port fclk_in_<bus>) captures
its bus on the forwarded clock.  The kit SDC launches the bus at the forwarded-clock edge + the ring input max
(landing_contract.ring_input_sdc: ft-hop rings (1 - ft_hop_in_share) x T, others IO_BUDGET x T) and CTS leaves the one-sink
fclk net a bare wire, so the capture edge arrives ~2 ps after its ideal time.  Measured on QC sle_st_a_v1 (4_cts.odb,
falling-edge writers, T 833): input max 350 + 41 ps port -> pin data vs capture 416.5 + 2.2 - lib setup 82..93 ->
-50..-66 ps on 2,743 d pins of the three ft-hop rings.

Target (arrival of the capturing fclk edge at the cland pin, from the launching edge):

    target_ps = input max + DATA_ALLOWANCE_PS (45) + cland lib setup (d vs fclk, TT lib; 95 when the lib is not readable)

The capture edge is the fall (T/2) for a setup_falling master, the rise (T) for a setup_rising one, so the port -> pin
clock delay the kit must build is pin_delay_ps = target - edge.  A row is written only when that is > 0 (rise writers and
the IO-budget rings need nothing: kits without a row are byte-identical).  cland_fclk_target.tcl (POST_CTS, sourced from
the kit's cts_post.tcl before the PG connect) measures the delay on the propagated clock and adds clock buffers in front
of the pin until it is met: it only ever raises the delay, never lowers it.  The buffers are real cells on the propagated
forwarded clock, so the post-CTS gate, hold gate and sign-off STA (set_propagated_clock [all_clocks]) see them.
"""
import re
import shutil
from pathlib import Path

DATA_ALLOWANCE_PS = 45.0
DEFAULT_SETUP_PS = 95.0
TABLE = "cland_fclk_targets.txt"
HOOK = "cland_fclk_target.tcl"
PG_MARK = "# FLOW 2026-10-26 PG:"
HOOK_LINES = ("# FABLE-FIX-QC-N N4.1 (D) 11-18: hard cland write clocks padded to their insertion target (cland_fclk_target.tcl,\n"
              "# table cland_fclk_targets.txt generated per kit by gen_phys; raise only), before the PG connect below.\n"
              "uplevel #0 [list source [file join $cp_dir cland_fclk_target.tcl]]\n")
_UNIT = {"ps": 1.0, "ns": 1000.0}


def lib_setup(lib, data_port="d", clock_pin="fclk"):
    """(largest setup of <data_port>[*] against <clock_pin> in ps, 'fall' | 'rise') from a liberty file, or (None, None)
    when the file is missing / has no such arc.  Scalar and table constraints both count (max over all values)."""
    try:
        text = Path(lib).read_text()
    except (OSError, TypeError, UnicodeDecodeError):
        return None, None
    m = re.search(r'time_unit\s*:\s*"?\s*([\d.]+)\s*(ps|ns)', text)
    scale = float(m[1]) * _UNIT[m[2]] if m else 1.0
    pin = rel = kind = None
    best = {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("pin"):
            m = re.match(r'pin\s*\(\s*"?([^")\s]+)"?\s*\)', s)
            if m:
                pin, rel, kind = m[1].split("[")[0], None, None
                continue
        if s.startswith("timing"):
            if re.match(r"timing\s*\(", s):
                rel = kind = None
                continue
            m = re.match(r"timing_type\s*:\s*(\w+)", s)
            if m:
                kind = m[1]
                continue
        m = re.match(r'related_pin\s*:\s*"?([^";\s]+)', s)
        if m:
            rel = m[1]
            continue
        if pin == data_port and rel == clock_pin and kind in ("setup_falling", "setup_rising") and "values" in s:
            vals = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s.split("values", 1)[1])]
            if vals:
                e = "fall" if kind == "setup_falling" else "rise"
                best[e] = max(best.get(e, float("-inf")), max(vals) * scale)
    if not best:
        return None, None
    edge = max(best, key=best.get)
    return best[edge], edge


def input_max(sdc, unit_ps=1.0):
    """{(forwarded clock, port): ring input max ps} from landing_contract.ring_input_sdc text"""
    out = {}
    for m in re.finditer(r"^set_input_delay -max (-?[\d.]+) -clock (\S+) \[get_ports \{([^}\[]+)(?:\[\*\])?\}\]", sdc, re.M):
        out[(m[2], m[3])] = float(m[1]) * unit_ps
    return out


def target(in_max_ps, setup_ps, edge, period_ps):
    """(target_ps, pin_delay_ps): arrival of the capturing edge at the cland pin and the port -> pin delay it needs"""
    tgt = in_max_ps + DATA_ALLOWANCE_PS + setup_ps
    return tgt, tgt - (period_ps / 2.0 if edge == "fall" else period_ps)


def hard_rows(land_slots, hard_cores):
    """[(bus, row, plan hard core)] of the hard cland children that capture a bus (not their ring_start copies)"""
    by = {c.get("physical_inst", c["inst"]): c for c in hard_cores or []}
    out = []
    for bus, v in sorted(((land_slots or {}).get("buses") or {}).items()):
        if isinstance(v, dict) and v.get("form") == "hard_child" and v.get("port") == "d" and \
                v.get("clock_port") == "fclk_in_" + bus:
            out.append((bus, v, by.get(v["instance"], {})))
    return out


def rows(land_slots, hard_cores, sdc, period_ps, macros_dir, unit_ps=1.0):
    """one dict per hard cland child: inst, pin, port, target_ps, pin_delay_ps, in_max_ps, setup_ps, edge, basis"""
    imax = input_max(sdc, unit_ps)
    out = []
    for bus, v, c in hard_rows(land_slots, hard_cores):
        ck = v["clock_port"]
        if (ck, bus) not in imax:
            continue
        setup, edge = (lib_setup(Path(macros_dir) / Path(c["lib"]).name, v["port"], v["clock_pin"])
                       if c.get("lib") else (None, None))
        basis = "lib"
        if setup is None:
            p = (c.get("param_wrap") or {}).get("params") or {}
            setup, basis = DEFAULT_SETUP_PS, "default"
            edge = "fall" if p.get("WFALL") == 1 or p.get("WNEG") == 1 else "rise"
        tgt, need = target(imax[(ck, bus)], setup, edge, period_ps)
        out.append(dict(inst=v["instance"], pin=v["clock_pin"], port=ck, target_ps=round(tgt, 1),
                        pin_delay_ps=round(need, 1), in_max_ps=round(imax[(ck, bus)], 1), setup_ps=round(setup, 1),
                        edge=edge, basis=basis))
    return out


def table(rs):
    """kit cland_fclk_targets.txt: `inst pin port pin_delay_ps target_ps edge` for the rows that need a delay"""
    body = "".join(f"{r['inst']} {r['pin']} {r['port']} {r['pin_delay_ps']:.1f} {r['target_ps']:.1f} {r['edge']}\n"
                   for r in rs if r["pin_delay_ps"] > 0)
    if not body:
        return ""
    return ("# inst pin port pin_delay_ps target_ps edge   (GENERATED by gen_phys / cland_fclk_target.py; POST_CTS raises the "
            "port -> pin clock delay to pin_delay_ps, never lowers it)\n" + body)


def wire(cts_post):
    """the kit's cts_post.tcl text with the hook sourced before the PG connect (idempotent)"""
    if HOOK in cts_post:
        return cts_post
    if cts_post.count(PG_MARK) != 1:
        raise ValueError("cland_fclk_target: cts_post.tcl has no single PG connect marker to source the hook before")
    return cts_post.replace(PG_MARK, HOOK_LINES + PG_MARK)


def emit(P, tn, land_slots, kd, unit_ps=1.0, log=print):
    """gen_phys hook: print OT_CLAND_FCLK_TARGET per hard cland child; write the table + hook when a delay is needed"""
    t = P.types[tn]
    if not hard_rows(land_slots, t.get("hard_cores")):
        return []
    import landing_contract as LC
    rs = rows(land_slots, t.get("hard_cores"), LC.ring_input_sdc(P, tn), float(P.die["period_ps"]),
              Path(kd) / "macros", unit_ps)
    for r in rs:
        log(f"OT_CLAND_FCLK_TARGET {r['inst']} {r['target_ps']:.1f} pin_delay={max(0.0, r['pin_delay_ps']):.1f} "
            f"in_max={r['in_max_ps']:.1f} setup={r['setup_ps']:.1f}({r['basis']}) edge={r['edge']} type={tn}")
    text = table(rs)
    if text:
        kd = Path(kd)
        (kd / TABLE).write_text(text)
        shutil.copyfile(Path(__file__).with_name(HOOK), kd / HOOK)
        hook = kd / "cts_post.tcl"
        hook.write_text(wire(hook.read_text()))
    return rs
