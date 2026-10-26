#!/usr/bin/env python3
"""Issue source-exact independent state leaf margin; parent topology stays open."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'results/arch/hier_contract_1015/hbm_v15.json'
c=json.loads(p.read_text()); changed=[]
for s in c['slots']:
    if not s['name'].startswith('coll_') or '_state' not in s['name']: continue
    assert s['cell']=='ot_hgi_coll_pring_static_state_lane'
    assert hashlib.sha256((ROOT/s['source']).read_bytes()).hexdigest()==s['source_sha256']
    assert s['outline']==dict(w=51.84,h=51.84), 'grant already applied or source dimensions changed'
    i=int(s['name'].split('_state')[1]); s['outline']=dict(w=64.8,h=64.8)
    s['origin'].update(x=round(200+(i%4)*75.6,3),y=round(21.6+(i//4)*75.6,3))
    for pin in s['pins']:
        pin['offset']=round(pin['offset']+6.48,3)
        pin['span_um']=[round(x+6.48,3) for x in pin['span_um']]
    s['clock_entry']['offset']=32.4
    s['grant']='independent_state_leaf_margin_1417'
    s['reroute_reason']='die_window: measured new-state CTS density/route margin; native C1472 remains separate structural failure'
    s['notes']='Source-exact independent diagnostic child only: 64.8 square, 293 pins, same groups/layers with +6.48 um local offset; unchanged state logic does not qualify native capture or parent. Parent registered peer topology/packing/clock remain OPEN.'
    changed.append(s)
assert len(changed)==32
slots={s['name']:s for s in c['slots']}
for s in changed:
    par=slots[s['parent']]; o=s['origin']; z=s['outline']
    assert o['x']+z['w']<=par['outline']['w'] and o['y']+z['h']<=par['outline']['h']
    for t in c['slots']:
        if t['name']==s['name'] or t.get('parent')!=s['parent']:continue
        a,b=t['origin'],t['outline']
        assert not(o['x']<a['x']+b['w'] and a['x']<o['x']+z['w'] and o['y']<a['y']+b['h'] and a['y']<o['y']+z['h']), (s['name'],t['name'])
c['state_margin_grant_1417']=dict(replicas=32,distinct_masters=1,outline_um=[64.8,64.8],old_outline_um=[51.84,51.84],added_outline_mm2=32*(64.8**2-51.84**2)/1e6,cycles_added=0,parent_and_die_qualified=False)
p.write_text(json.dumps(c,indent=1)+'\n')
f=ROOT/'results/arch/hbm_die_v15/collective_state_pins_1319.json';d=json.loads(f.read_text());d['outline_um']=[64.8,64.8]
for key in ('pins','pin_ranges'):
    if isinstance(d.get(key),list):
        for pin in d[key]:
            if isinstance(pin,dict):
                for a in ('offset',):
                    if a in pin: pin[a]=round(pin[a]+6.48,3)
                if 'span_um' in pin:pin['span_um']=[round(x+6.48,3) for x in pin['span_um']]
d['pin_ranges']={k:[round(x+6.48,3) for x in v] for k,v in d['pin_ranges'].items()}
d['scope']='1417 independent margin grant only; native C1472 and actual parent topology remain OPEN'
f=ROOT/'results/arch/hbm_die_v15/collective_state_pins_1417.json';f.write_text(json.dumps(d,indent=1)+'\n')
print(json.dumps(c['state_margin_grant_1417']))
