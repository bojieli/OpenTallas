"""CP2 core taps. Legacy add uses an ETM MAX bound; add_from_means is the explicit authoritative mean policy.

S81-TYPES-7-CTAP 11-08 (class CORE-TAP-LATE): a core clock pin left on a grid tap arrives at
leg + internal, where the grid-tap leg measured 53-262 ps on leaf t27 (OT_TAP_CORE, 4_1_cts.log),
so a 246-ps core already overshoots target 250 +/- window and CTS pads its whole tap.  Opt-in
leg_ps / window_ps make the rule internal + leg_ps > common_ps - window_ps (defaults 0 keep the old
internal > common_ps rule).  merge=True keeps the type's existing taps (their clk_c<k> order stays,
new core taps are appended, an existing tap of the same name is not duplicated); the default
replaces clock.taps as before.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from cores import clock_pins, lef_pins, resolve
from schema import tap_clear
from core_clock_contract import load as clock_contract


def _needs_tap(internal, common_ps, leg_ps, window_ps):
    return internal + leg_ps > common_ps - window_ps


def _commit(t, taps, merge):
    if not taps:
        return taps
    if merge:
        old = list((t.get('clock') or {}).get('taps') or [])
        t['clock'].update(core_taps='early', taps=old + taps)
    else:
        t['clock'].update(core_taps='early', taps=taps)
    return taps


def _existing(t, merge):
    old = (t.get('clock') or {}).get('taps') or [] if merge else []
    return {a.get('name') for a in old}, [a['xy'] for a in old if a.get('xy')]


def add(t, common_ps=250.0, modules=None, root=None, leg_ps=0.0, window_ps=0.0, merge=False):
    taps=[]
    names,taken=_existing(t,merge)
    for c in t.get('hard_cores',[]):
        if modules is not None and c.get('module') not in modules:
            continue
        geometry=lef_pins(resolve(c['lef'],root),c.get('module'))
        for pin,v in clock_pins(c,root).items():
            if not _needs_tap(v['rise'],common_ps,leg_ps,window_ps) or c['inst']+'.'+pin in names:
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
            xy=tap_clear(t,x+dx+px,y+dy+py,taken+[a['xy'] for a in taps],clear=4.32)
            taps.append(dict(name=c['inst']+'.'+pin,kind='core',xy=list(xy),
                             insertion_ps=round(v['rise'],5),budget_owner=c['lib'],
                             note='CP2 early core tap; selected TT max_clock_tree_path_rise'))
    return _commit(t,taps,merge)


def add_from_means(t, common_ps=250.0, modules=None, root=None, require_signed=True, leg_ps=0.0, window_ps=0.0,
                   merge=False):
    taps=[]
    names,taken=_existing(t,merge)
    for c in t.get('hard_cores',[]):
        if modules is not None and c.get('module') not in modules:
            continue
        geometry=lef_pins(resolve(c['lef'],root),c.get('module'))
        for pin,v in clock_contract(c,root,require_signed=require_signed).items():
            mean = v['corners']['tt']['mean_ps']
            if not _needs_tap(mean,common_ps,leg_ps,window_ps) or c['inst']+'.'+pin in names:
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
            xy=tap_clear(t,x+dx+px,y+dy+py,taken+[a['xy'] for a in taps],clear=4.32)
            taps.append(dict(name=c['inst']+'.'+pin,kind='core',xy=list(xy),
                             insertion_ps=round(mean,5),budget_owner=v['contract_source'],
                             note=('CP2 early core tap; SIGNED TT pin-register mean' if v['signed'] else
                                   'DIAGNOSTIC/BUDGET core tap; NOT a SIGNED mean contract')))
    return _commit(t,taps,merge)
