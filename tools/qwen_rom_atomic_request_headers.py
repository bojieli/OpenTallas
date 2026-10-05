#!/usr/bin/env python3
"""Request-header-only evidence from interleaved logs; original return gate FAIL."""
import argparse,gzip,json,re,hashlib
from pathlib import Path
from qwen_rom_source_observer_replay import replay,file_sha256
from qwen_rom_program_identity import ROOT,decoded,sha
from qwen_rom_kv_launch_readiness import FIELDS,instruction

HEAD=re.compile(rb'R (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)')
MAIN=re.compile(rb'(?m)^[BSDIWK] [^\n]*\n')

def request_profile(fields,reads,groups=6144):
 """Literal original IL8 KV loop, actual all-port requests including masked lanes."""
 if not fields['wsrc'] or fields['tiles']!=1 or fields['split']>11:raise ValueError('historical one-round source profile only')
 chunks=(fields['k']+(1<<fields['split'])-1)>>fields['split']
 edges=sorted({r[0] for r in reads})
 if len(edges)!=chunks*8 or len(reads)!=chunks*8*groups:raise ValueError('all source loop port requests required')
 order={edge:i for i,edge in enumerate(edges)};seen=set()
 for edge,tile,group,address in reads:
  g=tile*4+group
  if not 0<=group<4 or not 0<=g<groups or (edge,g) in seen:raise ValueError('distinct source request port identity')
  seen.add((edge,g));cycle=order[edge];k,j=divmod(cycle,8)
  want=(fields['wbase']+(g>>fields['split'])*fields['ts']+(g&((1<<fields['split'])-1))*fields['wcs']+k*fields['ks']+(j>>fields['jsh'])*fields['js'])&((1<<24)-1)
  if address!=want:raise ValueError('source address does not match accepted descriptor loop')
 return {'word_requests':len(reads),'first_source_request_edge':edges[0],'last_source_request_edge':edges[-1],'request_edges':edges,'response_payload_qualified':False,'effective_attention_mask_qualified':False}

def source_contract():
 cap=json.loads((ROOT/'results/rtl/qwen_rom_TP4_terminal_20261002/capture.json').read_text())
 header=(ROOT/'rtl/test/qwen_rom_runtime/observer/qwen_rom_observer.hpp').read_bytes()
 if sha(header)!='6c37db03c5fb524bd86a3b63621cdef2dc63e37bd626b6a5ea715d6b42245fcd':raise ValueError('frozen original header required')
 host=gzip.decompress((ROOT/'results/uarch/qwen_rom_source_read_deadlines_20261003/qwen_rom_rt_observed.cpp.gz').read_bytes())
 if sha(host)!='d42a775f630831d3f7640e1b439902f1d3ee07d1b92629375f090a5e4b93b6ad':raise ValueError('frozen actual host required')
 pool=decoded(cap['files']['source/rtl/test/qwen_runtime/qwen_rt_matvec.hpp'])
 if b'done_.wait(l, [&] { return left_ == 0; });' not in pool or b'pool.run(NT, [&](size_t i)' not in host:raise ValueError('blocking callback boundary required')
 if b' std::fprintf(file,"R %ld %zu %d %u %u %u",edge,stage,rank,tile,group,address);' not in header:raise ValueError('single-call atomic request header required')
 matvec=decoded(cap['files']['source/rtl/hdc/ot_hdc_matvec.sv'])
 if sha(matvec)!='a405904d794687047077208a7d3a8d2e1de88024303151e58b5909e093adec18':raise ValueError('frozen address producer required')
 for anchor in (b'cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;',b'cur <= base_k + ks_r;',b"if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur <= cur + js_r;",b'kv_addr[gi*AW +: AW] <= cur + ((gb + gi) >> split_r) * ts_r + ((gb + gi) & ((1 << split_r) - 1)) * wcs_r;'):
  if anchor not in matvec:raise ValueError('literal source address recurrence required')
 probe=json.loads((ROOT/'results/uarch/qwen_rom_L0_observer_format_failure_20261003/original-native-concurrency-FAIL-r1.json').read_text())
 if probe['header_sha256']!=sha(header) or probe['header_count']!=8192 or not probe['whole_atomic_headers_recovered'] or probe['DUT_or_provider_run']:raise ValueError('original-header concurrent recovery prerequisite')
 return {'host_sha256':sha(host),'header_sha256':sha(header),'blocking_pool_sha256':sha(pool),'address_producer_sha256':sha(matvec),'scope':'six request fields emitted by one stdio call; payload fragments excluded; native concurrent header recovery prerequisite'}

def extract(bundle,raw):
 contract=source_contract()
 heads=list(HEAD.finditer(raw))
 if len(heads)!=raw.count(b'R '):raise ValueError('every source request header must be parsed')
 mains=list(MAIN.finditer(raw))
 # Worker callbacks finish before main-thread commits/dispatch. Whole main lines
 # are independently checked by the existing descriptor/write/snapshot gate.
 clean=b''.join(m.group() for m in mains).decode()
 producer=replay(bundle,clean,layers=1,require_reads=False)
 current={};groups={};first={};phase=[]
 for m in mains:phase.append((m.start(),'main',m.group()))
 for m in heads:phase.append((m.start(),'read',tuple(map(int,m.groups()))))
 for _,kind,value in sorted(phase,key=lambda e:e[0]):
  if kind=='main':
   a=value.split()
   if a[0]==b'I' and a[7]==b'1':
    rank=int(a[3]);fields=dict(zip([n for n,_ in FIELDS],map(int,a[8:])))
    current[rank]={'edge':int(a[1]),'pc':int(a[5])+int(a[6]),'fields':fields,'ib379':instruction(fields)}
   continue
  edge,layer,rank,tile,group,address=value
  e=current.get(rank)
  if layer!=0 or not 0<=rank<4 or e is None or not e['fields']['wsrc'] or edge<e['edge']:raise ValueError('actual request without accepted source KV consumer')
  key=(rank,e['pc']);groups.setdefault(key,[]).append((edge,tile,group,address))
  for lane in range(16):first.setdefault((rank,address*16+lane),{'edge':edge,'consumer_pc':e['pc'],'word_address':address,'tile':tile,'group':group})
 requests={}
 for rank in range(4):
  life=producer['states'][f'L0/die{rank}']['source_lifetimes']
  for e in life['KV_consumer_accepts']:
   key=(rank,e['pc']);reads=groups.pop(key,[])
   if not reads or min(r[0] for r in reads)<e['edge']:raise ValueError('source consumer request coverage')
   requests[f'die{rank}/PC{e["pc"]}']=dict(request_profile(e['fields'],reads),accepted_issue_edge=e['edge'],accepted_ib379=e['ib379'])
  deadlines=[]
  for w in life['committed_writes']:
   read=first.get((rank,w['address']))
   if read is None or read['edge']<=w['edge']:raise ValueError('actual request must follow producer write commit')
   deadlines.append(dict(read,address=w['address'],producer_pc=w['pc'],write_edge=w['edge'],source_edge_slack=read['edge']-w['edge']))
  life['source_request_deadlines']=deadlines
 if groups:raise ValueError('unexpected accepted request consumer')
 return {'status':'PASS_SOURCE_REQUEST_HEADERS_AND_PRODUCER_STATE_ONLY','original_16lane_return_gate':'FAIL_INTERLEAVED_RECORDS_PRESERVED','source_contract':contract,'source_program_states':producer['states'],'source_request_profiles':requests,'raw_sha256':sha(raw),'source_provenance_independently_qualified':False,'returned_payload_qualified':False,'provider_ACK_drained_retired':None,'current_source_physical_transfer':False,'provider_PHY_rate_credit':False,'scope':'historical TP4pos0 L0 only; all host requests include masked lanes, not a future service deadline or lifetime release'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 b=json.loads(gzip.decompress(a.bundle.read_bytes()));r=extract(b,a.raw.read_bytes())
 with a.out.open('x') as f:json.dump(r,f,sort_keys=True,indent=2);f.write('\n')

if __name__=='__main__':main()
