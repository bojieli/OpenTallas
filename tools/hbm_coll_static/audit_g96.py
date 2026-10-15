#!/usr/bin/env python3
"""Independent emitted-word/lifetime audit; never accepts scheduler PASS alone."""
import argparse,json,pathlib,collections,re
p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);p.add_argument('layout',type=pathlib.Path);a=p.parse_args()
v=json.loads((a.directory/'calendar.json').read_text());layout=json.loads(a.layout.read_text());f=layout['fields'];af=layout['ar_fields']
words={}
for line in (a.directory/'expanded_uops.jsonl').open():
 x=json.loads(line);k=(x['owner'],x['cycle']);assert k not in words;words[k]=int(x['word'],16)
def field(o,c,name):
 x=f[name];return (words.get((o,c),0)>>x['lsb'])&((1<<x['width'])-1)
def ar(o,c,name):
 x=af[name];bits=field(o,c,'ar_low')|(field(o,c,'ar_high')<<31)
 return (bits>>x['lsb'])&((1<<x['width'])-1)
checks=collections.Counter();loads=collections.defaultdict(list);qseen={}
for x in v['qroutes']:
 o,c,s,d=x['owner'],x['capture'],x['source'],x['sink']
 assert field(o,c,'capture_slot')>>s&1
 assert field(o,c+1,'sink_slot')>>d&1
 assert (field(o,c+1,'sink_select')>>(4*d))&15==s
 checks['qroute_word_checks']+=1
 key=(o,c,s)
 if key in qseen:assert qseen[key]==x['identity']
 qseen[key]=x['identity']
for x in v['loads']:
 o,c,t=x['owner'],x['cycle'],x['tag'];assert ar(o,c,'load_v')==1 and ar(o,c,'load_tag')==t
 q=int(o.split('q')[1]);rank=x['rank'];req=c-15
 assert field(o,req,'inj_rd')&1 and field(o,req,'inj_idx')&65535==q*16+t
 assert field(o,req,'inj_meta')&((1<<33)-1)==(1<<32)|(255<<24)|(rank<<16)|(q*16+t)
 loads[o].append((c,0,t,0));checks['native_loads']+=1
for x in v['arithmetic']:
 o=f'd{x["rank"]}q{x["q"]}';c=x['read'];t=x['tag']
 assert ar(o,c,'add_read')==1 and ar(o,c,'read_tag')==t
 assert ar(o,c+1,'add_issue')==1 and x['writeback']==c+9
 loads[o].append((c,1,t,c+10));checks['native_adds']+=1
for x in v['publications']:
 o,c=x['owner'],x['read'];tags=x['tags']
 assert ar(o,c,'pub_read')==1 and ar(o,c,'pub_tag_a')==tags[0]
 assert ar(o,c,'pub_bf16')==int(x['bf16']) and ar(o,c,'pub_tag_b')==tags[-1]
 assert ar(o,c+1,'pub_issue')==1 and ar(o,c,'pub_release')==int(x['release'])
 match=re.search(r'g(\d+).*q(\d+).*pair(\d+)',x['identity'])
 if x['bf16']:
  assert match
  g,q,pair=map(int,match.groups());src=g;index=g*32+q*8+pair
 else:src=int(o.split('q')[0][1:]);index=tags[0]
 assert ar(o,c,'pub_src')==src and ar(o,c,'pub_index')==index
 for t in tags:
  loads[o].append((c,2,t,0))
  if x['release']:loads[o].append((c+1,3,t,0))
 checks['native_publications']+=1
for o,events in loads.items():
 tags={}
 for c,kind,t,ready in sorted(events):
  if kind==0:assert t not in tags;tags[t]=c+1
  elif kind==1:assert t in tags and tags[t]<=c;tags[t]=ready
  elif kind==2:assert t in tags and tags[t]<=c
  else:assert t in tags;del tags[t]
 assert not tags
 checks['quarter_lifetime_audits']+=1
deliveries={}
for x in v['qroutes']:
 o=x['owner'];q=int(o.split('q')[1]);npt=3 if q==0 else 2
 if x['sink']!=npt:continue
 match=re.search(r'bf16.g(\d+).q(\d+).pair(\d+)',x['identity'])
 assert match
 g,lq,pair=map(int,match.groups());assert q==lq
 k=(o,g,q,pair)
 if k in deliveries:assert deliveries[k]==x['capture']
 deliveries[k]=x['capture']
assert len(deliveries)==96*4*12*8
checks['unique_indexed_BF16_deliveries']=len(deliveries)
for x in v['transport_hops']:
 o=f'd{x["src"]}q{x["q"]}';d=f'd{x["dst"]}q{x["q"]}';r=x['rail'];dr=x['dst_rail'];s=x['seq']
 for key,c in [('wr',x['write']),('rd',x['read'])]:
  assert field(o,c,'lk_'+key+'_v')>>r&1
  seq=((field(o,c-1,'lk_'+key+'_seq_high')>>(10*r))&1023)*64+((field(o,c-1,'lk_'+key+'_slot')>>(6*r))&63)
  assert seq==s<65536
 assert field(d,x['receive']-1,'lk_rx_expect')>>dr&1
 seq=((field(d,x['receive']-2,'lk_rx_seq_high')>>(10*dr))&1023)*64+((field(d,x['receive']-2,'lk_rx_slot')>>(6*dr))&63)
 assert seq==s
 checks['native_link_hops']+=1
by=collections.defaultdict(list)
for x in v['transport_hops']:by[(x['src'],x['q'],x['rail'])].append(x)
for link,events in by.items():
 last={}
 ordered=sorted(events,key=lambda x:x['read'])
 assert [x['write'] for x in ordered]==sorted(x['write'] for x in events)
 for ordinal,x in enumerate(ordered):
  assert x['seq']==ordinal and x['slot']==ordinal%64
  if x['slot'] in last:assert x['write']>=last[x['slot']]+4
  last[x['slot']]=x['read']
 checks['replay64_and_sequence_audits']+=1
for link,slots in v['endpoint_slots'].items():
 seq=0
 for x in slots:
  j=x['slot_ordinal'];assert x['accept']==17+(613*j)//487
  assert x['endpoint_read']==x['accept']-6 # pin-registered native TX5
  assert x['endpoint_rx_publish']==24+(613*(j+1)+486)//487-1
  if x['valid']:assert x['sequence']==seq;seq+=1
  else:assert x['sequence'] is None
 checks['actual_613_487_reserved_slots']+=len(slots)
result={'status':'PASS: independent actual V2 expanded-word, chronological tag/visibility, qslot, replay64/full-sequence and613/487 idle-slot audit',
        'checks':dict(checks),'cycles':v['cycles'],'ratio_to_immutable1325_9':v['cycles']/1325.9,
        'qualification':'candidate static schedule proof only; expanded program is not yet64row compressed, actual endpoint/FEC/physical/nativeSUjoin unqualified'}
(a.directory/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
