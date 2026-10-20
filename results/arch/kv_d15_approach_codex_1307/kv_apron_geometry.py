import os,sys,json
sys.path.insert(0,'tools/qwen_kv_die')
import kv_die as K
import kv_rly_std as RS
K.HOST_V14.update(on=True,north=True,trees=True);K.V143['on']=True
K._set_geometry(True,reserve_native_astk=True)
K._relays=lambda m:None # EXPLICIT geometry-only inspection before physical relay allocation; never gate/bind
rows=[]
for apron in (float(sys.argv[1]),):
 os.environ['OT_KV_D2D_APRON_UM']=str(apron)
 m=K._build(kv_wq_leaves=True,kv_wq_binary=True,kv_wq_leaf_s=True,kv_wq_head=False,kv_wq_wide=True,kv_wq_mirror=True,split=True)
 by={i.name:i for i in m['insts']};d=by['d2d_kv'];l=by.get('lnk')
 pts=K.d2d_view_ports()['att_tx_payload'][4]
 centre=(min(x for x,y in pts)+max(x for x,y in pts))/2
 fw,fh,_=RS.layout(548,RS.frame_rev('ks_kvs_attn__attn__tx_payload'))
 # output at middle of actual 548pin span, one relay halfheight below Southface plus21.6um gap.
 x=d.x+centre-fw;y=d.y-21.6-fh;out=(x+fw,y+fh/2)
 overlap=[]
 for i in m['insts']:
  if min(x+fw,i.x+i.w)>max(x,i.x)+.001 and min(y+fh,i.y+i.h)>max(y,i.y)+.001:overlap.append(i.name)
 far=max(abs(out[0]-(d.x+px))+abs(out[1]-(d.y+py)) for px,py in pts)
 rows.append(dict(apron_um=apron,die=m['die'],d2d=[d.x,d.y,d.w,d.h],link=([l.x,l.y,l.w,l.h] if l else None),nearby=[[i.name,i.x,i.y,i.w,i.h] for i in m['insts'] if abs(i.y-d.y)<800 and abs(i.x-d.x)<1600],candidate_relay=[x,y,fw,fh],candidate_endpoint_max_um=far,overlap=overlap,scope='geometry-only; no relays allocated, source-side hop and full bind outstanding'))
print(json.dumps(rows,indent=2));open('../apron_geometry_'+sys.argv[1]+'.json','w').write(json.dumps(rows,indent=2))
