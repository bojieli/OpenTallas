import json, subprocess, sys, re, math
R='/home/ubuntu/OpenTallas'
def show(ref, path):
    try: return subprocess.run(['git','-C',R,'show',f'{ref}:{path}'],capture_output=True,text=True,timeout=60).stdout
    except Exception: return ''
def audit(ref, kit):
    d=f'physical/ref_tile/{kit}'
    s=show(ref,d+'/spec.json'); 
    if not s: return {'kit':kit,'err':'no spec'}
    s=json.loads(s); env=show(ref,d+'/kit.env'); g=show(ref,d+'/gate_result.json'); fp=show(ref,d+'/floorplan.json')
    g=json.loads(g) if g.strip().startswith('{') else {}
    fp=json.loads(fp) if fp.strip().startswith('{') else {}
    out={'kit':kit,'ref':ref,'gate':g.get('verdict'),'gate_commit':(g.get('commit') or '')[:9],'kind':s.get('kind')}
    pr=s.get('pin_regs'); pr_on=bool((isinstance(pr,dict) and pr.get('enable')) or s.get('io_flop_at_pins') or 'OT_PIN_REGS=1' in env or 'OT_KEEP_PIN_REGS=1' in env)
    excl=(pr or {}).get('exclude') if isinstance(pr,dict) else None
    rl='OT_RST_LAND=1' in env; rp=s.get('reset_ports') or []
    out['1pins']=f"pinregs={'on' if pr_on else 'OFF'}{' excl='+str(excl) if excl else ''} reset_ports={len(rp)} landing={'on' if rl else ('OFF' if rp else 'n/a')}"
    o=s.get('outline',{}); w,h=o.get('w'),o.get('h')
    if w and h: out['outline']=f"{w}x{h} ar {max(w,h)/min(w,h):.2f}"
    items=g.get('items',[])
    def pick(pat): return [i for i in items if re.search(pat,(i.get('check') or '')+' '+(i.get('message') or ''),re.I)]
    def fmt(lst,n=2): return ' || '.join(f"{i.get('severity')} {i.get('check')}: {(i.get('message') or '')[:170]}" for i in lst[:n])
    out['2reach']=fmt([i for i in pick(r'reach|wire_len|405|relay') if 'fanout' not in (i.get('check') or '')]) or '-'
    hf=pick(r'high_fanout'); out['3fanout']=(f"{len(hf)} WARN; "+fmt(hf,1)) if hf else '-'
    ld=pick(r'logic_depth'); out['4depth']=fmt(ld,1) or '-'
    out['5storage']=fmt(pick(r'flop.?array|storage|memory_infer|ram|delay.?line|hold chain'),1) or '-'
    mac=[b for b in fp.get('blocks',[]) if b.get('kind') in ('macro','child','hard')]
    off=[b for b in mac if abs(b['x']/43.2-round(b['x']/43.2))>1e-3]
    out['6fp']=f"macros={len(mac)} offlattice_x={len(off)} "+(fmt(pick(r'^util|fill|channel|density|pin demand|FLOORPLAN'),3) or '')
    hm=(s.get('route') or {}).get('io_hold_margin_ns')
    out['7clock']=f"io_hold_margin={hm} "+(fmt(pick(r'clock_rule|clock_domain|spread|ck_insertion'),2) or '')
    out['fails']=fmt([i for i in items if i.get('severity') in ('FAIL','REFUSE')],4) or '-'
    return out
if __name__=='__main__':
    for a in sys.argv[1:]:
        ref,kit=a.split(':')
        r=audit(ref,kit); print(json.dumps(r))
