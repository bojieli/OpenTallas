#!/usr/bin/env python3
"""S81-DV die STA PILOT (S81-DIE4 10-17): learn the die timing classes early on a routed (GRT) DV die case.

NOT A DIE RESULT: the case's DV blocks are stand-in abstracts (dv_diecase.stand_in_lib: flop-first, C = 25 ps launch,
U = 25 ps setup), the 276-b stations are the CLOSED relay views, other lanes DFF stand-in stations with BUF clock
forwards.  Die hold budget (FLOW-HOLD, owner 10-16): C = 25 ps placeholder launch (already in the stand-in libs),
hold uncertainty 25 once per link, no planning pads; setup uncertainty 60.  Clocks are PROPAGATED: one root clk, every
hop's clock is the forwarded clock of the previous hop (neighbour-relative clocking), so a hop's slack carries the
real fclk skew of its own lane only.

Relay ETMs export ck_o as a self-related clock output (rising/falling_edge arcs related to ck_o), which no STA can
propagate a clock through; the pilot libs turn those two groups into ONE combinational positive-unate ck -> ck_o arc
(cell_rise from the rising_edge group, cell_fall from the falling_edge group: the forwarded edge delay).  Labelled.

  dv_sta_pilot.py --case-remote DIR --out LOCALDIR [--relay-ref REF] [--corners tt ff]
writes LOCALDIR/{libs/rly_<d>_<corner>.lib, sta_<corner>.tcl, run.sh, classify.py}; rsync it next to the case and run
run.sh (docker ORFS); classify.py turns the end-format reports into per-(link class, hop kind) WNS / TNS / counts.

S81-LAND2 options: --relay-widths (closed dsfd_dvrly_<W>_<dir> views of a dv_diecase --relay-widths case);
--hop-fix half|outhold (the relay->relay hold fix prototypes of dv_land_pilot variant, applied to every relay lib);
--standin-views DIR (local copy of the case's views/: the stand-in block libs are re-emitted into libs/ with the hop-0
SOURCE CONTRACT: lane data outputs launch --src-data-ps after clk, the forwarded cko --src-cko-ps after clk, and under
half-cycle hops cko is the INVERTED clock (the hop-0 forward cell inverts like every relay forward)).
"""
import argparse, re, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
GITDIR = __import__('os').environ.get('OT_GIT_DIR', str(ROOT))   # S81-BIND3: sources from a git archive, refs from the repo
RLY = ('EW', 'WE', 'NS', 'SN')
PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
STD = dict(tt=('SEQ_RVT_TT_nldm_220123.lib', 'INVBUF_RVT_TT_nldm_220122.lib.gz', 'SIMPLE_RVT_TT_nldm_211120.lib.gz'),
           ff=('SEQ_RVT_FF_nldm_220123.lib', 'INVBUF_RVT_FF_nldm_220122.lib.gz', 'SIMPLE_RVT_FF_nldm_211120.lib.gz'))


def _group(txt, start):
    """-> end index of the brace group whose '{' is the first at/after start"""
    i = txt.index('{', start); n = 0
    for j in range(i, len(txt)):
        n += {'{': 1, '}': -1}.get(txt[j], 0)
        if n == 0:
            return j + 1
    raise ValueError('unbalanced')


def patch_ck_o(lib):
    m = re.search(r'pin\("ck_o"\)\s*\{', lib)
    if not m:
        raise ValueError('no ck_o pin')
    pend = _group(lib, m.start())
    body = lib[m.start():pend]
    groups = {}
    for t in re.finditer(r'timing\(\)\s*\{', body):
        g = body[t.start():_group(body, t.start())]
        tt = re.search(r'timing_type\s*:\s*(\w+)', g).group(1)
        groups[tt] = g
    if set(groups) != {'rising_edge', 'falling_edge'} or 'related_pin : "ck_o"' not in groups['rising_edge']:
        raise ValueError(f'unexpected ck_o arcs {sorted(groups)}')

    def table(g, name):
        s = re.search(name + r'\(', g).start()
        return g[s:_group(g, s)]
    arc = ('timing() {\n        related_pin : "ck";\n        timing_sense : positive_unate;\n        timing_type : combinational;\n'
           '        /* S81-DIE4 STA pilot: ETM self-related ck_o edges -> one ck -> ck_o forwarded-clock arc */\n        '
           + '\n        '.join([table(groups['rising_edge'], 'cell_rise'), table(groups['rising_edge'], 'rise_transition'),
                               table(groups['falling_edge'], 'cell_fall'), table(groups['falling_edge'], 'fall_transition')])
           + '\n      }')
    nb = body
    for g in groups.values():
        nb = nb.replace(g, '', 1)
    nb = nb.rstrip()[:-1].rstrip() + '\n      ' + arc + '\n    }'
    return lib[:m.start()] + nb + lib[pend:]


STA = r'''# S81-DV die STA PILOT {corner} (tools/s81_dv/dv_sta_pilot.py) -- NOT_A_DIE_RESULT: stand-in DV blocks, die hold budget
set C /case
foreach f {{{std}}} {{ read_liberty {plat}/lib/NLDM/asap7sc7p5t_$f }}
foreach f [glob $C/views/dv_*.lib] {{ read_liberty $f }}
foreach f [glob /pilot/libs/rly_*_{corner}.lib] {{ read_liberty $f }}
read_db $C/out/grt.odb
source {plat}/setRC.tcl
set_wire_rc -signal -layer M6
create_clock -name clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst]
if {{[catch {{estimate_parasitics -global_routing}} e]}} {{ puts "OT_STA_PARA placement ($e)"; estimate_parasitics -placement }} else {{ puts "OT_STA_PARA global_routing" }}
puts "OT_STA_WNS_SETUP"; report_worst_slack -max -digits 1
puts "OT_STA_WNS_HOLD"; report_worst_slack -min -digits 1
puts "OT_STA_TNS_SETUP"; report_tns -digits 1
foreach {{d tag}} {{max setup min hold}} {{
  if {{[catch {{report_checks -path_delay $d -group_path_count 200000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /pilot/out/{corner}_$tag.end.rpt}}]}} {{
    report_checks -path_delay $d -group_count 200000 -endpoint_count 1 -unique_paths_to_endpoint -format end > /pilot/out/{corner}_$tag.end.rpt
  }}
  report_checks -path_delay $d -group_path_count 12 -fields {{slew cap fanout}} -digits 1 > /pilot/out/{corner}_$tag.paths.rpt
}}
report_check_types -max_slew -max_capacitance -violators > /pilot/out/{corner}_drv.rpt
puts OT_STA_DONE
'''

STATION_RPT = r'''set fo [open /pilot/out/{corner}_station.rpt w]
foreach inst [get_cells st_*] {{
  set ps [get_pins [get_full_name $inst]/i*]
  foreach d {{max min}} {{
    set pe [lindex [find_timing_paths -path_delay $d -to $ps -group_path_count 1] 0]
    set sl none; if {{$pe ne ""}} {{ catch {{ set sl [sta::format_time [$pe slack] 1] }} }}
    puts $fo "[get_full_name $inst] $d $sl"
  }}
}}
close $fo
'''

CLASSIFY = r'''#!/usr/bin/env python3
# per-(link class, hop kind) slack classes from the pilot end-format reports (S81-DIE4 STA pilot)
import json, re, sys, collections
case = json.load(open(sys.argv[1])); out = sys.argv[2]
cls = {}
for c in (case['chains'] if isinstance(case['chains'], list) else []):
    cls[c['link'].replace('-', '_')] = c['cls']
def klass(ep):
    inst = ep.split('/')[0]
    m = re.match(r'(st|f_r)_(.+)_(\d+)(?:_\d+)?$', inst)
    if m:
        ln = m.group(2)
        return (cls.get(ln, ln.split('_')[0]), 'relay276' if m.group(1) == 'st' else 'dff_station')
    if inst.startswith('u_'):
        return ('block_in', inst[2:].split('_')[0])
    return ('other', inst.split('_')[0])
res = {}
for corner in sys.argv[3:]:
    for tag in ('setup', 'hold'):
        try: txt = open(f'{out}/{corner}_{tag}.end.rpt').read()
        except OSError: continue
        agg = collections.defaultdict(lambda: dict(n=0, neg=0, wns=1e9, tns=0.0, worst=None))
        for line in txt.splitlines():
            f = line.split()
            if len(f) < 4 or '/' not in f[0]: continue
            try: sl = float(f[-2] if f[-1] in ('(VIOLATED)', '(MET)') else f[-1])
            except ValueError: continue
            k = '|'.join(klass(f[0])); a = agg[k]; a['n'] += 1
            if sl < a['wns']: a['wns'] = sl; a['worst'] = f[0]
            if sl < 0: a['neg'] += 1; a['tns'] += sl
        res[f'{corner}_{tag}'] = dict(sorted(agg.items(), key=lambda kv: kv[1]['wns']))
json.dump(res, open(f'{out}/classes.json', 'w'), indent=1)
for k, v in res.items():
    print(k); [print(f'  {c:40s} n={a["n"]:7d} neg={a["neg"]:7d} wns={a["wns"]:9.1f} tns={a["tns"]:12.1f} {a["worst"]}') for c, a in list(v.items())[:15]]
'''


def standin_contract(lib, data_ps, cko_ps, invert):
    """hop-0 source contract on a dv_diecase stand-in lib: data launch data_ps, cko cko_ps (inverted under half-cycle)"""
    out = []
    for blk in re.split(r'(?=\n    (?:bus|pin) \()', lib):
        if blk.startswith('\n    pin (cko_'):
            blk = re.sub(r'values \("[\d.]+"\) ; \} cell_fall \(scalar\) \{ values \("[\d.]+"\)',
                         f'values ("{cko_ps:g}") ; }} cell_fall (scalar) {{ values ("{cko_ps:g}")', blk)
            if invert:
                blk = blk.replace('timing_sense : positive_unate', 'timing_sense : negative_unate')
        elif blk.startswith('\n    bus (') and 'direction : output' in blk:
            blk = re.sub(r'(rising_edge ; cell_rise \(scalar\) \{ values \(")[\d.]+("\) ; \} cell_fall \(scalar\) \{ values \(")[\d.]+',
                         lambda g: f'{g.group(1)}{data_ps:g}{g.group(2)}{data_ps:g}', blk)
        out.append(blk)
    return ''.join(out).replace('/* STAND-IN:', f'/* S81-LAND2 hop-0 source contract: data {data_ps:g} / cko {cko_ps:g}{" inverted" if invert else ""} | STAND-IN:', 1)


def _timings(seg):
    """-> [(timing_type, body)] of the timing() groups of one liberty pin group"""
    out = []
    for t in re.finditer(r'timing\(\)\s*\{', seg):
        body = seg[t.start():_group(seg, t.start())]
        tt = re.search(r'timing_type\s*:\s*(\w+)', body)
        out.append((tt.group(1) if tt else 'combinational', body))
    return out


def _first(body, name, allv=False):
    m = re.search(name + r'\(\w*\)\s*\{(.*?)\}', body, re.S)
    if not m:
        return []
    v = re.search(r'values\(([^)]*)\)', m.group(1))
    nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e-?\d+)?', v.group(1))] if v else []
    return nums if allv else nums[:1]


def leaf_pin_arcs(lib, cell, spec_path, corner):
    """S81-BIND3: replace the stand-in scalar arcs of the pins listed in spec for this stand-in cell by the worst arc of
    the CLOSED leaf view pin that owns it: inputs setup = max setup_rising, hold = max hold_rising (whole tables);
    outputs clk -> q = max (tt: setup side) / min (ff: hold side) of the lightest-load entry.  The cluster above the
    leaf is not hardened: its glue and clock insertion are 0 here (labelled in the lib)."""
    import json
    spec = [s for s in json.load(open(spec_path)) if f"dv_{s['inst']}" == cell]
    for s in spec:
        p = f"{s['view_dir']}/{s['cell']}_{corner}.lib"
        leaf = subprocess.run(['git', '-C', GITDIR, 'show', f"{s['view_ref']}:{p}"], capture_output=True, text=True, check=True).stdout
        segs = [leaf[m.start():_group(leaf, m.start())] for m in re.finditer(r'pin\("' + re.escape(s['leaf_pin']) + r'\[\d+\]"\)\s*\{', leaf)]
        if not segs:
            raise SystemExit(f"leaf pin {s['leaf_pin']} not in {p}")
        m = re.search(r'\n    bus \(' + re.escape(s['pin']) + r'\) \{.*?\n    \}', lib, re.S)
        blk = m.group(0)
        ts = [t for g in segs for t in _timings(g)]
        if 'direction : input' in blk:
            su = max(x for tt, b in ts if tt == 'setup_rising' for k in ('rise_constraint', 'fall_constraint') for x in _first(b, k, True))
            ho = max(x for tt, b in ts if tt == 'hold_rising' for k in ('rise_constraint', 'fall_constraint') for x in _first(b, k, True))
            nb = re.sub(r'(setup_rising ; rise_constraint \(scalar\) \{ values \(")[^"]*("\) ; \} fall_constraint \(scalar\) \{ values \(")[^"]*',
                        lambda g: f'{g.group(1)}{su:.1f}{g.group(2)}{su:.1f}', blk)
            nb = re.sub(r'(hold_rising ; rise_constraint \(scalar\) \{ values \(")[^"]*("\) ; \} fall_constraint \(scalar\) \{ values \(")[^"]*',
                        lambda g: f'{g.group(1)}{ho:.1f}{g.group(2)}{ho:.1f}', nb)
            note = f'setup {su:.1f} / hold {ho:.1f}'
        else:
            col = [x for tt, b in ts if tt == 'rising_edge' for k in ('cell_rise', 'cell_fall') for x in _first(b, k)]
            dq = max(col) if corner == 'tt' else min(col)
            nb = re.sub(r'(rising_edge ; cell_rise \(scalar\) \{ values \(")[^"]*("\) ; \} cell_fall \(scalar\) \{ values \(")[^"]*',
                        lambda g: f'{g.group(1)}{dq:.1f}{g.group(2)}{dq:.1f}', blk)
            note = f'clk->q {dq:.1f}'
        tag = f"/* S81-BIND3 CLOSED leaf {s['cell']}.{s['leaf_pin']} @{s['view_ref']} {corner}: {note}; cluster glue / insertion 0 */"
        lib = lib.replace(blk, nb.replace(f"bus ({s['pin']}) {{", f"bus ({s['pin']}) {{ {tag}", 1))
        print(f"leaf-pin {cell}.{s['pin']} {corner}: {note}")
    return lib


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--case-remote', required=True, help='routed DV die case dir on the run host (has out/grt.odb, views/)')
    ap.add_argument('--relay-widths', type=int, nargs='+', default=[276])
    ap.add_argument('--hop-fix', choices=('none', 'half', 'outhold'), default='none')
    ap.add_argument('--outhold-ps', type=float, default=200.0)
    ap.add_argument('--standin-views', type=Path, default=None)
    ap.add_argument('--src-data-ps', type=float, default=25.0)
    ap.add_argument('--src-cko-ps', type=float, default=25.0)
    ap.add_argument('--station-report', action='store_true',
                    help='per relay station: worst setup / hold to its i[*] pins (out/<corner>_station.rpt): every hop, '
                    'not only the worst 200k endpoints')
    ap.add_argument('--relay-kind', choices=('rly', 'rlyh'), default='rly',
                    help='rlyh (S81-BIND3): the CLOSED half-cycle dsfd_dvrlyh_* views (ck -> ck_o negative unate, ETM tables '
                    'kept: cell_rise / cell_fall are the ck_o output edges); implies the inverted hop-0 source contract')
    ap.add_argument('--leaf-pins', type=Path, default=None,
                    help='JSON [{inst, pin, view_ref, view_dir, cell, leaf_pin}]: a stand-in block pin takes the boundary '
                    'arc of the CLOSED leaf view that owns it (S81-BIND3; cluster glue / cluster clock insertion = 0, labelled)')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--relay-ref', default='origin/main')
    ap.add_argument('--corners', nargs='+', default=['tt', 'ff'])
    a = ap.parse_args()
    (a.out / 'libs').mkdir(parents=True, exist_ok=True)
    import dv_land_pilot as LP
    for b in a.relay_widths:
        for d in RLY:
            for c in a.corners:
                rk = a.relay_kind
                p = f'physical/ref_tile/s81dv_{rk}_{b}_{d.lower()}/views/dsfd_dv{rk}_{b}_{d}/dsfd_dv{rk}_{b}_{d}_{c}.lib'
                r = subprocess.run(['git', '-C', GITDIR, 'show', f'{a.relay_ref}:{p}'], capture_output=True, text=True)
                if r.returncode:
                    continue
                lib = patch_ck_o(r.stdout)
                if rk == 'rlyh':
                    i_ = lib.index('S81-DIE4 STA pilot: ETM self-related')
                    j_ = lib.rindex('timing_sense : positive_unate', 0, i_)
                    lib = lib[:j_] + 'timing_sense : negative_unate' + lib[j_ + len('timing_sense : positive_unate'):]
                    lib = lib.replace('/* S81-DIE4 STA pilot:', '/* S81-BIND3: CLOSED half-cycle view, ck_o = ~ck | S81-DIE4 STA pilot:', 1)
                elif a.hop_fix == 'half':
                    lib = LP._swap_ck_o(lib)
                elif a.hop_fix == 'outhold':
                    lib = LP._outhold(lib, a.outhold_ps)
                (a.out / 'libs' / (f'rly_{d}_{c}.lib' if b == 276 else f'rly_{b}_{d}_{c}.lib')).write_text(lib)
    sta = STA
    if a.standin_views:
        for f in sorted(a.standin_views.glob('dv_*.lib')):
            for c in a.corners:
                txt = standin_contract(f.read_text(), a.src_data_ps, a.src_cko_ps, a.hop_fix == 'half' or a.relay_kind == 'rlyh')
                if a.leaf_pins:
                    txt = leaf_pin_arcs(txt, f.stem, a.leaf_pins, c)
                (a.out / 'libs' / f'{f.stem}_{c}.lib').write_text(txt)
        sta = sta.replace('[glob $C/views/dv_*.lib]', '[glob /pilot/libs/dv_*_{corner}.lib]')
    if a.station_report:
        sta = sta.replace('puts OT_STA_DONE', STATION_RPT + 'puts OT_STA_DONE')
    for c in a.corners:
        (a.out / f'sta_{c}.tcl').write_text(sta.format(corner=c, plat=PLAT, std=' '.join(STD[c])))
    (a.out / 'classify.py').write_text(CLASSIFY)
    runs = '; '.join(f'/usr/bin/time -v openroad -threads ${{CPUS:-8}} -no_init -exit /pilot/sta_{c}.tcl > /pilot/out/sta_{c}.log 2>&1' for c in a.corners)
    (a.out / 'run.sh').write_text(f'''#!/bin/bash
# S81-DV die STA pilot (NOT_A_DIE_RESULT); case {a.case_remote}
D=$(cd $(dirname $0) && pwd); N=dvsta-$$; mkdir -p $D/out
docker run --rm --name $N --cpus=${{CPUS:-8}} --memory=${{MEMG:-96}}g -v {a.case_remote}:/case:ro -v $D:/pilot -w /pilot openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; {runs}; chmod -R a+rwX /pilot/out"
rc=$?; python3 $D/classify.py {a.case_remote}/case.json $D/out {' '.join(a.corners)} > $D/out/classes.txt 2>&1; echo $rc > $D/out/run.exit; exit $rc
''')
    (a.out / 'run.sh').chmod(0o755)
    print(a.out)


if __name__ == '__main__':
    main()
