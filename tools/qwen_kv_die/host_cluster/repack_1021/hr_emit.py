"""KV-HROOT10: emit the qkd_hr_cluster repack kit spec + DIAGNOSTIC stand-in views (never bindable) for hr_parent.py."""
import collections
import json
import os
import re
from pathlib import Path

FLOP = {"tt": (40.0, 15.0, 55.0), "ff": (30.0, 12.0, 40.0), "ss": (55.0, 20.0, 75.0)}   # setup, hold, clk->q (ps)
INS = {"tt": 250.0, "ff": 200.0, "ss": 330.0}     # ASSUMED stand-in clock insertion (core children 188-277 TT measured)
TRACK = {"M4": (0.012, 0.048), "M5": (0.012, 0.048)}
CLOCKS = ('ck_core', 'ck_host', 'ck_ingest', 'ck_phy_fam', 'ck_phy')


def snapt(v, lay):
    off, pit = TRACK[lay]
    return round(off + round((v - off) / pit) * pit, 3)


def standin_lef(name, W, H, pins, dirs):
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  FOREIGN {name} 0 0 ;", f"  SIZE {W} BY {H} ;", "  SYMMETRY X Y ;"]
    used = set()
    for nm, (x, y) in sorted(pins.items()):
        base = nm.split('[')[0]
        face = 'W' if x < 0.01 else 'E' if x > W - 0.01 else 'S' if y < 0.01 else 'N'
        lay = 'M4' if face in 'EW' else 'M5'
        if face in 'EW':
            p = snapt(y, lay)
            while (face, p) in used:
                p = round(p + 0.048, 3)
            used.add((face, p))
            x0, x1 = (0.0, 0.192) if face == 'W' else (W - 0.192, W)
            r = (x0, p - 0.012, x1, p + 0.012)
        else:
            p = snapt(x, lay)
            # M5 pins must not sit on the PG stripe x positions (stripes at 2.46 + k*5.4 / 2.652 + k*5.4, 0.12 wide)
            def hits(q):
                for off in (2.46, 2.652):
                    k = round((q - off) / 5.4)
                    if abs(q - (off + k * 5.4 + 0.06)) < 0.2:
                        return True
                return False
            while (face, p) in used or hits(p):
                p = round(p + 0.048, 3)
            used.add((face, p))
            y0, y1 = (0.0, 0.192) if face == 'S' else (H - 0.192, H)
            r = (p - 0.012, y0, p + 0.012, y1)
        d = "OUTPUT" if dirs.get(base) == 'output' else "INPUT"
        use = "CLOCK" if base in CLOCKS else "SIGNAL"
        L += [f"  PIN {nm}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT", f"      LAYER {lay} ;",
              "        RECT %.3f %.3f %.3f %.3f ;" % r, "    END", f"  END {nm}"]
    stripes = []
    for net, use, off in (("VDD", "POWER", 2.46), ("VSS", "GROUND", 2.652)):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M5 ;"]
        x = off
        while x + 0.12 < W - 2.16:
            L.append("        RECT %.3f 2.151 %.3f %.3f ;" % (x, x + 0.12, H - 2.151))
            stripes.append(x)
            x += 5.4
        L += ["    END", f"  END {net}"]
    # OBS: M1-M4 inset 1.0 um from the faces with 10.8-um deep pin-access windows left open along every pin face
    E, D = 1.0, 10.8
    L += ["  OBS"]
    for k in range(1, 5):
        L += [f"    LAYER M{k} ;", "      RECT %.3f %.3f %.3f %.3f ;" % (D, D, W - D, H - D)]
    L += ["    LAYER M5 ;"]
    xs = sorted(stripes)
    edges = [D] + [v for x in xs if D < x < W - D for v in (x - 0.1, x + 0.22)] + [W - D]
    for a, b in zip(edges[::2], edges[1::2]):
        if b - a > 0.1:
            L.append("      RECT %.3f %.3f %.3f %.3f ;" % (a, D, b, H - D))
    L += ["  END", f"END {name}", "END LIBRARY"]
    return "\n".join(L) + "\n"


def standin_lib(name, W, H, pins, dirs, related, corner):
    su, ho, cq = FLOP[corner]
    r = INS[corner]
    buses, scal = collections.defaultdict(list), []
    for nm in pins:
        m = re.fullmatch(r"(\w+)\[(\d+)\]", nm)
        if m:
            buses[m.group(1)].append(int(m.group(2)))
        else:
            scal.append(nm)

    def body(p, base):
        ck = related.get(base, 'ck_core')
        if base in CLOCKS:
            arcs = []
            for tt, v in (("min_clock_tree_path", r - 10), ("max_clock_tree_path", r + 10)):
                arcs += [f"      timing() {{ timing_type : {tt}; timing_sense : positive_unate;",
                         f'        cell_rise(scalar) {{ values("{v:.1f}"); }} cell_fall(scalar) {{ values("{v:.1f}"); }} }}']
            return [f'    pin("{p}") {{', "      direction : input;", "      clock : true;", "      capacitance : 2.0;"] + arcs + ["    }"]
        if dirs.get(base) == 'output':
            t = [f'      timing() {{ related_pin : "{ck}"; timing_type : rising_edge;',
                 f'        cell_rise(scalar) {{ values("{r + cq:.1f}"); }} cell_fall(scalar) {{ values("{r + cq:.1f}"); }}',
                 '        rise_transition(scalar) { values("25.0"); } fall_transition(scalar) { values("25.0"); } }']
            return [f'    pin("{p}") {{', "      direction : output;"] + t + ["    }"]
        t = [f'      timing() {{ related_pin : "{ck}"; timing_type : setup_rising;',
             f'        rise_constraint(scalar) {{ values("{su - r:.1f}"); }} fall_constraint(scalar) {{ values("{su - r:.1f}"); }} }}',
             f'      timing() {{ related_pin : "{ck}"; timing_type : hold_rising;',
             f'        rise_constraint(scalar) {{ values("{ho + r:.1f}"); }} fall_constraint(scalar) {{ values("{ho + r:.1f}"); }} }}']
        return [f'    pin("{p}") {{', "      direction : input;", "      capacitance : 1.0;"] + t + ["    }"]
    L = [f"library ({name}_{corner}) {{", "  delay_model : table_lookup;", "  capacitive_load_unit (1,fF);",
         '  time_unit : "1ps";', '  voltage_unit : "1v";', '  current_unit : "1mA";', '  pulling_resistance_unit : "1kohm";',
         '  leakage_power_unit : 1pW;', "  input_threshold_pct_rise : 50;", "  input_threshold_pct_fall : 50;",
         "  output_threshold_pct_rise : 50;", "  output_threshold_pct_fall : 50;", "  slew_lower_threshold_pct_rise : 10;",
         "  slew_lower_threshold_pct_fall : 10;", "  slew_upper_threshold_pct_rise : 90;", "  slew_upper_threshold_pct_fall : 90;",
         "  nom_process : 1.0;", "  nom_temperature : 25.0;", "  nom_voltage : 0.70;"]
    for b, idx in sorted(buses.items()):
        L += [f'  type ("{b}") {{ base_type : array; data_type : bit; bit_width : {max(idx) + 1}; bit_from : {max(idx)}; bit_to : 0; }}']
    L += [f'  cell ("{name}") {{', f"    area : {W * H:.1f};", "    is_macro_cell : true;"]
    for p in sorted(scal):
        L += body(p, p)
    for b, idx in sorted(buses.items()):
        L += [f'    bus("{b}") {{', f"      bus_type : {b};", f"      direction : {'output' if dirs.get(b) == 'output' else 'input'};"]
        for i in sorted(idx, reverse=True):
            L += ["  " + x for x in body(f"{b}[{i}]", b)]
        L += ["    }"]
    L += ["  }", "}"]
    return "\n".join(L) + "\n"


def emit(V, blocks, nets, rows, over, portface, portpos, out):
    import hr_parent as HP
    name = V['name']
    kit = f'physical/ref_tile/{name}'
    sdir = out / kit / 'standin'
    PW, PH = V['outline']
    children = []
    for inst, b in sorted(blocks.items(), key=lambda kv: kv[0]):
        if b['standin']:
            cell = b['cell']
            d = sdir / cell
            d.mkdir(parents=True, exist_ok=True)
            dirs = HP.rtl_dirs(b['rtl'])
            # related clock per pin: ingest_qm host-facing pins (to cdc_host) on ck_host, the rest ck_core
            related = {}
            if inst == 'u_ingest_qm':
                for p, bits in HP.NB['inst'][inst].items():
                    if any(oi == 'u_cdc_host' for n in bits for (oi, _, _) in nets[n]):
                        related[p] = 'ck_host'
            (d / f'{cell}.lef').write_text(standin_lef(cell, b['w'], b['h'], b['pins'], dirs))
            for c in ('tt', 'ff', 'ss'):
                (d / f'{cell}_{c}.lib').write_text(standin_lib(cell, b['w'], b['h'], b['pins'], dirs, related, c))
            ins = {"schema": "opentallas.closure_loop.ck_insertion.v1", "standin": True, "assumed_ps": INS}
            for c in ('tt', 'ff', 'ss'):
                ins[c] = {"boundary": {"n": len(b['pins']), "mean": INS[c], "min": INS[c] - 10, "max": INS[c] + 10}, "errors": []}
            ins['clock_measurements'] = {c: {k: ins[k] for k in ('tt', 'ff', 'ss')} for c in b['clocks']}
            if len(b['clocks']) == 1:
                ins['clock'] = ins['lib_clock_pin'] = b['clocks'][0]
            (d / 'insertion.json').write_text(json.dumps(ins, indent=1) + "\n")
            (d / 'STANDIN_NOT_A_VIEW').write_text(f"KV-HROOT10 diagnostic stand-in for {cell} in the {name} parent gate "
                                                  "(parent-assigned pins = the pin plan the leaf kit must adopt); never bind\n")
            (d / 'PROVISIONAL_NOT_A_VIEW').write_text("standin\n")
            (d / 'pins.json').write_text(json.dumps({k: [round(v[0], 3), round(v[1], 3)] for k, v in sorted(b['pins'].items())}) + "\n")
            view = f'{kit}/standin/{cell}'
            state = 'STAND-IN (no closed view)'
        else:
            view = b['view']
            state = 'CLOSED view (origin/main)'
        children.append({"view": view, "count": 1, "inst": inst, "at": [b['x'], b['y']], "orient": b['o'],
                         "at_exact": True, "state": state})
    # parent pins: each top port on the face its consumer chose, range = its bits' projections widened to <= 4 pins/um
    byport = collections.defaultdict(list)
    for nm, (f, pos) in portpos.items():
        byport[nm.split('[')[0]].append((f, pos))
    pins, ranges = collections.defaultdict(list), {}
    for p, lst in sorted(byport.items()):
        f = collections.Counter(x[0] for x in lst).most_common(1)[0][0]
        ps = [x[1] for x in lst if x[0] == f]
        L = PH if f in 'EW' else PW
        lo, hi = min(ps), max(ps)
        need = len(lst) / 4.0
        if hi - lo < need:
            c = (lo + hi) / 2
            lo, hi = c - need / 2, c + need / 2
        lo, hi = max(lo, 21.6), min(hi, L - 21.6)
        pins[f].append(p)
        ranges[p] = [round(lo, 2), round(hi, 2)]
    # clock entries: per clock, on the face nearest the centroid of the children it feeds
    for ck in CLOCKS:
        users = [inst for inst, ports in HP.NB['inst'].items() if ck in ports]
        if not users:
            continue
        cx = sum(blocks[u]['x'] + blocks[u]['w'] / 2 for u in users) / len(users)
        cy = sum(blocks[u]['y'] + blocks[u]['h'] / 2 for u in users) / len(users)
        f = HP.face_of(cx, cy, PW, PH)
        pos = cy if f in 'EW' else cx
        pins[f].append(ck)
        ranges[ck] = [round(pos - 4, 2), round(pos + 4, 2)]
    dens = {f: round(sum(len(HP.NB['ports'][p]) for p in ps) / (PH if f in 'EW' else PW), 2) for f, ps in pins.items()}
    spec = {
        "_status": "KV-HROOT10 10-20: CRITICAL parent qkd_host_root (qkd_hr_cluster) REPACK, DIAGNOSTIC pathfinding gate on "
                   "closed + stand-in leaf views (peer 518.4 sq slot, prompt 475.2x432, ingest_qm 345.6 sq); NO REVIEW.json / "
                   "NO submit (critical prefix) -> lanes/COORD-REVIEW-QUEUE.md",
        "name": name, "top": "qkd_hr_cluster", "kind": "cluster", "diagnostic": True, "recipe": 4,
        "sources": ["rtl/qwen_sys/host_cluster_20261017/qkd_hr_cluster.v"],
        "clock": "entries", "clock_port": "ck_core",
        "clock_ports": ["ck_core", "ck_host", "ck_ingest", "ck_phy_fam"] + [f"ck_phy[{i}]" for i in range(8)],
        "clock_note": "wires-only parent: every glue cell lives in a child; one entry per clock FAMILY (core / host / ingest / "
                      "phy, 8 phase-matched ck_phy lanes); every cross-family net goes through a hard CDC leaf (cdc_pc, "
                      "cdc_host, ingest_qm); 0 landings (families asynchronous, region_plan.json)",
        "reset_ports": [],
        "outline": {"w": PW, "h": PH, "exact": True},
        "child_lattice_um": 43.2,
        "children": children,
        "macros": [], "inter": [],
        "pins": dict(pins), "pin_ranges": ranges,
        "pin_density_per_um": dens,
        "pin_regs": {"enable": False, "reason": "wires-only parent: every child registers its own pins; owner 10-20 09:05 "
                                                "pin regs only at region crossings (the CDC leaves) and wires > 405 um"},
        "route": {"pd": 0.5, "threads": 32, "peak_ram_gb": 96, "macro_halo_um": 5.4, "hold_margin_ns": 0.03,
                  "io_hold_margin_ns": 0.03},
        "region_plan": "results/arch/qwen_split_1014/host_root_cluster/landed/region_plan.json",
        "plan": {"tool": "tools/qwen_kv_die/host_cluster/repack_1020 (hr_anneal + hr_refine + hr_parent)",
                 "lanes_over_405_bits": over,
                 "longest": [{"pair": list(k), "max_um": round(mx, 1), "mean_um": round(m, 1), "bits": n}
                             for mx, m, n, k in rows if k[0] != 'BROADCAST'][:12]},
        "job": {"owner": "Claude:KV-HROOT10", "branch": "claude/kv-hroot10-1020", "tag": name.split('_')[-1],
                "purpose": "KV host root parent repack (qkd_host_root CRITICAL): coordinator review before any route",
                "submit": False},
    }
    spec.update(V.get('spec_extra', {}))
    sp = out / 'tools/ref_tile/specs_qhost_cluster' / f'{name}.json'
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(spec, indent=1) + "\n")
    print('wrote', sp, 'and stand-ins under', sdir, 'pin density', dens)
