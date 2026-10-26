import json,hashlib,sys,os
# refreeze.py KITDIR REPO_PINS_REL REPO_ROOT PLAN_REL SRC OUT
kit,pins_rel,root,plan_rel,src=sys.argv[1:6]
f=json.load(open(os.path.join(kit,'freeze.json')))
pp=os.path.join(root,pins_rel); rp=json.load(open(pp)); kp=json.load(open(os.path.join(kit,'pins.json')))
def norm(d):
    L=d['pins'] if isinstance(d,dict) else d
    return sorted(((p['name'] if 'name' in p else (p['bus'] if p.get('bit') is None else '%s[%d]'%(p['bus'],p['bit']))),round(float(p['x']),4),round(float(p['y']),4),p.get('layer')) for p in L)
a,b=norm(rp),norm(kp); assert a==b,(len(a),len(b),len(set(a)^set(b)))
sh=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest()
old=dict(f); os.rename(os.path.join(kit,'freeze.json'),os.path.join(kit,'freeze.stale_aspect_s5.json'))
f.update(schema="opentallas.qc.core_freeze.v2",outline_um=[354.24,259.2],plan=plan_rel,
  plan_sha256=sh(os.path.join(root,plan_rel)),pins_file=pins_rel,pins_sha256=sh(pp),pins=len(a),
  pins_match_kit="exact name+xy+layer %d/%d"%(len(a),len(b)),source=src,
  supersedes={"freeze.stale_aspect_s5.json":{"outline_um":old["outline_um"],"pins_file":old["pins_file"]}},
  io_hold={"mode":"sender_min","sender_ps":40,"basis":"COORD 2026-10-26 00:19 two-sided 40 ps budget; counts once senders show the 40 ps min-output check (same release batch) + io_hold_parent receipt"})
f.pop('plan_lef',None)
json.dump(f,open(os.path.join(kit,'freeze.json'),'w'),indent=1); print(kit,'OK',len(a),f['plan_sha256'][:8])
