import argparse,pathlib,json,hashlib,gzip
p=argparse.ArgumentParser(description="Read-only source-bound historical producer trace; never a static target timing proof")
p.add_argument('--actual',type=pathlib.Path,required=True);p.add_argument('--program',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True)
a=p.parse_args();root=a.actual;program=a.program;out=a.out
ranks={}
for rank in range(8):
 p=program/f'die{rank}/program.hex';words=[x.strip().lower() for x in p.read_text().splitlines() if x.strip()]
 witness=root/f'rank{rank}_accepted_actual_words.txt';accepted=[]
 for line in witness.read_text().splitlines():
  pc,unit,edge,end,word=line.split();pc,unit,edge,end=map(int,(pc,unit,edge,end));
  if pc>=len(words) or int(word,16)!=int(words[pc],16) or (int(word,16)&3)!=unit:raise ValueError('accepted instruction differs from actual loaded program at PC'+str(pc))
  accepted.append({'pc':pc,'unit':unit,'accepted_edge':edge,'end':end,'instruction_sha256':hashlib.sha256(word.encode()).hexdigest()})
 if [o['pc'] for o in accepted]!=list(range(len(words))):raise ValueError('accepted instruction coverage incomplete')
 commits=root/f'rank{rank}_operation_commits.txt';selected=[];counts={}
 for line in commits.read_text().splitlines():
  pc,address,value,edge,port=line.split();pc,address,edge=map(int,(pc,address,edge));counts.setdefault(pc,{'count':0,'first_edge':edge,'last_edge':edge});counts[pc]['count']+=1;counts[pc]['last_edge']=edge
  if pc in (11,15,19,23):selected.append({'pc':pc,'address':address,'value':value,'edge':edge,'port':port})
 ranks[str(rank)]={'program_path':str(p),'program_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'witness_path':str(witness),'witness_sha256':hashlib.sha256(witness.read_bytes()).hexdigest(),'commits_path':str(commits),'commits_sha256':hashlib.sha256(commits.read_bytes()).hexdigest(),'accepted':accepted,'effects_summary':counts,'selected_producer_writes':selected}
report={'scope':'HISTORICAL_LV6_FUNCTIONAL_TRACE_DYNAMIC_HANDSHAKE_CPP_VM','static_target_schedule_qualified':False,'timing_transport_qualified':False,'source_program_words_matched_all_ranks':True,'actual_directory':str(root),'ranks':ranks}
with gzip.open(out,'wt')as f:json.dump(report,f,sort_keys=True)
print(out)
