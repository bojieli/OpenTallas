#!/usr/bin/env python3
"""Stage a HEAD natural hard child through the shared native core generator.

No face shell, RTL retiming, invented memory view, or route is performed here.
The spec's source commit, live context ports, geometry and review are mandatory.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def actual_centres(G,kd):
    fz=json.loads((kd/'freeze.json').read_text())
    pp=kd/'plan_pins.json'
    if not pp.exists():
        pins=[]
        for row in json.loads((kd/'pins.json').read_text()):
            name=row['bus'] if row['bit'] is None else f"{row['bus']}[{row['bit']}]"
            x,y=row['x'],row['y'];face=row['face']
            if face in ('W','E'):x+=G.PIN_LEN_UM/2*(1 if face=='W' else -1)
            elif face in ('S','N'):y+=G.PIN_LEN_UM/2*(1 if face=='S' else -1)
            pins.append(dict(name=name,x=round(x,6),y=round(y,6),layer=row['layer']))
        pp.write_text(json.dumps(dict(schema='opentallas.core.native_actual_pins.v1',module=fz['module'],pins=pins),indent=2)+'\n')
    body=json.loads(pp.read_text())
    interior={(r['bus'] if r['bit'] is None else f"{r['bus']}[{r['bit']}]"):r for r in json.loads((kd/'pins.json').read_text()) if r['face']=='interior'}
    for pin in body['pins']:
        if pin['name'] in interior:pin.update({key:interior[pin['name']][key] for key in ('x','y')})
    pp.write_text(json.dumps(body,indent=2)+'\n')
    fz['plan_pins_source']=fz['pins_file'];fz['plan_pins_source_sha256']=fz['pins_sha256']
    fz['pins_file']='plan_pins.json';fz['pins_sha256']=digest(pp)
    fz['pins_canon_sha256']=G.plan_pins_canon_sha256(json.loads(pp.read_text()),fz['outline_um'])
    fz['head_driver']=dict(tool='tools/s81_head/head_native_core_kit.py',added_cycles=0,
                           kind='unchanged natural module, timed internal boundary')
    fz['kit_hash']=G.kit_hash(kd)
    (kd/'freeze.json').write_text(json.dumps(fz,indent=2)+'\n')
    shutil.copyfile(G.TOOL/'pin_audit.py',kd/'pin_audit_core.py')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--spec',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a,rest=ap.parse_known_args()
    sf=a.spec.resolve();sp=json.loads(sf.read_text());base=sf.parent
    if sp.get('added_cycles')!=0:raise SystemExit('natural child requires0addedcycles; use a priced plan event forretiming')
    review_path=(base/sp['geometry_review']).resolve();review=json.loads(review_path.read_text())
    if review.get('verdict') not in ('PASS','PASS-COND') or not review.get('allow_kit_gen',False):
        raise SystemExit('reviewed geometry permittingkitgeneration required')
    context_path=(base/sp['context_mask_file']).resolve();context=json.loads(context_path.read_text())
    if any(v.get('constant_bits') or v.get('unused_bits') for v in context.values()):
        raise SystemExit('context hasconstant/unusedports; provide provedpackedwrapperandspecializedinterface first')
    pins_path=(base/sp['pins_file']).resolve();pins=json.loads(pins_path.read_text())
    pin_rows=pins['pins'] if isinstance(pins,dict) else pins
    if len(pin_rows)!=sum(v['width'] for v in context.values()):raise SystemExit('context/pin count differs')
    module=sp['module'];view=sp.get('view',module+'@head');out=a.out.resolve()
    inp=out/'_inputs';inp.mkdir(parents=True,exist_ok=True)
    # The shared generator requires a real repository plan even for a local child view.
    plan=(ROOT/sp.get('plan','physical/die_plan/s81_head/die_plan.json')).resolve()
    views=dict(plan=str(plan),view_list=[dict(view=view,module=module,outline_um=sp['outline_um'],
        pins_file=str(pins_path),pins_sha256=digest(pins_path),instances=[sp['parent_instance']],placed=1,recipe_keys=[module])])
    vf=inp/'views.json';vf.write_text(json.dumps(views,indent=2)+'\n')
    macros=sp.get('macro_placement',[])
    mf=inp/'macro_placement.json';mf.write_text(json.dumps(dict(macro_placement=[dict(k=m['inst'],macro=m['module'],origin_um=m['origin_um'],orient=m.get('orient','R0')) for m in macros]),indent=2)+'\n')
    gs=importlib.util.spec_from_file_location('head_native_shared',ROOT/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py')
    G=importlib.util.module_from_spec(gs);gs.loader.exec_module(G)
    original_io=G.io_tcl;clocks=set(sp.get('clock_ports',['clk']))
    def io(pins,w,h,tag):
        edge=[p for p in pins if min(p['x'],w-p['x'],p['y'],h-p['y'])<=.5]
        text,rows=original_io(edge,w,h,tag)
        for p in pins:
            if p in edge:continue
            if p['layer']!='M5':raise SystemExit('interior entry mustbeM5')
            clock=p['name'] in clocks;size=(.048,.48) if clock else (.024,.192)
            text+=f"place_pin -pin_name {{{p['name']}}} -layer M5 -location {{{p['x']:.6f} {p['y']:.6f}}} -pin_size {{{size[0]} {size[1]}}}\n"
            bus,bit=G.split_name(p['name']);rows.append(dict(bus=bus,bit=bit,x=p['x'],y=p['y'],layer='M5',face='interior',size=list(size),clock=clock))
        return text,rows
    G.io_tcl=io
    recipe=dict(top=module,files=sp['source_files'],params=sp.get('params',{}),defines=sp.get('defines',[]),
                source_commit=sp['source_commit'],read_at_commit=True,macros=sorted({m['module'] for m in macros}),
                macro_place_halo_um=4.32,source='HEAD natural hard child, unchanged interface/RTL/cycles')
    profile=dict(source_commit=sp['source_commit'],family=sp.get('family','HEAD_NATIVE_CHILD'),added_face_cycles=0,
                 qualification='UNROUTED_CANDIDATE',clock_ports=list(clocks),reset_ports=sp.get('reset_ports',['rst_n']),
                 context_mask_sha256=digest(context_path),geometry_review_sha256=digest(review_path),
                 endpoint_contract=dict(kind='INTERNAL_CORE',partition_rule='R2_INTERNAL_TIMED_IN_PARTITION',
                    parent_partition=sp['parent_partition'],instance=sp['parent_instance'],source=sp['source_files'][0]))
    if sp.get('port_inventory'):profile['port_inventory']=sp['port_inventory']
    sys.argv=['gen_core_kit_hbm','--views',str(vf),'--view',view,'--out',str(out),'--recipe-key',module,
              '--face-shell','off','--core-insertion','none','--sigmax','M7','--clock-taps','density',
              '--clock-tap-sinks','1250','--clock-tap-dmax','80']
    if macros:sys.argv+=['--macro-placement',str(mf),'--macro-inst-fmt','{k}']
    sys.argv+=rest
    G.main(recipe_overrides={module:recipe},source_profile=profile)
    kd=out/re.sub(r'[^A-Za-z0-9_.-]','_',view);actual_centres(G,kd)
    shutil.copyfile(review_path,kd/'geometry_review.json')
    shutil.copyfile(context_path,kd/'context_mask.json')
    (kd/'HOLD_PNR').write_text('Naturalcutcandidate: actualmappedgraphcut+FF/macropinreach+nativeclock G1 and strictLEC required beforeP&R.\n')
    (kd/'TRIAL_ONLY').write_text('Preparedkit; no physical signofforparentcomposition claim.\n')
    fz=json.loads((kd/'freeze.json').read_text());fz['kit_hash']=G.kit_hash(kd)
    (kd/'freeze.json').write_text(json.dumps(fz,indent=2)+'\n')
    print(json.dumps(dict(kit=str(kd),module=module,pins=len(pin_rows),srams=len(macros),added_cycles=0,status='PREPARED_HOLD_PNR')))
if __name__=='__main__':main()
