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
"""
import argparse, re, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--case-remote', required=True, help='routed DV die case dir on the run host (has out/grt.odb, views/)')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--relay-ref', default='origin/main')
    ap.add_argument('--corners', nargs='+', default=['tt', 'ff'])
    a = ap.parse_args()
    (a.out / 'libs').mkdir(parents=True, exist_ok=True)
    for d in RLY:
        for c in a.corners:
            p = f'physical/ref_tile/s81dv_rly_276_{d.lower()}/views/dsfd_dvrly_276_{d}/dsfd_dvrly_276_{d}_{c}.lib'
            lib = subprocess.run(['git', '-C', str(ROOT), 'show', f'{a.relay_ref}:{p}'], capture_output=True, text=True, check=True).stdout
            (a.out / 'libs' / f'rly_{d}_{c}.lib').write_text(patch_ck_o(lib))
    for c in a.corners:
        (a.out / f'sta_{c}.tcl').write_text(STA.format(corner=c, plat=PLAT, std=' '.join(STD[c])))
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
