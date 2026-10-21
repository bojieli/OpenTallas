import sys,json,math
from pathlib import Path
sys.path.insert(0,'tools/qwen_kv_die')
import kv_die as K, kv_bundle_eq as EQ, kv_rly_std as R
apron=int(sys.argv[1])
L=Path('/srv/opentallas-scratch/claude/codex-kv-relay-plan-2210')
def report(m):
    by={i.name:i for i in m['insts']}
    host,d2d,attn=(by[n] for n in ['host','d2d_kv','kvs_attn'])
    K._d2d_pin(d2d,'rx_payload')
    frame=R.layout(548,R.frame_rev('ks_d2d_kv__rx_payload'))[:2]
    fw,fh=frame[0]+K.SHAVE,frame[1]+K.SHAVE
    ylo,yhi=K.up(host.y+host.h+21.6,K.GY), math.floor((d2d.y-21.6-fh)/K.GY)*K.GY
    rows=[]
    y=yhi
    keep=[K.F.Inst(kn,'keepout',x,y,w,h,'R0') for kn,x,y,w,h in m.get('keepouts',[])]
    ports=['rx_payload','rec_rx','rec_tx','att_tx_payload','emb_tx_payload']
    found={p:[] for p in ports}
    while y>=ylo:
        sites=[]
        x=K.up(d2d.x-340,K.GX)
        while x<=d2d.x+d2d.w+340-fw:
            if EQ._free(m,m['insts']+keep,x,y,fw,fh):
                sites.append((round(x,3),round(y,3)))
                for p in ports:
                    ep_x=x if p in ('rx_payload','rec_rx') else x+fw-K.SHAVE
                    far=K.ep_far('d2d_kv',p,(ep_x,y+(fh-K.SHAVE)/2))
                    if far is not None and far<=340:
                        found[p].append(dict(x=round(x,3),y=round(y,3),farthest_pin_um=round(far,3)))
            x+=K.up(fw+4.32,K.GX)
        rows.append(dict(y=round(y,3),sites=sites))
        y-=K.up(fh+4.32,K.GY)
    # Distinct legal row sites must satisfy all five payload words together.
    def match(todo, used):
        if not todo:return {}
        p=todo[0]
        for v in found[p]:
            q=(v['x'],v['y'])
            if q not in used:
                rest=match(todo[1:],used|{q})
                if rest is not None:return {p:v,**rest}
        return None
    assignment=match(sorted(ports,key=lambda p:len(found[p])),set())
    assert assignment is not None, 'individual approaches exist but cannot coexist'
    # Portrait control is a slot feasibility check only, preserving exact source.
    import kv_static_die as S
    without=dict(m,insts=[i for i in m['insts'] if i.name!='kvs_ctl'])
    ctl=by['kvs_ctl']
    portrait=S.free_spot(without,345.6,475.2,(ctl.x+ctl.w/2,ctl.y+ctl.h/2),K.GX,K.GY)
    d=dict(schema='opentallas.kv_relay_corridor_plan.v1',apron_um=apron,die=m['die'],
      frame_548_um=list(frame),actual_channel_um=d2d.y-host.y-host.h,rows=rows,endpoint_approaches=found,
      homes={n:dict(x=by[n].x,y=by[n].y,w=by[n].w,h=by[n].h) for n in ['host','kvs_attn','kvs_emb','d2d_kv','kvs_ctl']},
      future_ctl_portrait=dict(x=portrait[0],y=portrait[1],w=345.6,h=475.2,adopted=False,source_flag=False),
      joint_endpoint_assignment=assignment,status='GEOMETRY_ONLY',obligations=['actual relay allocation and equalization','strict bind','exact K22 relay check','GEN safety','M8+PG trial GRT','TT/FF STA','die IR-drop'])
    assert rows and all(found.values()), 'no actual endpoint approach for one or more D2D words'
    (L/f'corridor_{apron}.json').write_text(json.dumps(d,indent=2))
    print(json.dumps(dict(apron=apron,channel=d['actual_channel_um'],rows=len(rows),sites=sum(len(r['sites']) for r in rows),endpoints={p:len(v) for p,v in found.items()},portrait=portrait)))
    raise SystemExit(0)
K._relays=report
K.build(kv_wq_mirror=True,split=True,host_v14=True,host_north=True,host_trees=True,v143=True,reserve_native_astk=True)
