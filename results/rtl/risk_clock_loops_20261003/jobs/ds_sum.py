import json,glob,sys,os
for f in sorted(glob.glob(os.path.expanduser('~/rcl-20261003/runs/ds/*.json'))):
    r=json.load(open(f)); ph=r['phases']; P=r['period_ns']*1000
    def fm(x): return '-' if x is None else f'{x:.0f}'
    def ws(x): return '-' if x is None else f'{x:.0f}'
    raw,rep=ph['raw'],ph['rep']
    print(f"{r['label']}: P={P:.0f} cells={r['synth']['cells']} raw r2r {fm(raw['r2r_fmax_mhz'])}MHz ws {ws(raw['r2r_setup_wns_ps'])} | rep r2r ws {ws(rep['r2r_setup_wns_ps'])} {fm(rep['r2r_fmax_mhz'])}MHz | all {fm(rep['all_fmax_mhz'])} rc={r['openroad_rc']}")
    for tag in ('raw','rep'):
        p=ph[tag]['r2r_path']; 
        print(f"   {tag} path {p['startpoint']} -> {p['endpoint']} cells={p['logic_cells']} maxfo={p['max_fanout_on_path']} arr={p.get('arrival_ps')}")
    for tag in ('raw','rep'):
        for k,v in (ph[tag].get('focus') or {}).items():
            pp=v.get('path') or {}
            print(f"   focus[{tag}] {k}: n={v.get('n_pins')} ws={ws(v.get('setup_wns_ps'))} fmax={fm(v.get('fmax_mhz'))} {pp.get('startpoint')} -> {pp.get('endpoint')} cells={pp.get('logic_cells')} maxfo={pp.get('max_fanout_on_path')}")
