"""PLAN ONLY: eight source leaves -> eight native VM banks, no target/dates installed.
Run with TOK load_provider directory as argv1 and output JSON path as argv2.
Only full64sector/512word contiguous U32 chunks; scalar/coalesced fallback remains
necessary for edges, strides, formats and runtime input. Reordering is confined
inside one resolved LOAD with unique destination words, before its commit fence.
"""
import sys,json
sys.path.insert(0,sys.argv[1])
from window_map import decode,encode

def schedule(start,destsector,mutant=False):
 assert start%64==0
 d=decode(start);qbit=d['pc']&16;j=d['slot']>>2;cycles=[]
 for group in range(2):
  for phase in range(4):
   words=[]
   for leaf in range(8):
    beat=phase if mutant else(phase+(leaf>>1))%4
    pc=qbit|(group<<3)|leaf;s=encode(d['row'],d['col'],pc,(j<<2)|beat)
    v=destsector+s-start
    words.append(dict(source_sector=s,source_leaf=leaf,source_group=group,source_slot=(j<<2)|beat,dest_sector=v,dest_bank=v&7,dest_quad=v>>13&3,count=8))
   assert len({w['source_leaf']for w in words})==8
   assert len({w['dest_bank']for w in words})==8,'native VM bank collision'
   cycles.append(words)
 seen=[w['source_sector']for c in cycles for w in c]
 assert sorted(seen)==list(range(start,start+64))
 assert sorted(w['dest_sector']for c in cycles for w in c)==list(range(destsector,destsector+64))
 return cycles
checks=0
for start in range(0,1<<17,64):
 for offset in range(8):schedule(start,8000+offset);checks+=1
for start in(0x100000>>5,703124928):
 if start+64<=703125000:
  for offset in range(8):schedule(start,8190+offset);checks+=1
try:schedule(0,0,True)
except AssertionError:mutant='caught_samebeat_allleaves_VMbank_collision'
else:raise AssertionError('collision mutant escaped')
result=dict(status='PLAN_ONLY_UNSELECTED_VECTOR_ROUTE_NO_PROVIDER_RATE_ADOPTION',checked_full_chunks=checks,words_per_chunk=512,sector_commands=64,issue_dates_per_full_chunk=8,output_VMbytes_per_candidate_date=256,source_ports=8,VMbank_ports=8,added_register_cycles='unselected',mutant=mutant,sample=schedule(0,0),holds=['real dated vector counter/dispatch producer','actual owned window epoch and indexed resolver','destination vector route/clock/plan/lot/833ps closure','all partial chunks and nonunit strides preserve fallback','source currently stack2 only','no blind throughput extension to entire programme'])
open(sys.argv[2],'w').write(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('sample','holds')}))
