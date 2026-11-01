import json,hashlib,collections
from pathlib import Path
root=Path('/srv/opentallas-scratch2/claude/codex-qc-programme-native-1131')
out=Path('/srv/opentallas-scratch2/claude/codex-qwen-images-1101/monitor_invariance1131');out.mkdir(exist_ok=True)
mask=(1<<457)-1
report={'scope':'Read-only actual native36-layer monitor payload comparison, no RTL/caller/calendar changes','ranks':[],'source_to_monitor':{'12':3,'13':3,'14':11,'15':10}}
rank_words=[]
for rank in range(8):
 path=root/f'rank{rank}/lowered/mu_table_input.json';m=json.loads(path.read_text())
 assert len(m['stages'])==36 and [s['stage'] for s in m['stages']]==list(range(1,37))
 refs={}; hashes={};bad=[];tail=[]; zeros=collections.Counter()
 for st in m['stages']:
  assert sorted(s['slice'] for s in st['slices'])==list(range(12))
  for sl in st['slices']:
   sid=sl['slice']; assert len(sl['prog_users'])==4
   for user,rs in enumerate(sl['prog_users']):
    pairs={r['addr']:int(r['payload_hex'],16) for r in rs}; assert set(pairs)==set(range(6))
    for pc in (3,10,11):
     pair=pairs[pc//2];word=(pair>>(512*(pc%2)))&mask
     key=(sid,user,pc)
     if key in refs and refs[key]!=word:bad.append((st['stage'],sid,user,pc))
     refs.setdefault(key,word)
 assert not bad,bad[:5]
 for sid in range(12):
  for user in range(4):
   xs,xa,silu=[refs[sid,user,pc] for pc in (3,11,10)]
   if not xa:zeros['XA_source_zero_nonowner']+=1
   for row,addr,payload in [(3816+2*user,6,xs|(xs<<512)),(3816+2*user+1,7,xa|(silu<<512))]:
    native=payload|(1<<1024)|(3<<1025)|(addr<<1027)
    tail.append(dict(slice=sid,user=user,physical_logical_row=row,local_pair_addr=addr,global_pair_addr=64*user+addr,global_instruction_indices=[128*user+2*addr,128*user+2*addr+1],payload_hex=f'{payload:0256x}',native_rom_word_hex=f'{native:0263x}'))
 summaries=[]
 for sid in range(12):
  summaries.append(dict(slice=sid,user0_words={str(pc):f'{refs[sid,0,pc]:0115x}' for pc in (3,10,11)},nonzero_source_pidx=[pc for pc in (3,10,11) if refs[sid,0,pc]],all36_layers_identical=True))
 # Inspect actual physical tail masks: all lane rows covering3816..4095 are zero.
 names=[root/f'rank{rank}/masks/table_s{s}_m{lane}.viamap.hex' for s in range(12) for lane in range(4)]
 free=True
 for p in names:
  rows=[int(t,16) for t in p.read_text().split()]
  assert len(rows)==512
  free=free and all(v==0 for v in rows[3816//8:])
 assert free
 digest=hashlib.sha256(''.join(f'{refs[k]:0115x}' for k in sorted(refs)).encode()).hexdigest()
 report['ranks'].append(dict(rank=rank,manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),checked_layers=36,checked_slice_user_source_words=len(refs)*36,all36_layers_identical=True,monitor_source_digest=digest,actual_physical_tail_3816_4095_all_zero=True,zero_source_summary=dict(zeros),slices=summaries))
 rank_words.append(refs)
 (out/f'rank{rank}_tail_candidate.json').write_text(json.dumps(dict(scope='SOURCE CANDIDATE ONLY, NOT INSTALLED',rows=tail),indent=2)+'\n')
assert all(r==rank_words[0] for r in rank_words)
report.update(all8_rank_monitor_sources_identical=True,status='PASS_INVARIANCE_AND_TAIL_CAPACITY_ONLY',existing_used_rows=3816,existing_tail_rows=280,candidate_tail_rows=8,candidate_used_rows=3824,candidate_free_rows=272,existing_stage_stride=106,uniform8pair_stride_rows=114,uniform8pair_total_rows=4104,existing_reads_per_window=88,candidate_reads_per_window=90,incremental_read_edges_per_window=2,incremental_occupied_time_ps_at833=1666,load_window_qualification='OPEN: actual start/last write/first use timing must be joined; not priced as hidden')
(out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['status'], 'all8same',report['all8_rank_monitor_sources_identical'],'rows',report['candidate_used_rows'])
