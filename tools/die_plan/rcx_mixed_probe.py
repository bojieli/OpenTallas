#!/usr/bin/env python3
"""Tiny mixed-width OpenRCX table-selection coupon; marker rules are NEVER timing rules."""
import argparse
import json
import re
from pathlib import Path
from unittest import mock
import rcx_width_probe as P
import rcx_width_rules as R

WIDTHS = (.16, .32, .64, 1.28)
CASES = [('w04', .04, None), ('w04_sh', .04, .04)]
for tag, width, space in [('w16', .16, .08), ('w32', .32, .08), ('w64', .64, .5), ('w128', 1.28, 1.)]:
    CASES += [(tag, width, None), (tag+'_sh', width, space)]


def geometry(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with mock.patch.object(P, 'CASES', CASES):
        P.gen(str(out))
    text=(out/'probe.def').read_text()
    for width, spacing in ((.64,.5),(1.28,1.)):
        text=text.replace(f'WIDTH {P.i(width)} SPACING 80',f'WIDTH {P.i(width)} SPACING {P.i(spacing)}')
    (out/'probe.def').write_text(text)
    (out/'cases.json').write_text(json.dumps(dict(scope='table-selection only; no timing qualification',
        length_um=P.LEN_UM,cases=[dict(name=n,width_um=w,shield_spacing_um=s) for n,w,s in CASES]),indent=1)+'\n')


def marker_rules(stock, widths):
    # Deliberately encode width as C/C(stock)=W/.04. This reveals which
    # table OpenRCX selects. These values are NOT physical capacitance.
    def encode(kind, layer, label, row, width, cal, cache, provenance):
        if kind == 'RESOVER':return row[:-1]+[row[-1]*R.W0/width]
        spacing, coupling, fringe, resistance=row
        return [spacing,coupling*width/R.W0,fringe*width/R.W0,resistance*R.W0/width]
    with mock.patch.object(R,'_scale_row',encode):
        return R.widen(stock,{},list(widths))[0]


def rules(out, stock):
    out=Path(out);raw=Path(stock).read_text()
    (out/'marker_multi.rules').write_text(marker_rules(raw,WIDTHS))
    (out/'marker_single064.rules').write_text(marker_rules(raw,[.64]))
    rsq=R.rpersq(raw)
    modes={'stock_native':(str(stock),False), 'stock_lefres':(str(stock),True),
           'shipped016':('/out/shipped016.rules',True),
           'marker_multi':('/out/marker_multi.rules',True),
           'marker_single064':('/out/marker_single064.rules',True)}
    for tag,(path,lef) in modes.items():
        t=['read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef',
           'read_def /out/probe.def','set tech [ord::get_db_tech]']
        if lef:
            t += [f'[$tech findLayer {layer}] setResistance {value:.8g}' for layer,value in sorted(rsq.items())]
        t += [f'extract_parasitics -ext_model_file {path}'+(' -lef_res' if lef else ''),
              f'write_spef /out/rcx_{tag}.spef']
        (out/f'extract_{tag}.tcl').write_text('\n'.join(t)+'\n')
    (out/'run_extract.sh').write_text('''#!/bin/bash
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
trap 'chown -R "$HUID:$HGID" /out' EXIT
for mode in stock_native stock_lefres shipped016 marker_multi marker_single064; do
  openroad -no_init -threads 2 -exit "/out/extract_$mode.tcl" > "/out/extract_$mode.log" 2>&1
done
''')


def render(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    out=Path(out);fig,ax=plt.subplots(figsize=(11,9))
    index=0
    for layer in P.LAYERS:
        for name,width,space in CASES:
            c=20+20*index;index+=1
            points=[(10,c),(110,c)] if layer=='M8' else [(c,10),(c,110)]
            ax.plot(*zip(*points),color='royalblue',lw=max(.8,width*2))
            for x,y in points:ax.plot(x,y,'o',ms=2,color='black')
            if space is not None:
                for sign in (-1,1):
                    offset=sign*(width+space)
                    q=[(9,c+offset),(111,c+offset)] if layer=='M8' else [(c+offset,9),(c+offset,111)]
                    ax.plot(*zip(*q),color='seagreen',lw=max(.5,width))
            x,y=points[1]
            ax.text(x+3,y if layer=='M8' else y+3,f'{layer} {name} {width:g} um',fontsize=6,
                    rotation=0 if layer=='M8' else 90,ha='left',va='center' if layer=='M8' else 'bottom')
    ax.set(xlim=(0,440),ylim=(0,280),xlabel='um',ylabel='um',
           title='Mixed-width clock RCX coupon: 100 um wires, matching endpoint pins, isolated cases\nBlue: clock; green: VSS shields. Line thickness enlarged for visibility.')
    ax.set_aspect('equal');fig.tight_layout();fig.savefig(out/'review.png',dpi=150);plt.close(fig)


def report(out):
    out=Path(out);data=P.report(str(out));ratios={}
    for name,values in data['marker_multi'].items():
        denominator=data['marker_single064'][name]['c_ff_per_um']
        ratios[name]=values['c_ff_per_um']/denominator if denominator else None
    expected={}
    for layer in P.LAYERS:
        for name,width,_space in CASES:
            # A single .64 table uses stock below .64 and its .64 entry
            # at/above .64. The full table has an exact entry for each width.
            expected[layer+'_'+name]=(width/.04 if width>.04 else 1)/(16 if width>=.64 else 1)
    checks={}
    for name, ratio in expected.items():
        observed=data['marker_multi'][name]['c_ff_per_um']
        control=data['marker_single064'][name]['c_ff_per_um']
        # report() rounds C to five decimals: propagate that quantisation.
        checks[name]=abs(observed-ratio*control) <= (1+ratio)*.5e-5+1e-12
    passed=all(checks.values())
    result=dict(scope='native OpenRCX table-selection mechanism only; marker C is synthetic',
        verdict='PASS' if passed else 'FAIL',mixed_width_qualified=False,
        finding='all four exact width entries selected; generator cache omitted W' if passed else 'inspect native selection ratios',
        modes=data,marker_multi_over_single064_cap=ratios,expected_ratios=expected,checks=checks)
    (out/'selection_report.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1))



def single_width_table(text, width):
    """Keep stock plus one exact width from an already calibrated multi table."""
    lines=text.splitlines();out=[];layer=None;index=0
    while index<len(lines):
        line=lines[index]
        match=re.match(r'^Metal (\d+) [A-Z]+$',line)
        if match:layer=int(match.group(1))
        if layer in (8,9) and line.startswith('WIDTH Table'):
            entries=[float(x) for x in line.split('entries:',1)[1].split()]
            if entries:
                if not any(abs(x-width)<1e-9 for x in entries):raise ValueError(f'width {width} missing')
                line=f'WIDTH Table 2 entries:  0.04 {width:g}'
        if layer in (8,9) and line.startswith('DIST count'):
            match=re.search(r'width ([0-9.]+)',line)
            if match and not any(abs(float(match.group(1))-x)<1e-9 for x in (.04,width)):
                while index<len(lines) and not lines[index].startswith('END DIST'):index+=1
                index+=1;continue
        out.append(line);index+=1
    return '\n'.join(out)+'\n'


def physical(out, rules_path):
    import shutil
    out=Path(out);text=Path(rules_path).read_text()
    (out/'physical_multi.rules').write_text(text)
    for width in WIDTHS:
        tag=f'physical_single{round(width*1000):04}'
        (out/(tag+'.rules')).write_text(single_width_table(text,width))
    rsq=R.rpersq(text)
    for tag in ['physical_multi']+[f'physical_single{round(w*1000):04}' for w in WIDTHS]:
        lines=['read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef',
               'read_def /out/probe.def','set tech [ord::get_db_tech]']
        lines += [f'[$tech findLayer {layer}] setResistance {value:.8g}' for layer,value in sorted(rsq.items())]
        lines += [f'extract_parasitics -ext_model_file /out/{tag}.rules -lef_res',f'write_spef /out/rcx_{tag}.spef']
        (out/('extract_'+tag+'.tcl')).write_text('\n'.join(lines)+'\n')
    (out/'run_physical.sh').write_text('#!/bin/bash\nset -e\nsource /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1\ntrap \'chown -R "$HUID:$HGID" /out\' EXIT\nfor mode in physical_multi physical_single0160 physical_single0320 physical_single0640 physical_single1280; do\n  openroad -no_init -threads 2 -exit "/out/extract_$mode.tcl" > "/out/extract_$mode.log" 2>&1\ndone\n')


def physical_report(out):
    import hashlib
    out=Path(out);data=P.report(str(out));checks={}
    for layer in P.LAYERS:
        for name,width,_space in CASES:
            net=layer+'_'+name
            control=data[f'physical_single{round(max(width,.16)*1000):04}'][net]
            actual=data['physical_multi'][net]
            checks[net]=dict(verdict='PASS' if actual==control else 'FAIL',width_um=width,multi=actual,single=control)
    passed=all(x['verdict']=='PASS' for x in checks.values())
    result=dict(schema='opentallas.rcx_mixed_width_qualification.v1',verdict='PASS' if passed else 'FAIL',
        native_pass=passed,widths_um=list(WIDTHS),layers=list(P.LAYERS),
        rules_sha256=hashlib.sha256((out/'physical_multi.rules').read_bytes()).hexdigest(),
        checks=checks,scope='native exact-width table selection versus independent single-width extraction',
        calibration='existing ASAP7 field-solver calibration; R(sheet)/width, no flow default changes',
        die_timing_qualified=False)
    (out/'physical_qualification.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('command',choices=('gen','rules','render','report','physical','physical-report'));ap.add_argument('out');ap.add_argument('--stock');ap.add_argument('--rules')
    a=ap.parse_args()
    if a.command=='gen':geometry(a.out)
    elif a.command=='rules':rules(a.out,a.stock)
    elif a.command=='render':render(a.out)
    elif a.command=='physical':physical(a.out,a.rules)
    elif a.command=='physical-report':physical_report(a.out)
    else:report(a.out)

if __name__=='__main__':main()
