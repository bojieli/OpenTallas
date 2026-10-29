#!/usr/bin/env python3
"""Emit native217-bit FUSED jobs from real HGI-1R records; fail closed without current4-role calendar."""
import argparse,hashlib,json,sys,re
from pathlib import Path
FIELDS=[('post',0,1),('nm1',1,4),('A',5,19),('B',24,19),('C',43,19),('O',62,19),('rsA',81,24),('rsB',105,24),('rsC',129,24),('rsO',153,24),('rgap',177,8),('eps',185,32)]
def pack(f):
 w=0
 for k,l,b in FIELDS:
  if not 0<=f[k]<1<<b:raise ValueError(f'{k} outside unsigned{b}: {f[k]}')
  w|=f[k]<<l
 return w

def main():
 p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--compiler-tools',type=Path,required=True);p.add_argument('--calendar',type=Path);p.add_argument('--calendar-rgap',action='store_true',help='accept explicit calendar PRE row-gap increases only');p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 if (a.out/'programme.mem').exists():p.error('output already contains executable programme; use a fresh directory')
 sys.path[:0]=[str(a.compiler_tools),str(a.compiler_tools/'hbm_next')]
 import isa_rows as IR
 import fused_phase_check as FC
 raw=a.image.read_bytes();sha=hashlib.sha256(raw).hexdigest();off=0;jobs=[];rejected=[]
 while off<len(raw):
  start=off;r,rx,off=IR.decode_one(raw,off)
  if r.unit!='FUSED' or r.op not in FC.FUSED_OPS:continue
  try:
   if FC.check_fused(r,rx):raise ValueError(str(FC.check_fused(r,rx)))
   if rx and (rx.rsel or rx.emask or rx.slot0):raise ValueError('dynamic row selection')
   n=rx.n if rx else 1
   if not 1<=n<=8:raise ValueError('NMAX8 exceeded')
   f={'post':int(r.op=='HC_POST'),'nm1':n-1,'rgap':rx.rgap if rx else 0,'eps':r.imm_a&0xffffffff}
   sizes=dict(zip('ABCO',[5120,20480,20,20480] if f['post'] else [20480,5120,4,5120]))
   for k in 'ABCO':
    d=r.desc[k]
    if any(getattr(d,x,0) for x in ['lstride','dyn_sel','n_sel','l1stride','ibcast','indexed']):raise ValueError(k+' unresolved address mode')
    span=d.n if d.m<=1 else (d.m-1)*d.stride+d.n
    if d.istride not in (0,1) or span!=sizes[k] or (d.m>1 and d.stride!=d.n):raise ValueError(k+' incompatible native5120 shape')
    f[k]=d.base;f['rs'+k]=rx.rs.get(k,0) if rx else 0
   w=pack(f);assert all((w>>l)&((1<<b)-1)==f[k] for k,l,b in FIELDS)
   jobs.append(dict(image_offset=start,op=r.op,fields=f,job217=f'{w:055x}',formats={k:r.desc[k].fmt for k in 'ABCO'}))
  except (ValueError,KeyError) as e:rejected.append(dict(image_offset=start,op=r.op,reason=str(e)))
 missing=[];c={}
 if not a.calendar or not a.calendar.exists():missing.append('current4role_native_calendar: source plan SHA, image offsets/launch/deadline edges, boot/START offsets, WSC/PK5/PB5, root ingress/status cycles')
 else:
  c=json.loads(a.calendar.read_text());required=['source_plan_commit','programme_image_sha256','roles','boot_release_offsets','root_config','root_ingress_cycles','root_status_return_cycles','controller_fetch_cycles','controller_start_cycles','controller_status_check_cycles','provider_start_cycle','provider_preload_complete_cycle','provider_cfg_commit_cycle','pad_warm_cycles','records'];missing.extend(k for k in required if k not in c)
  if not missing:
   if not re.fullmatch('[0-9a-f]{40}',c['source_plan_commit']):missing.append('exact40hex source plan SHA')
   if c['programme_image_sha256']!=sha:missing.append('image SHA mismatch')
   if c['roles']!={'NWq0':'SW','NEq0':'SE','NWq1':'NW','NEq1':'NE'}:missing.append('selected4role mapping')
   if set(c['boot_release_offsets'])!={'SW','SE','NW','NE','root'}:missing.append('all5 boot release offsets')
   cfg=c['root_config']
   if set(cfg)!={'wsc','pk5','pb5'} or not 0<=cfg.get('wsc',-1)<=255 or not 0<=cfg.get('pk5',-1)<=32 or cfg.get('pb5') not in (0,1):missing.append('actual root straps')
   if c['controller_fetch_cycles']!=2 or c['controller_start_cycles']!=1 or c['controller_status_check_cycles']!=2:missing.append('actual controller fetch2/start1/statuscheck2 contract')
   if any(not isinstance(c[k],int) or c[k]<0 for k in ['root_ingress_cycles','root_status_return_cycles']):missing.append('actual nonnegative root path cycles')
 if c and not missing:
  if c['pad_warm_cycles']<32 or c['provider_start_cycle']<max(c['boot_release_offsets'].values())+6+c['pad_warm_cycles']:missing.append('START after all delivered resets+6 and actual pad warm')
  if not c['provider_preload_complete_cycle']<c['provider_cfg_commit_cycle']<c['provider_start_cycle']:missing.append('real preload/commit/START order')
 if not jobs:missing.append('no native FUSED jobs in source image')
 if len(jobs)>256:missing.append('finite provider256entry capacity exceeded')
 if rejected:missing.append('native field restrictions rejected records')
 receipt=dict(schema='opentallas.native_fused_job217.v1',image_sha256=sha,jobs=jobs,rejected=rejected,missing=missing,status='MISSING',executable_programme_emitted=False,whole_kernel_qualified=False)
 if not missing:
  sched={x['image_offset']:x for x in c['records']};words=[];prev=-1
  if len(sched)!=len(c['records']) or set(sched)!={j['image_offset'] for j in jobs}:missing.append('one scheduled entry per exact native record offset')
  for j in jobs:
   if j['image_offset'] not in sched:continue
   t=sched[j['image_offset']]
   override=t.get('rgap_override')
   if override:
    v=override.get('value'); original=j['fields']['rgap']
    if (not a.calendar_rgap or j['op']=='HC_POST' or j['fields']['nm1']+1<=4
        or not isinstance(v,int) or isinstance(v,bool) or not original<=v<=255
        or override.get('original')!=original or override.get('source_job217')!=j['job217']
        or override.get('added_service_cycles')!=(v-original)*j['fields']['nm1']):
     missing.append('invalid/unaccepted calendar rgap override at '+str(j['image_offset']))
    else:
     j['source_job217']=j['job217'];j['fields']['rgap']=v;j['job217']=f'{pack(j["fields"]):055x}'
   launch=t['launch_cycle'];deadline=t['completion_cycle']
   if t.get('root_capture_cycle')!=launch+1+c['root_ingress_cycles'] or t.get('root_done_cycle',-1)+2+c['root_status_return_cycles']!=deadline:missing.append('explicit dispatch1/statuscheck2/rootpath cycle accounting at '+str(j['image_offset']))
   if not 0<=launch<deadline<1<<32 or launch<=prev or launch<c['provider_start_cycle']+3:missing.append('ordered bounded launch/deadline at '+str(j['image_offset']))
   prev=deadline+3;words.append(((deadline-c['provider_start_cycle'])<<249)|((launch-c['provider_start_cycle'])<<217)|int(j['job217'],16))
  if not missing:
   (a.out/'programme.mem').write_text(''.join(f'{w:071x}\n' for w in words));receipt.update(status='COMPILED_OPT_IN',executable_programme_emitted=True,entries=len(words),entry_bits=281,calendar=c)
 (a.out/'jobs.json').write_text(json.dumps(receipt,indent=2)+'\n');(a.out/'MISSING.txt').write_text('\n'.join(missing)+'\n' if missing else '')
 print(json.dumps(dict(status=receipt['status'],jobs=len(jobs),rejected=len(rejected),missing=missing,executable_programme_emitted=receipt['executable_programme_emitted'])))
 return 2 if missing else 0
if __name__=='__main__':raise SystemExit(main())
