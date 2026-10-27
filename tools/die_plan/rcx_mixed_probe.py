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
        return R.widen(stock,{},widths)[0]


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
    # In correctly selected multi-width tables: .16/.64=.25, .32/.64=.5,
    # .64/.64=1 and 1.28/.64=2. Constant .25 diagnoses the known second-entry clamp.
    wide=[ratio for name,ratio in ratios.items() if any('_'+tag in name for tag in ('w32','w64','w128'))]
    clamped=bool(wide) and all(r is not None and abs(r-.25)<.02 for r in wide)
    result=dict(scope='native OpenRCX table-selection mechanism only; marker C is synthetic',
        verdict='FAIL' if clamped else 'REVIEW',mixed_width_qualified=False,
        root_cause='second width entry used for every wider wire' if clamped else 'inspect native selection ratios',
        modes=data,marker_multi_over_single064_cap=ratios)
    (out/'summary.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('command',choices=('gen','rules','render','report'));ap.add_argument('out');ap.add_argument('--stock')
    a=ap.parse_args()
    if a.command=='gen':geometry(a.out)
    elif a.command=='rules':rules(a.out,a.stock)
    elif a.command=='render':render(a.out)
    else:report(a.out)

if __name__=='__main__':main()
