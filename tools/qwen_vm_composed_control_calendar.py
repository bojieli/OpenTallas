import pathlib,json,hashlib,collections,argparse
p=argparse.ArgumentParser();p.add_argument('--su',type=pathlib.Path,default=pathlib.Path('/tmp/qwen-vm-su-20261007/run/events.json'));p.add_argument('--me',type=pathlib.Path,default=pathlib.Path('/tmp/qwen-vm-native-evidence-20261007/physical/trace.json'));p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('/tmp/qwen-vm-composed-calendar-20261007'));a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
su=json.loads(a.su.read_text())['19'];me=json.loads(a.me.read_text());events=collections.defaultdict(lambda:dict(reads={},writes=[]))
for x in su:
 e=events[x['cycle']+5]
 for family,items in x['reads'].items():e['reads'][family.upper()]=items
 if x['writes']:e['writes']+= [dict(family='SU',seat=l,address=addr)for l,addr in x['writes']]
 if x['reducer'] is not None:e['writes'].append(dict(family='REDUCER',seat=0,address=x['reducer']))
for x in me['edges']:
 if not x['me_clk_en']:continue
 f=me['frames'][x['frame']];rm=int(f['xre'],16);wm=int(f['owe'],16)
 if not (rm or wm):continue
 e=events[x['cycle']+90]
 if rm:
  ra=int(f['xaddr'],16);e['reads']['VX']=[[i,(ra>>(24*i))&0xffffff]for i in range(2048)if rm>>i&1]
 if wm:
  wa=int(f['oaddr'],16);mask=int(f['omask'],16)
  for i in range(48):
   if wm>>i&1:
    for l in range(16):
     if mask>>(16*i+l)&1:e['writes'].append(dict(family='ME',seat=16*i+l,address=((wa>>(24*i))&0xffffff)*16+l))
frames=[];lookup={};timeline=[];conflicts=[];fold_peaks={str(n):dict(read_distinct_words_per_bank=0,write_distinct_words_per_bank=0,combined_distinct_words_per_bank=0)for n in (128,256)}
for cycle,e in sorted(events.items()):
 # Retain enabled seat addresses; merge only identical entire frames.
 key=json.dumps(e,sort_keys=True,separators=(',',':'))
 if key not in lookup:lookup[key]=len(frames);frames.append(e)
 timeline.append(dict(cycle=cycle,frame=lookup[key]))
 for n in (128,256):
  shift=n.bit_length()-1
  bank=lambda w:(w^(w>>shift))&(n-1)
  reads=collections.defaultdict(set);writes=collections.defaultdict(set)
  for seats in e['reads'].values():
   for _,addr in seats:reads[bank(addr>>4)].add(addr>>4)
  for w in e['writes']:writes[bank(w['address']>>4)].add(w['address']>>4)
  peaks=fold_peaks[str(n)];peaks['read_distinct_words_per_bank']=max(peaks['read_distinct_words_per_bank'],max(map(len,reads.values()),default=0));peaks['write_distinct_words_per_bank']=max(peaks['write_distinct_words_per_bank'],max(map(len,writes.values()),default=0));peaks['combined_distinct_words_per_bank']=max(peaks['combined_distinct_words_per_bank'],max((len(reads[b]|writes[b])for b in set(reads)|set(writes)),default=0))
  if any(w['family']=='REDUCER'for w in e['writes']):
   reducer=next(w for w in e['writes']if w['family']=='REDUCER');word=reducer['address']>>4;b=bank(word)
   conflicts.append(dict(cycle=cycle,banks=n,formula=f'(word ^ (word >> {shift})) & {n-1}',reducer_scalar=reducer['address'],reducer_word=word,reducer_lane=reducer['address']&15,reducer_bank=b,read_words_same_bank=sorted(reads[b]),same_word_read=word in reads[b],read_scalars_same_bank=sorted({addr for seats in e['reads'].values()for _,addr in seats if bank(addr>>4)==b}),enabled_read_seats=sum(len(v)for v in e['reads'].values())))
out=dict(scope='Source-pinned child control captures composed at observed native controller issue edges; no unobserved writer family is assigned zero as a production claim.',source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [a.su,a.me]},issue_edges=dict(SU=10,ME=95),native_capture_accept_edges=dict(SU=5,ME=5),frames=frames,edges=timeline)
(a.out/'calendar.json').write_text(json.dumps(out,separators=(',',':'))+'\n')
summary=dict(enabled_edges=len(timeline),unique_frames=len(frames),reducer_bank_witnesses=conflicts,fold_peaks=fold_peaks,read_window={f:[min(c for c,e in events.items()if f in e['reads']),max(c for c,e in events.items()if f in e['reads'])]for f in ['VA','VB','VC','VX']if any(f in e['reads']for e in events.values())},write_window={f:[min(c for c,e in events.items()if any(w['family']==f for w in e['writes'])),max(c for c,e in events.items()if any(w['family']==f for w in e['writes']))]for f in ['SU','ME','REDUCER']})
(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
assert len(conflicts)==2 and all(x['cycle']==160 and x['reducer_scalar']==16160 for x in conflicts)
