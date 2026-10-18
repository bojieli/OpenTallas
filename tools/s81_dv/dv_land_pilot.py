#!/usr/bin/env python3
"""S81-LAND: model the forwarded-clock LANDING (LANDING-CONTRACT.md, rtl/dsrom_sys/s81_dv/land) in the die STA pilot.

The pilot case (dv_diecase stand-ins) has no landing cells; every lane's last hop ends on a stand-in block input that
captures on the root clk.  A landing (ring of D slots written on the lane's forwarded clock, read E edges later on the
block root) turns that arrival hop into (a) one ordinary forwarded-clock hop into the ring and (b) the ring -> o
crossing, whose setup / hold are the arrival path's with the capture edge moved by E (setup) and by E - D (hold):
        setup_E = S1 + (E - 1) T          hold_E = H0 + (D - E) T            (S1 / H0: single-cycle pilot slacks)
which SDC states exactly as   set_multicycle_path -setup E  /  -hold (D - 1)   on the lane's block-input pins.
ONE E per link (all lanes of a bundle share the compiler slot), the SAME E at TT and FF.

  dv_land_pilot.py plan --case case.json --reports OUTDIR --out DIR [--D 4] [--corners tt ff]
      -> DIR/land_plan.json (per link: stages, S1 / H0 per corner, E, window margins, added edges) + DIR/landing.sdc
  dv_land_pilot.py kit --plan DIR --case-remote CASE --libs-remote LIBS [--corners tt ff]
      -> DIR/sta_land_<corner>.tcl + run.sh: the dv_sta_pilot STA with landing.sdc sourced, plus per-link worst
         setup / hold at the landed block pins (link_<corner>.rpt) and the relay-hop hold path details (hop_<corner>.rpt)
  dv_land_pilot.py variant --mode {half,outhold} --base-libs DIR --out DIR --case-remote CASE --out-remote RDIR
      relay->relay hold fix prototypes on the same routed case (S81-LAND2):
        half    : half-cycle hops -- every relay's ck -> ck_o arc becomes NEGATIVE unate (ck_o = ~ck: rise/fall tables
                  swapped; the kept inverter pair becomes one/three inverters), and every DFF stand-in station's BUF
                  clock forward (ff_*) is replace_cell'd by INVx8; station k+1 captures half a period after station k
        outhold : every relay data output o[*] launches --outhold-ps later (cell_rise/cell_fall + ps, min AND max: a
                  delay cell in the relay output adds to both)
      -> DIR/{libs/, sta_<c>.tcl, run.sh}; run.sh = base STA (no landing) + classify, then plan + kit + landed STA
"""
import argparse, collections, json, math, re
from pathlib import Path
T = 833.333


def end_slacks(path):
    """endpoint -> slack from a report_checks -format end report"""
    out = {}
    for line in open(path):
        f = line.split()
        if len(f) < 4 or '/' not in f[0]:
            continue
        try:
            out[f[0]] = float(f[-2] if f[-1] in ('(VIOLATED)', '(MET)') else f[-1])
        except ValueError:
            pass
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('plan')
    p.add_argument('--case', required=True, type=Path)
    p.add_argument('--reports', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--D', type=int, default=4)
    p.add_argument('--corners', nargs='+', default=['tt', 'ff'])
    k = sp.add_parser('kit')
    k.add_argument('--plan', required=True, type=Path)
    k.add_argument('--case-remote', required=True)
    k.add_argument('--libs-remote', required=True)
    k.add_argument('--corners', nargs='+', default=['tt', 'ff'])
    k.add_argument('--extra-tcl', type=Path, default=None, help='tcl inserted after read_db (variant netlist edits)')
    k.add_argument('--standin-libs', action='store_true', help='read the stand-in block libs from the libs dir (dv_sta_pilot '
                   '--standin-views hop-0 source contract) instead of the case views')
    k.add_argument('--hop-endpoints', nargs='*', default=['st_x_f_0L00_l2_0/i[22]', 'st_tvS_s_7N_0/i[117]', 'st_tvS_s_7N_5/i[117]',
                                                         'st_xrE_0S_l1_0/i[33]', 'st_xrE_0S_l1_3/i[33]', 'st_pv_W_l1_0/i[224]'])
    v = sp.add_parser('variant')
    v.add_argument('--mode', choices=('half', 'outhold'), required=True)
    v.add_argument('--outhold-ps', type=float, default=200.0)
    v.add_argument('--base-libs', required=True, type=Path, help='local copy of the pilot rly_<d>_<c>.lib (ck->ck_o patched)')
    v.add_argument('--out', required=True, type=Path)
    v.add_argument('--case-remote', required=True)
    v.add_argument('--out-remote', required=True)
    v.add_argument('--corners', nargs='+', default=['tt', 'ff'])
    v.add_argument('--D', type=int, default=4)
    a = ap.parse_args()
    if a.cmd == 'kit':
        return kit(a)
    if a.cmd == 'variant':
        return variant(a)
    case = json.load(open(a.case))
    links = {}
    for c in case['chains']:
        nm = c['link'].replace('-', '_')
        blk, pin = c['dst'].split('.')
        links[nm] = dict(cls=c['cls'], bits=c['bits'], stages=c['stages'], dst=blk, pin=pin)
    S = {c: end_slacks(a.reports / f'{c}_setup.end.rpt') for c in a.corners}
    H = {c: end_slacks(a.reports / f'{c}_hold.end.rpt') for c in a.corners}
    per = collections.defaultdict(lambda: {c: dict(s1=1e9, h0=1e9, n=0) for c in a.corners})
    rx = re.compile(r'u_(.+)/(i_.+)\[\d+\]$')
    for c in a.corners:
        for ep, sl in S[c].items():
            m = rx.match(ep)
            if m and m.group(2)[2:] in links:
                d = per[m.group(2)[2:]][c]; d['s1'] = min(d['s1'], sl); d['n'] += 1
        for ep, sl in H[c].items():
            m = rx.match(ep)
            if m and m.group(2)[2:] in per:
                d = per[m.group(2)[2:]][c]; d['h0'] = min(d['h0'], sl)
    plan, sdc = [], ['# S81-LAND landing model (tools/s81_dv/dv_land_pilot.py): per forwarded-clock link, ring D = %d,'
                     ' ONE E for TT and FF; NOT_A_DIE_RESULT (stand-in blocks)' % a.D]
    hist = collections.Counter()
    for nm, L in sorted(links.items()):
        if L['stages'] == 0:
            continue                                   # no relay: no forwarded clock (neighbour root -> root)
        r = per.get(nm)
        if r is None:   # no block pin in the worst-200k setup lists at any corner: single-cycle met with margin -> E = 1
            r = {c: dict(s1=0.0, h0=1e9, n=0, unlisted=True) for c in a.corners}
        # hold end reports list only the worst 200k endpoints: an absent block pin met hold with margin (> listed worst)
        e_min = max(1 + max(0, math.ceil(-r[c]['s1'] / T)) for c in a.corners)
        e = e_min
        su = {c: round(r[c]['s1'] + (e - 1) * T, 1) for c in a.corners}
        ho = {c: (round(r[c]['h0'] + (a.D - e) * T, 1) if r[c]['h0'] < 1e8 else None) for c in a.corners}
        ok = all(v >= 0 for v in su.values()) and all(v is None or v >= 0 for v in ho.values())
        fin = [r[c]['s1'] for c in a.corners if r[c]['s1'] < 1e8]     # unlisted at a corner = met with margin there
        spread = round(max(fin) - min(fin), 1) if fin else 0.0
        plan.append(dict(link=nm, cls=L['cls'], dst=L['dst'], bits=L['bits'], stages=L['stages'],
                         s1={c: round(r[c]['s1'], 1) for c in a.corners},
                         h0={c: (round(r[c]['h0'], 1) if r[c]['h0'] < 1e8 else None) for c in a.corners},
                         E=e, setup_E=su, hold_E=ho, tt_ff_spread_ps=spread, window_ok=ok,
                         added_edges=1 + e, ring_flops=a.D * L['bits'] + L['bits']))
        hist[e] += 1
        sdc.append(f'set_multicycle_path -setup {e} -to [get_pins u_{L["dst"]}/{L["pin"]}[*]]')
        sdc.append(f'set_multicycle_path -hold {a.D - 1} -to [get_pins u_{L["dst"]}/{L["pin"]}[*]]')
    a.out.mkdir(parents=True, exist_ok=True)
    summ = dict(links=len(plan), E_hist=dict(sorted(hist.items())), window_fail=[p['link'] for p in plan if not p['window_ok']],
                ring_flops=sum(p['ring_flops'] for p in plan), bits=sum(p['bits'] for p in plan),
                max_spread_ps=max(p['tt_ff_spread_ps'] for p in plan))
    json.dump(dict(schema='opentallas.s81_land.pilot_plan.v1', T_ps=T, D=a.D, corners=a.corners,
                   rule='E = max over corners of 1 + ceil(-S1/T); setup_E = S1 + (E-1)T; hold_E = H0 + (D-E)T', summary=summ,
                   links=plan), open(a.out / 'land_plan.json', 'w'), indent=1)
    (a.out / 'landing.sdc').write_text('\n'.join(sdc) + '\n')
    print(json.dumps(summ, indent=1))


def _swap_ck_o(lib):
    """ck -> ck_o positive -> negative unate: an odd inverter count, so ck_o rises when ck falls (cell_rise <- the
    falling-input table, i.e. the old cell_fall, and vice versa; transitions follow their output edge)."""
    m = re.search(r'pin\("ck_o"\)\s*\{', lib)
    i = lib.index('timing_sense : positive_unate;', m.start())
    j = lib.index('\n    }\n', i)
    body = lib[i:j].replace('positive_unate', 'negative_unate', 1)
    body = body.replace('/* S81-DIE4', '/* S81-LAND2 HALF-CYCLE PROTOTYPE: ck_o = ~ck (tables of the even-inverter view, edges swapped) | S81-DIE4')
    tmp = {'cell_rise(': '@CF(', 'cell_fall(': '@CR(', 'rise_transition(': '@FT(', 'fall_transition(': '@RT('}
    for k, t in tmp.items():
        body = body.replace(k, t)
    for t, k in (('@CR(', 'cell_rise('), ('@CF(', 'cell_fall('), ('@RT(', 'rise_transition('), ('@FT(', 'fall_transition(')):
        body = body.replace(t, k)
    return lib[:i] + body + lib[j:]


def _outhold(lib, ps):
    """+ps on every o[*] rising_edge arc delay (cell_rise / cell_fall values)"""
    out, pos = [], 0
    for m in re.finditer(r'pin\("o\[\d+\]"\)\s*\{', lib):
        e = lib.index('\n    }\n', m.start())
        seg = lib[m.start():e]
        seg = re.sub(r'((?:cell_rise|cell_fall)\(\w+\)\s*\{\s*index_1\("[^"]*"\);\s*values\(")([^"]*)("\))',
                     lambda g: g.group(1) + ','.join(f'{float(x) + ps:.5f}' for x in g.group(2).split(',')) + g.group(3), seg)
        out.append(lib[pos:m.start()]); out.append(seg); pos = e
    out.append(lib[pos:])
    return ''.join(out).replace('cell (', f'/* S81-LAND2 OUTHOLD PROTOTYPE: o[*] launch +{ps:g} ps */\n  cell (', 1)


def variant(a):
    import shutil, sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import dv_sta_pilot as P
    (a.out / 'libs').mkdir(parents=True, exist_ok=True)
    for f in sorted(a.base_libs.glob('rly_*_*.lib')):
        lib = f.read_text()
        lib = _swap_ck_o(lib) if a.mode == 'half' else _outhold(lib, a.outhold_ps)
        (a.out / 'libs' / f.name).write_text(lib)
    extra = ''
    if a.mode == 'half':
        extra = ('# S81-LAND2 HALF-CYCLE PROTOTYPE: DFF stand-in station clock forwards BUFx8 -> INVx8 (ck_o = ~ck)\n'
                 'set nrep 0; foreach i [get_cells ff_*] { replace_cell $i INVx8_ASAP7_75t_R; incr nrep }\n'
                 'puts "OT_HALF_REPLACED $nrep"\n')
    for c in a.corners:
        t = P.STA.format(corner=c, plat=P.PLAT, std=' '.join(P.STD[c]))
        t = t.replace('NOT_A_DIE_RESULT', f'NOT_A_DIE_RESULT + S81-LAND2 {a.mode} hop prototype')
        t = t.replace('source {plat}/setRC.tcl'.format(plat=P.PLAT), extra + 'source {plat}/setRC.tcl'.format(plat=P.PLAT))
        (a.out / f'sta_{c}.tcl').write_text(t)
    (a.out / 'classify.py').write_text(P.CLASSIFY)
    here = Path(__file__).resolve().parent
    for f in ('dv_land_pilot.py', 'dv_sta_pilot.py'):
        shutil.copy(here / f, a.out / f)
    cs = ' '.join(a.corners)
    runs = '; '.join(f'/usr/bin/time -v openroad -threads ${{CPUS:-8}} -no_init -exit /pilot/sta_{c}.tcl > /pilot/out/sta_{c}.log 2>&1' for c in a.corners)
    if extra:
        (a.out / 'extra.tcl').write_text(extra)
    xt = f' --extra-tcl $D/extra.tcl' if extra else ''
    (a.out / 'run.sh').write_text(f'''#!/bin/bash
# S81-LAND2 hop-fix prototype {a.mode} (NOT_A_DIE_RESULT); case {a.case_remote}
D=$(cd $(dirname $0) && pwd); N=dvhop-$$; mkdir -p $D/out $D/land
docker run --rm --name $N --cpus=${{CPUS:-8}} --memory=${{MEMG:-48}}g -v {a.case_remote}:/case:ro -v $D:/pilot -w /pilot openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; {runs}; chmod -R a+rwX /pilot/out" || {{ echo 1 > $D/out/run.exit; exit 1; }}
python3 $D/classify.py {a.case_remote}/case.json $D/out {cs} > $D/out/classes.txt 2>&1
python3 $D/dv_land_pilot.py plan --case {a.case_remote}/case.json --reports $D/out --out $D/land --D {a.D} --corners {cs} > $D/land/plan.txt 2>&1 || {{ echo 2 > $D/out/run.exit; exit 2; }}
python3 $D/dv_land_pilot.py kit --plan $D/land --case-remote {a.case_remote} --libs-remote {a.out_remote}/libs --corners {cs}{xt}
bash $D/land/run.sh; rc=$?
python3 $D/classify.py {a.case_remote}/case.json $D/land/out {cs} > $D/land/out/classes.txt 2>&1
echo $rc > $D/out/run.exit; exit $rc
''')
    (a.out / 'run.sh').chmod(0o755)
    print(a.out)


def kit(a):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import dv_sta_pilot as P
    plan = json.load(open(a.plan / 'land_plan.json'))
    for c in a.corners:
        t = P.STA.format(corner=c, plat=P.PLAT, std=' '.join(P.STD[c]))
        t = t.replace('NOT_A_DIE_RESULT', 'NOT_A_DIE_RESULT + S81-LAND landing model (landing.sdc)')
        t = t.replace('set_false_path -from [get_ports rst]', 'set_false_path -from [get_ports rst]\nsource /pilot/landing.sdc')
        t = t.replace('puts OT_STA_DONE', f'''set fo [open /pilot/out/link_{c}.rpt w]
foreach {{l pins}} {{{' '.join(f'{p["link"]} u_{p["dst"]}/i_{p["link"]}[*]' for p in plan['links'])}}} {{
  set ps [get_pins $pins]
  foreach d {{max min}} {{
    set pe [lindex [find_timing_paths -path_delay $d -to $ps -group_path_count 1] 0]
    if {{$pe eq ""}} {{ puts $fo "$l $d none"; continue }}
    set pn "?"; catch {{ set pn [get_full_name [[$pe path] pin]] }}
    set sl "?"; catch {{ set sl [sta::format_time [$pe slack] 1] }}
    puts $fo "$l $d $sl $pn"
  }}
}}
close $fo
foreach ep {{{' '.join(a.hop_endpoints)}}} {{
  catch {{ report_checks -path_delay min -to [get_pins $ep] -fields {{slew cap fanout}} -digits 1 >> /pilot/out/hop_{c}.rpt }}
}}
puts OT_STA_DONE''')
        t = t.replace('/pilot/libs/', '/libs/')
        if a.standin_libs:
            t = t.replace('[glob $C/views/dv_*.lib]', '[glob /libs/dv_*.lib]')
        if a.extra_tcl:
            t = t.replace(f'source {P.PLAT}/setRC.tcl', a.extra_tcl.read_text() + f'source {P.PLAT}/setRC.tcl', 1)
        (a.plan / f'sta_land_{c}.tcl').write_text(t)
    runs = '; '.join(f'/usr/bin/time -v openroad -threads ${{CPUS:-8}} -no_init -exit /pilot/sta_land_{c}.tcl > /pilot/out/sta_{c}.log 2>&1' for c in a.corners)
    (a.plan / 'run.sh').write_text(f'''#!/bin/bash
# S81-LAND die STA pilot with the landing model (NOT_A_DIE_RESULT); case {a.case_remote}
D=$(cd $(dirname $0) && pwd); N=dvland-$$; mkdir -p $D/out
docker run --rm --name $N --cpus=${{CPUS:-8}} --memory=${{MEMG:-48}}g -v {a.case_remote}:/case:ro -v {a.libs_remote}:/libs:ro -v $D:/pilot -w /pilot openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; {runs}; chmod -R a+rwX /pilot/out"
rc=$?; echo $rc > $D/out/run.exit; exit $rc
''')
    (a.plan / 'run.sh').chmod(0o755)
    print(a.plan)


if __name__ == '__main__':
    main()
