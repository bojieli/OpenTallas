"""CP2 core taps. Legacy add uses an ETM MAX bound; add_from_means is the explicit authoritative mean policy."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from cores import clock_pins, lef_pins, resolve
from schema import tap_clear
from core_clock_contract import load as clock_contract


def add(t, common_ps=250.0, modules=None, root=None):
    taps=[]
    for c in t.get('hard_cores',[]):
        if modules is not None and c.get('module') not in modules:
            continue
        geometry=lef_pins(resolve(c['lef'],root),c.get('module'))
        for pin,v in clock_pins(c,root).items():
            if v['rise']<=common_ps:
                continue
            x,y=c['origin_um'];w,h=c['outline_um']
            # The dedicated drop belongs beside the actual transformed clock pin,
            # avoiding a long unbuffered lead across the hard core.
            pp=geometry.get(pin) or geometry.get(pin.split('[')[0])
            px,py=pp['xy'] if pp and pp.get('xy') else (w/2,0.)
            orient=c.get('orient','R0')
            if orient in ('MY','R180'):px=w-px
            if orient in ('MX','R180'):py=h-py
            dx,dy=c.get('track_offset_um',[0.,0.])
            xy=tap_clear(t,x+dx+px,y+dy+py,[a['xy'] for a in taps],clear=4.32)
            taps.append(dict(name=c['inst']+'.'+pin,kind='core',xy=list(xy),
                             insertion_ps=round(v['rise'],5),budget_owner=c['lib'],
                             note='CP2 early core tap; selected TT max_clock_tree_path_rise'))
    if taps:
        t['clock'].update(core_taps='early',taps=taps)
    return taps


def add_from_means(t, common_ps=250.0, modules=None, root=None, require_signed=True):
    taps=[]
    for c in t.get('hard_cores',[]):
        if modules is not None and c.get('module') not in modules:
            continue
        geometry=lef_pins(resolve(c['lef'],root),c.get('module'))
        for pin,v in clock_contract(c,root,require_signed=require_signed).items():
            mean = v['corners']['tt']['mean_ps']
            if mean<=common_ps:
                continue
            x,y=c['origin_um'];w,h=c['outline_um']
            # The dedicated drop belongs beside the actual transformed clock pin,
            # avoiding a long unbuffered lead across the hard core.
            pp=geometry.get(pin) or geometry.get(pin.split('[')[0])
            px,py=pp['xy'] if pp and pp.get('xy') else (w/2,0.)
            orient=c.get('orient','R0')
            if orient in ('MY','R180'):px=w-px
            if orient in ('MX','R180'):py=h-py
            dx,dy=c.get('track_offset_um',[0.,0.])
            xy=tap_clear(t,x+dx+px,y+dy+py,[a['xy'] for a in taps],clear=4.32)
            taps.append(dict(name=c['inst']+'.'+pin,kind='core',xy=list(xy),
                             insertion_ps=round(mean,5),budget_owner=v['contract_source'],
                             note=('CP2 early core tap; SIGNED TT pin-register mean' if v['signed'] else
                                   'DIAGNOSTIC/BUDGET core tap; NOT a SIGNED mean contract')))
    if taps:
        t['clock'].update(core_taps='early',taps=taps)
    return taps
