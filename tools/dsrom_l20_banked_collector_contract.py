#!/usr/bin/env python3
"""Source-only banked collector sizing and existing golden saturation witnesses.
Only selected arithmetic AST functions execute. No golden model constructor,
checkpoint/config reads, RTL elaboration, simulation or physical tools.
"""
import argparse,ast,hashlib,json,math,re,struct,subprocess
from fractions import Fraction
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
REAL='4e38326d6f361bc85e660f48c59c355e2bb95274'
PRIOR='4966b786975abda4d1af209691f470e50d00f5d1'
PINS={}
def raw(rev,path):
 b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
 PINS[rev+':'+path]={'commit':rev,'path':path,'sha256':hashlib.sha256(b).hexdigest()}
 return b

def record(rev,path):return json.loads(raw(rev,path))
def emit(path,obj):
 b=(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
 if path.exists() and path.read_bytes()!=b:raise SystemExit('Immutable output differs: '+str(path))
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
def cite(path,needle):
 lines=raw(REAL,path).decode().splitlines();matches=[{'line':i,'text':s.strip()} for i,s in enumerate(lines,1) if needle in s]
 assert matches,(path,needle)
 return {'pin':REAL+':'+path,'matches':matches}
def p2(e):return Fraction(2)**e

def fvalue(key):
 mag=key&0x7fffffff;e=mag>>23;m=mag&0x7fffff
 assert e!=255
 value=Fraction(m if e==0 else (1<<23)+m)*p2(-149 if e==0 else e-150)
 return -value if key>>31 else value

def source_scale(amax):
 # Pinned S3 integer comparisons, finite input path. x magnitude as Fraction.
 amax=max(amax,Fraction(6,512));key=struct.unpack('>I',struct.pack('>f',float(amax)))[0]
 ea=((key>>23)&255)-127;ma=(1<<23)|(key&0x7fffff)
 if key<0x3dc00000:
  n=1+sum(amax>Fraction(3*(2*j+1),512) or (amax==Fraction(3*(2*j+1),512) and j%2==1) for j in range(1,8));return n,-9
 if key&(1<<22):
  n=8+sum(ma>3*(17+2*j)*(1<<18) or (ma==3*(17+2*j)*(1<<18) and j%2==1) for j in range(3));return n,ea-5
 n=11+sum(ma>3*(17+2*j)*(1<<17) or (ma==3*(17+2*j)*(1<<17) and j%2==1) for j in range(3,8));return n,ea-6

def independent_scale(amax):
 # Exact quotient nearest-even on extended E4M3 grid, THEN existing finite cap.
 q=max(amax,Fraction(6,512))/6
 e=q.numerator.bit_length()-q.denominator.bit_length()
 if q<p2(e):e-=1
 choices=[(Fraction(n,512),n%2) for n in range(1,8)]
 for qs in range(max(-9,e-4),max(-9,e-2)+1):choices.extend((n*p2(qs),n%2) for n in range(8,17))
 return min(min(choices,key=lambda z:(abs(q-z[0]),z[1]))[0],Fraction(448))

def qdq_model(keys,repair):
 assert len(keys)==32
 codes=[];scales=[];scale_codes=[];out=[];unbounded=[]
 for block in range(2):
  ks=keys[16*block:16*block+16];xs=[fvalue(k) for k in ks];amax=max(abs(x) for x in xs)
  n,qs=source_scale(amax);unbounded.append((n,qs));s=n*p2(qs)
  if repair and s>448:n,qs,s=14,5,Fraction(448)
  if repair:assert s==independent_scale(amax)
  scales.append(s)
  pn,pq=n,qs
  if pn==16:pn=8;pq+=1
  packed=pn if pq==-9 and pn<8 else ((pq+10)<<3)|(pn-8)
  scale_codes.append(packed if 1<=packed<=126 else None)
  for key,x in zip(ks,xs):
   a=abs(x);mid=[Fraction(k,4)*s for k in [1,3,5,7,10,14,20]]
   code=sum(a>t or (a==t and j%2==1) for j,t in enumerate(mid))
   sign=bool(key>>31) and a!=0;codes.append(code|(8 if sign else 0))
   y=Fraction([0,1,2,3,4,6,8,12][code],2)*s
   if y==0:bits=0x8000 if sign else 0
   else:
    try:bits=struct.unpack('>I',struct.pack('>f',float(-y if sign else y)))[0]>>16
    except OverflowError:bits=0xff80 if sign else 0x7f80
   out.append(bits)
 return {'codes':codes,'scales':scales,'scale_codes':scale_codes,'BF16':out,'source_n_qs':unbounded}

def golden_functions():
 env={'np':np};extracted=[]
 for path,names,constants in [('tools/hdc_golden.py',['bits','from_bits','to_bf16'],['F']),('tools/hdc_golden_v41.py',['_round_grid','_e4m3_round','qdq_fp4_e4m3'],['FP4_MAX','FP4_AMAX_FLOOR_E4M3','E2M1_VALUES','E2M1_MIDPOINTS'])]:
  tree=ast.parse(raw(REAL,path).decode());nodes=[]
  for n in tree.body:
   if isinstance(n,ast.FunctionDef) and n.name in names:nodes.append(n)
   elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets):nodes.append(n)
  assert {n.name for n in nodes if isinstance(n,ast.FunctionDef)}==set(names)
  exec(compile(ast.Module(body=nodes,type_ignores=[]),path,'exec'),env)
  extracted.extend({'file':path,'name':n.name if isinstance(n,ast.FunctionDef) else n.targets[0].id,'kind':'function' if isinstance(n,ast.FunctionDef) else 'source_constant','line':n.lineno,'end_line':n.end_lineno} for n in nodes)
 return env,extracted

def saturation_witnesses():
 env,functions=golden_functions();vectors=[]
 def add(name,keys):vectors.append((name,keys))
 for x in [2688.,2784.,3072.,6144.]:
  key=struct.unpack('>I',struct.pack('>f',x))[0]
  for delta in [-1,0,1]:add(f'finite_{int(x)}_ULP{delta:+}',[key+delta]*32)
 # Scale clamp must precede codes: max just past2784 plus .25*448 ties.
 for delta in [-1,0,1]:
  small=struct.unpack('>I',struct.pack('>f',112.))[0]+delta
  add(f'prethreshold_112_ULP{delta:+}',[0x452e0001]+[small]*15+[0xc52e0001]+[small|0x80000000]*15)
 add('negative_zero_and_tiny',[0x80000000,0x80000001,0x00000000,0x00000001]*8)
 add('largest_finite',[0x7f7fffff]*16+[0xff7fffff]*16)
 # Cover every finite exponent, signs, low mantissa, midpoint bits and max.
 for e in range(255):
  for m in [0,1,0x3fffff,0x400000,0x7fffff]:
   k=(e<<23)|m
   if k>=0x7f800000:continue
   add(f'finite_exp{e}_mant{m:x}',[k]*(16)+[(k|0x80000000)]*16)
 # All scale-grid midpoint ties and adjacent binary32 keys.
 for qs in range(-9,124):
  for n in range(8,16):
   try:k=struct.unpack('>I',struct.pack('>f',float(3*(2*n+1)*p2(qs))))[0]
   except OverflowError:continue
   if k<0x7f800000:
    for delta in [-1,0,1]:add(f'grid_q{qs}_n{n}_ULP{delta:+}',[k+delta]*32)
 failures=0;named=[];digest=hashlib.sha256()
 for name,keys in vectors:
  x=np.array(keys,dtype=np.uint32).view(np.float32)
  with np.errstate(all='ignore'):g=env['qdq_fp4_e4m3'](x,16).view(np.uint32)>>16
  fixed=qdq_model(keys,True);legacy=qdq_model(keys,False)
  assert fixed['BF16']==[int(v) for v in g],name
  mismatch=legacy['BF16']!=fixed['BF16'];failures+=mismatch
  digest.update(bytes.fromhex(''.join(f'{v:04x}' for v in fixed['BF16'])))
  if not name.startswith(('finite_exp','grid_')):
   named.append({'name':name,'input_binary32_hex':[f'{k:08x}' for k in keys],
    'golden_BF16_hex':[f'{int(k):04x}' for k in g],'retained_source_BF16_hex':[f'{k:04x}' for k in legacy['BF16']],
    'retained_source_n_qs':legacy['source_n_qs'],'capped_scales':[str(s) for s in fixed['scales']],
    'expected_direct_code_nibbles':fixed['codes'],'expected_scale_byte_hex':[f'{v:02x}' for v in fixed['scale_codes']],'expected_code_port128_hex':''.join(f'{v:x}' for v in reversed(fixed['codes'])),'expected_scale_port16_hex':''.join(f'{v:02x}' for v in reversed(fixed['scale_codes'])),'retained_source_fault':False,'source_defect':mismatch})
 nonfinite=[]
 for label,k in [('positive_inf',0x7f800000),('negative_inf',0xff800000),('quiet_nan',0x7fc00001),('signaling_nan',0x7f800001)]:
  x=np.array([k]+[0]*15+[0]*16,dtype=np.uint32).view(np.float32)
  with np.errstate(all='ignore'):g=env['qdq_fp4_e4m3'](x,16)
  nonfinite.append({'name':label,'input_bits':f'{k:08x}','golden_nonfinite_elements':int(np.count_nonzero(~np.isfinite(g))),
    'original_source_fault':True,'publication':'Reject nonfinite block/row under retained fault; preserve accepted-intent recovery fence. No admission of NaN/Inf rawpacked data.',
    'scope':'Fault/protocol case separate from finite saturation equality; no numerical policy inferred from NaN payload bits.'})
 return {'verdict':'PASS_FINITE_CAPPED_SCALE_MODEL_VS_ACTUAL_PINNED_GOLDEN_AND_FRACTION_ORACLE',
  'actual_golden_AST_functions':functions,'finite_vectors':len(vectors),'finite_elements':32*len(vectors),'retained_source_mismatch_vectors':failures,'output_digest':digest.hexdigest(),
  'named_witnesses':named,'nonfinite_witnesses':nonfinite,
  'full_finite_domain_argument':'For any finite binary32 block, amax/6 is finite infloat64. Existing golden chooses extended-grid RNE thenmin448. S3 exact RNE decision capped to n14/qs5 gives thatsame scale. S4 thresholds and S5code/sign fromthatscale yield identical nearest-even code for every finite element; result magnitudes<=2688 andexact BF16. Tests span every finite exponent/sign plus scale-boundary ties/ULPs; not exhaustive2^32vectors or RTL qualification.',
  'nonfinite_repair_scope':'Guard thefinitecap with retained nonfinite flag; preserve original invalid-row fault/data path, never publish it. Golden NaN/Inf cases are separatefault witnesses, not finitequantizationexactness claims.',
  'required_source_repair':'At S3 before S4 thresholds, clamp the ROUNDED scale to448 (n14,qs5). Use same repaired n/qs for S4 thresholds, S5codes, S6BF16 anddirectpackedscale7e. Sideband-only clamp is incorrect.',
  'classification':'CLASS_A_EXISTING_GOLDEN_CORRECTNESS_REPAIR; no new quality contract or unreachable-amax assumption.',
  'prior_records_preserved':'1fb/4966 finite-domain gate requiring inputbound orusercontract was based on missinggolden binding; superseded only bythis additive record. Failed originals intact.'}


def baseline_quantizer_bench(witness):
 # Original quantizer only. Expected vectors are assertions, never injected
 # quantized results or a substitute packed producer. No repairedRTL exists.
 lines=['`timescale 1ns/1ps','// PREPARED ONLY: unchanged source negative saturation witness.',
 'module tb_l20_qdq4_existing_golden;',
 'reg clk=0,rst_n=0,v=0; reg [1023:0] x=0; wire vo,fault;wire [511:0] y;integer differences=0;',
 'always #0.5 clk=~clk;',
 'ot_hdc_fp4qdq dut(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.vo(vo),.y(y),.fault(fault));',
 'task automatic send(input [1023:0] values);begin @(negedge clk);x=values;v=1;@(negedge clk);v=0;end endtask',
 'task automatic wait_result;integer n;begin n=0;while(!vo && n<16)begin @(negedge clk);n=n+1;end if(!vo)$fatal(1,"quantizer latency timeout");end endtask',
 'task automatic finite_case(input [1023:0] values,input [511:0] original_expected,input [511:0] golden_expected,input string name);',
 'begin send(values);wait_result;if(fault || y!==original_expected)$fatal(1,"retained source transcription mismatch %s",name);',
 'if(y!==golden_expected)begin differences=differences+1;$display("EXPECTED_RETAINED_SATURATION_DEFECT %s",name);end end endtask',
 'task automatic nonfinite_case(input [31:0] value);begin send({992\'d0,value});wait_result;if(!fault)$fatal(1,"retained nonfinite fault missing");end endtask',
 'initial begin repeat(4)@(negedge clk);rst_n=1;']
 for case in witness['named_witnesses']:
  xv=''.join(reversed(case['input_binary32_hex']));old=''.join(reversed(case['retained_source_BF16_hex']));gold=''.join(reversed(case['golden_BF16_hex']))
  lines.append(f'finite_case(1024\'h{xv},512\'h{old},512\'h{gold},"{case["name"]}");')
 for case in witness['nonfinite_witnesses']:lines.append(f'nonfinite_case(32\'h{case["input_bits"]});')
 lines+=['if(differences==0)$fatal(1,"expected original finite saturation defect absent");',
 '$display("BASELINE_DEFECTS_REPRODUCED_NOT_CORRECTED_OR_PACKED_PRODUCER_QUALIFICATION");$finish;end',
 'initial begin repeat(5000)@(posedge clk);$fatal(1,"bounded fixture timeout");end endmodule']
 return '\n'.join(lines)+'\n'

def min_channel(wires,pdn=0):
 lo,hi=0.,2000.
 for _ in range(64):
  m=(lo+hi)/2;tracks=math.floor(m/.036*.5+1e-9)+math.floor(m/.048*.5+1e-9)
  if tracks>=wires:hi=m
  else:lo=m
 return math.ceil(hi/.216)*.216

def bank_sim(rows,ready_pause=0):
 # Five finite sources: local,3peers,own. One skid each, one 1W/bank.
 # Rows identify rank, not any activation/payload. Credit returned on commit.
 streams=[list(x) for x in rows];fifo=[None]*5;rr=[0]*4;pipeline=[];stored={};trace=[];accepted={};max_occ=0
 for t in range(3000):
  commits=[z for z in pipeline if z[0]==t];pipeline=[z for z in pipeline if z[0]!=t]
  for due,src,rank,at in commits:
   assert rank not in stored;stored[rank]=t;trace.append({'event':'committed','cycle':t,'source':src,'rank':rank,'bank':rank%4,'address':rank//4,'accepted':at})
  # Reserved registered write grant -> macro write nextedge. One perbank.
  if t>=ready_pause:
   for b in range(4):
    for distance in range(5):
     s=(rr[b]+distance)%5
     if fifo[s] is not None and fifo[s][0]%4==b:
      rank,at=fifo[s];fifo[s]=None;rr[b]=(s+1)%5;pipeline.append((t+1,s,rank,at));break
  # Sourceaccept atedge, cannot be serviced in thissameedge model.
  for s in range(5):
   if fifo[s] is None and streams[s]:
    rank=streams[s].pop(0);assert rank not in accepted;accepted[rank]=t;fifo[s]=(rank,t)
  max_occ=max(max_occ,sum(x is not None for x in fifo)+len(pipeline))
  if not any(streams) and not any(x is not None for x in fifo) and not pipeline:
   return {'cycles':t+1,'committed_rows':len(stored),'max_packet_reservations':max_occ,'max_accept_to_commit_cycles':max(stored[k]-accepted[k] for k in stored),'trace':trace}
 raise AssertionError('finite collector failed todrain')


def replay_sim(stalls=None, demand=None):
 # Credit/valid use old state; neither new SRAM return nor same-edge pop is
 # available to another consumer/request before the following edge.
 stalls=set(stalls or []);demand=set(demand) if demand is not None else None
 buffers=[];pending=None;issued=0;consumed=[];max_occ=0;misses=[]
 for t in range(2000):
  old_used=len(buffers)+(pending is not None)
  consume=(t in demand if demand is not None else t not in stalls)
  if consume and buffers:
   group=buffers.pop(0);consumed.extend(range(4*group,4*group+4))
  elif demand is not None and t in demand:misses.append(t)
  if pending and pending[0]==t:buffers.append(pending[1]);pending=None
  if issued<128 and old_used<2:
   assert pending is None
   pending=(t+1,issued);issued+=1
  max_occ=max(max_occ,len(buffers)+(pending is not None))
  if len(consumed)==512:
   assert consumed==list(range(512)) and not misses,misses
   return {'cycles':t+1,'SRAM_read_edges':128,'rank_order_sha256':hashlib.sha256(bytes(k%256 for k in consumed)).hexdigest(),'max_groups_reserved':max_occ,'ordered_all512':True,'demand_misses':misses}
 raise AssertionError('replay didnotdrain')


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--witness-output',type=Path,required=True);ap.add_argument('--prepare',type=Path,required=True);a=ap.parse_args()
 prev=record(PRIOR,'results/uarch/dsrom_l20_connection_prepreview_20261002/model.json')
 old=record('e474925e4b8e5f07f41001e6efc40909fdc0a48e','results/uarch/dsrom_l20_mandatory_service_fixture_20261002/model.json')
 fp=record(REAL,'results/floorplan/v41_pack_refit_w18_e8p5.json')
 service='rtl/chip/ot_chip_v41x_ckv_die_service.sv';fetch='rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv';merge='rtl/chip/ot_chip_v41x_ckv_stream_merge.sv'
 citations=[cite(service,n) for n in ['wire [4:0] wv','new_sel_pulse <=','buf_row[','npresent <=','rel <=','new_owned']]
 citations += [cite(fetch,n) for n in ['o_ready','slots retire']]+[cite(merge,n) for n in ['assign c_take','c_rows_q','rdy[o]']]
 citations += [cite('rtl/hdc/v41/ot_hdc_fp4qdq.sv',n) for n in ['s3_n[b] <=','s4_n[b] <=','r = twov(s5_c[i])','s1_nf <=']]
 citations += [cite('tools/hdc_golden_v41.py',n) for n in ['np.minimum(_e4m3_round','state["ckv"][L].append','q = np.sign(x)']]
 directory='physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/';name='ot_sram_1r1w_256x256_m2_r2c2'
 lef=raw(REAL,directory+name+'.lef').decode();v=raw(REAL,directory+name+'.v').decode();ss=raw(REAL,directory+name+'_ss.lib').decode();ff=raw(REAL,directory+name+'_ff.lib').decode()
 width,height=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',lef).groups());cell=float(re.search(r'area\s*:\s*([\d.]+)',ss).group(1))
 def table_values(lib,kind):
  out=[]
  for match in re.finditer(r'\b'+kind+r'\s*\([^)]*\)\s*\{([^}]+)\}',lib):
   text=match.group(1);values=text[text.index('values'):];out.extend(float(z) for z in re.findall(r'-?\d+\.\d+',values))
  return out
 q=table_values(ss,'cell_rise')+table_values(ss,'cell_fall');qff=table_values(ff,'cell_rise')+table_values(ff,'cell_fall')
 worst=max(q);best_ff=min(qff)
 saturation=saturation_witnesses()
 parent=record('6a868d3c9','results/rtl/parent_dsrom_prerequisite_review_20261002/qdq4_scale_static_screen.json')
 saturation['independent_parent_static_intake']={'record':parent,'scope':'Source-pinned independent BF16amax integertranscription; notexecutedRTL, allFP32proof oractivationfrequency claim.'}
 raw('6a868d3c9','tools/parent_dsrom_qdq4_scale_review.py')
 # Concrete ascendingGIDs demonstrate owner and rankbank areindependent.
 owner_for_rank={r:s for s,rs in enumerate([[3,7,11],[15,19,23],[27,31,35],[39,43,47]]) for r in rs}
 owner_for_rank[511]=0
 gids=[];last=-1
 for rank in range(512):
  owner=owner_for_rank.get(rank,rank%4);g=last+1
  while ((g>>4)&3)!=owner:g+=1
  gids.append(g);last=g
 assert all(a<b for a,b in zip(gids,gids[1:])) and gids[-1]<(1<<21)
 ownership_witness=[{'rank':r,'bank':r%4,'globalID':gids[r],'owner':(gids[r]>>4)&3} for r in sorted(owner_for_rank)]
 rr=bank_sim([[0,4,8,12],[16,20,24],[28,32,36],[40,44,48],[52]],ready_pause=2)
 all_rows=bank_sim([list(range(s,511,4)) for s in range(4)]+[[511]])
 conflict=bank_sim([[3,7,11],[15,19,23],[27,31,35],[39,43,47],[511]])
 calendar_tree=ast.parse(raw('117ae7d5d25fda1084402c456340f2861eb32d1f','tools/dsrom_attention_controller_l20_model.py').decode())
 calendar_node=next(n for n in calendar_tree.body if isinstance(n,ast.FunctionDef) and n.name=='selected_calendar')
 cal={};exec(compile(ast.Module(body=[calendar_node],type_ignores=[]),'pinned_merger_calendar','exec'),cal)
 emits=cal['selected_calendar'](126,128)
 # Instrument only the pinned recurrence's fill events; memory feeds A,
 # not the downstream emitted-beat events. Firsttwo groupsare explicitly
 # cold-primed atcycles2,3, remainingAfillrequests127,128,130,131...
 cal_source=ast.get_source_segment(raw('117ae7d5d25fda1084402c456340f2861eb32d1f','tools/dsrom_attention_controller_l20_model.py').decode(),calendar_node)
 assert cal_source.count('emits = []')==1 and cal_source.count('if fill:')==1
 cal_source=cal_source.replace('emits = []','emits = []; fills = []').replace('if fill:','if fill:\n            fills.append(t)').replace('return emits','return emits, fills')
 instr={};exec(compile(cal_source,'pinned_merger_fill_instrumentation','exec'),instr)
 same_emits,fills=instr['selected_calendar'](126,128);assert same_emits==emits
 demands=[2,3]+fills;assert len(demands)==128
 replay=[replay_sim(),replay_sim(range(4,40)),replay_sim(t for t in range(200) if t%5!=0),replay_sim(demand=demands)]
 macro_count=4*9;halo=fp['geometry']['pin_halo_um'];bank_w=3*(width+2*halo);bank_h=3*(height+2*halo)
 read_tracks=9229;write_tracks=11680;channel=min_channel(read_tracks+write_tracks)
 island_w=4*bank_w;island_h=bank_h+channel;island=island_w*island_h/1e6
 state={'four_ingress_packets':4*2352,'two_readgroup_payloads':2*4*2304,'four_registered_write_grant_payload_identity':4*(2304+10+16+3+1),'two_readgroup_identity_count_valid':2*(7+16+3+1),'four_RR_selectors':4*3,'write_commit_flags':4,'pending_read_identity_slot_valid':7+16+1+1,'read_credit_count':2}
 added_bits=sum(state.values()) # four incoming packets,2 four-rowreadgroups,metadata,RR,writeack,readtags
 write_mux=4*4*2304;read_mux=0 # full groups aligned4; native row lane orderbank0..3.
 logic=added_bits*.2916+write_mux*.2
 removed=1179648*.2916/.5/1e6+(4709376+4718592)*.2/.5/1e6
 replacement=island+logic/.5/1e6
 # Saturation makes prior4rangeflags+1S6packedfault register unnecessary;
 # use retainedfault alias. ClassA capproxy remains separatelypriced.
 saturation_net_placed=((2*31+2*15)*.2-5*.2916)/.5/1e6
 newfull=prev['retained_hub']['full_goal_source_screen']['required_placed_subtotal_mm2']-removed+replacement+saturation_net_placed
 hub=next(r for r in fp['soft_regions'] if r[0]=='HUB_ATTENTION');ox,oy=hub[2],hub[3]
 placements=[{'bank':b,'slice':r*3+c,'origin_um':[ox+b*bank_w+c*(width+2*halo)+halo,oy+r*(height+2*halo)+halo],'size_um':[width,height],'orientation':'R0'} for b in range(4) for r in range(3) for c in range(3)]
 existing=[i for i in fp['instances'] if i[-1]=='HUB_ATTENTION']
 # Allretainedattentionhardmacros are1024x256 QEwindows, notcollectors.
 known_lef=raw(REAL,'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef').decode()
 ew,eh=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',known_lef).groups())
 assert all(i[1]=='ot_sram_1r1w_1024x256_m2_r2c2' for i in existing)
 overlaps=[i[0] for i in existing if i[2]<ox+island_w and i[2]+ew>ox and i[3]<oy+island_h and i[3]+eh>oy]
 assert not overlaps
 assert ox+island_w<=hub[2]+hub[4] and oy+island_h<=hub[3]+hub[5]
 # Replay provides at leastone4-rowgroup everycycle when merger takes; source
 # merger requests never more thanonegroup/cycle. Its measured recurrence is
 # retained; memorycoldstart is independently priced, not silentlyhidden.
 model=dict(schema='opentallas.dsrom.L20-banked-collector-existing-golden-contract.v1',source=REAL,prior=PRIOR,
  status='FINITE_BANKED_SERVICE_MODEL_AND_EXISTING_GOLDEN_REPAIR_PREPARED_NOT_BUILD_READY',engine_RTL_build_ready=False,launch_allowed=False,
  original_failed_screens_preserved={'monolithic_service_perrank_mm2':prev['full_service_area']['full_listed_service_placed_mm2_per_rank'],'records':[PRIOR,'1fb01b08d2bf08f9458928595d94f492ac8aab4a'],'original_controller_failure':prev['original_FAILURE']},
  saturation_repair=saturation,
  saturation_area_latency={'scale_registers_unchanged':True,'direct_sideband_quantizer_added_FF_bits':176,'candidate_sideband_registers':{'S4_packedscales':16,'S5_packedscales':16,'S6_codes_and_scales':144,'S6_fault_alias_existing':0},'alignment':'S3cappeddecision serialized intoS4scale16, thenS5scale16 andS6outputscale16; code128fromsameS5codes/sign atS6. Existing n/qs transport forBF16 remainsunchanged.','prior181FF_superseded_by_saturation':True,'removed_range_flags_and_fault_alias_bits':5,'producer_service_added_bits_revised':9156,'extra_registered_cycles_candidate':0,'bit_operations':'two31bit constant comparisons / two15bit n+qs selects at S3; compareparallelwith existing scaleRNE and capBEFORE thresholdstage',
   'analytical_mux_equivalent_area_proxy_um2':(2*31+2*15)*.2,'area_proxy_scope':'Prior.2um2/mux-bit proxy; comparison is not a characterized mux or measuredtiming. Must measure theactual S3 logic, no closure transfer orfreeclock.',
   'common_controller_cut':'Prospective+2cycles retained separately; saturation equality doesnotcertify controller orS3timing.'},
  writer_actual_simultaneity={'source_ports':5,'steady_sources':'one rankordered localfetch+3independentpeerRX; ownrow isonceepoch andrank511, bypassesfetch ifselected',
   'current_source_legal_phase':'Fresh go schedules ownpulse before newlystarted fetch can return realHBM row. Fresh localfetch+own overlap isnotproven attainable then. Threepeerinputs have no latency/epoch/readyguard, so own+3orlocal+3 canoverlap.',
   'retirement_violation':'Current newselection lacksoldfetchdrain; stale f_ov canoverlapownpulse, so current5portexpression cannot safelybe reducedbyassumingfresh jobs.',
   'corrected_publication_phase':'Owncollectorpublication maywaitfor9visiblewrites whileother fetch/peerrows arrive. Model retains5contenders andoneheldownrow, never assumes disjointness tosaveports.',
   'concrete_ascending_GID_samebank_ownership_witness':ownership_witness,
   'row_ownership':'owner=globalID[5:4], stack=ID[7:6], local=((ID>>8)<<4)|ID[3:0]. SortedIDs doNOT imply rankmod4==owner; adversarialsamebank conflicts legal.',
   'acceptance':'Four1rowingress FIFOs (local+3RX), existingownedrow held. Jointlocalaccept requires FIFOseat plus all3TXcopy reservations. Peer ready onlywhen inputFIFO and512rankseat reserved. Return end-to-end peer/rank credit onlyafterSRAMcommit. FIFOstorage maybe reused after a grant transfers its packet into thepricedregisteredbankgrant; no packet-storage slot isfreed without anotherfiniteowner. No free5writeports.'},
  bank_addressing={'banks':4,'physical_depth_each':256,'logical_depth_each':128,'slices_perbank':9,'macro_width':256,'macro_count':36,'rows':512,'row_bits':2304,'bank':'rank&3','address':'rank>>2',
   'write_ports_perbank':1,'read_ports_perbank':1,'write_arbitration':'Perbank rotatingRR among5heads; oneacceptedwrite perbank/edge. Samebank heads wait heldunderfinitebackpressure. Reserve rank beforeenqueue; duplicate orwrongGID/epoch never accepted.',
   'write_fairness_bound':'If5heads targetonebank, eachgrant within5serviceedges; one registeredgrant->nextedge macrocommit; protocolpresent/npresent change onlyoncommit. RR guarantees depend on no infinite pause/reset.',
   'read_order':'QK thenPV eachreplay rank0..511 as128alignedgroups offour. Eachgroupaddressesfour distinctbanks, lanes0..3=rank4g..4g+3. Samegolden row/treeorder; no extra readreplicas.',
   'read_backpressure':'Two4rowgroup buffers andoneoutstanding synchronous macroread. Reserve groupcredit BEFORE issue. Hold groupuntil c_take; nooverwrite onmergerstall. Eachopcode rewind after previous DRAIN.',
   'read_write_hazard':'Phased: all512committed+ownvisible+WINDOW128 beforeREADY; no acceptedcollectorwrites during QK/PV, no read/write collision. Macro actualread-before-write preserved, no forwardednewdata assumption.'},
  finite_arbitration_checks={'samebank_with_pause':rr,'five_including_rank511_samebank':conflict,'full512_fill':all_rows,'ordered_replay_scenarios':replay,'actual_L20_merger_A_fill_requests':demands,'actual_L20_merger_KV_emit_calendar':emits,'verdict':'PASS_INTEGER_EVENT_MODEL_ONLY_NOT_RTL_OR_PROVIDER_QUALIFICATION'},
  state_ports_area={'new_state_fields':state,'new_control_and_buffer_bits':added_bits,'new_FF_cell_um2':added_bits*.2916,'write_mux_bit_equivalents':write_mux,'read_mux_bit_equivalents_aligned512':read_mux,'saturation_cap_net_placed_area_proxy_mm2':saturation_net_placed,
   'two_read_buffers_payload_bits':18432,'four_ingress_packet_skid_bits':9408,'SRAM_hard_area_mm2':36*cell/1e6,'SRAM_allocated_logical_bits':512*2304,'physical_memory_bits':36*256*256,'depth_utilization':.5,
   'collector_oldFF_read_write_mux_placed_removed_mm2':removed,'new_macro_channel_and_logic_placed_candidate_mm2':replacement,'full_listed_attention_service_candidate_mm2':newfull,'four_TP_ranks':4,
   'other_co_residents':'Priorlisted MACs/stationary/transposer/stage/ID/slot/merger/mandatory/backend costs retained. Existinghistoricalindexer21.677mm2 reservation separatelysourcebound, currentX_IDX2/SUN256/SUM64 completeareastillneeds sourceequivalence.',
   'with_historical_indexer_reservation_diagnostic_mm2':newfull+fp['refit']['hub_units']['indexer']['area_mm2'],'historical_indexer_transfer_certified':False},
  physical_proposal={'macro':name,'macro_dimensions_um':[width,height],'pin_halo_eachside_um':halo,'OBS_excerpt':lef[lef.index('  OBS'):],
   'macro_source_behavior':'1R1W synchronous;read-before-write sameaddress, outputholdswhenr_ce0. Viewsareexistingcompilercharacterization, not newservicehardenedmeasurement.',
   'SS_clkq_range_ps':[min(q),worst],'FF_clkq_min_ps':best_ff,'SS_remaining_route_and_receiver_setup_ps_at1p2':2500/3-60-worst,
   'candidate_source_based_origin_um':[ox,oy],'proposed_macro_placements':placements,'retained_attention_macro_overlap_screen':{'checked_instances':len(existing),'overlap_instances':overlaps,'verdict':'PASS_GEOMETRY_ONLY_NOT_SOFT_LOGIC_OR_SLOT_RESERVATION'},
   'bank_cluster_layout':'Eachbank3x3 existingmacros;fourclustersinonehorizontalrow, nodepth/readreplicas beyond36macros.',
   'bank_cluster_bbox_um':[bank_w,bank_h],'combined_conservative_read_write_channel_tracks':read_tracks+write_tracks,'M2_M4_channel_height_um':channel,
   'candidate_dedicated_hub_island_bbox_um':[island_w,island_h],'island_gross_mm2':island,'source_hub_region':next(r for r in fp['soft_regions'] if r[0]=='HUB_ATTENTION'),
   'serviceband_216um_fit':False,'hub_island_reserved_in_actual_source':False,
   'route_scope':'Dedicatedmacrofree horizontalM2/M4 channel along macroedges, notoverOBS. M1-M4blockedinsidearrays, M4edgepins;M5verticalallowedwherecapacitybound. Conservativecombined11680write+9229read wires priced; no implicitM6+capacity.',
   'co_resident_fit_verdict':'NO_ACTUAL_RESERVATION. Islandgeometry fitsgrosshubdimension but cannotallocatefromco-residents. Fullgoal withhistoricalindexer diagnostic exceeds41.0935mm2 envelope; currentsourceequivalentindex/SU/VM/clock/CDC mustbe bound.',
   'OBS_replicas':36,'signal_ports_bits_perbank_read':2304,'signal_ports_bits_perbank_write':2304,'MACs_percycle_collector':0},
  latency_composition={'write_service':'Atmost4differentbankwrites/cycle, worst1samebank/cycle.512rows drained<=512writegrants afterallrowsareoffered, plus registeredcommit/READYedges. Arrival/provider/HBMvisibility countedseparately; cannotassignallrows time0 withoutbuffering.',
   'read_service':'128SRAMreadedges per512replay,1synchronousedge readlatency; bufferssupplyatmostone4rowgroup/cycle, minimum throughput under finite scheduledmergerbackpressure modeled above.',
   'post_READY_startup_bound_candidate_cycles':4,'steady_merger_calendar':'Retainedtwo-buffer merger KVemit recurrence126,127,129,130... (last316), Afill127,128,130,131... unchangedifreadbufferprimed, butcoldstart+4cycles/job ischargedconservativelyuntil sourcephaseproof.',
   'QK_runtime_candidate_cycles':2894+4,'PV_runtime_candidate_cycles':3374+4,'controller_common_cut_added_each':2,'QK_PV_added_banked_coldstart_cycles':8,
   'actual_L20_work_counts':{'QK_descriptors':1,'PV_descriptors':1,'program_PCs':[55,63],'logical_rows_each':512,'four_rowgroups_each':128,'macro_read_operations_QK_plus_PV':36*128*2,'macro_write_operations_perselection':512*9,'collector_ingest_bytes':512*288,'replay_bytes_QK_plus_PV':2*512*288},
   'whole_token':'Priorfinitecandidate3166517 +8coldstart cycles is onlypartialconditionalcalendar. Indexed selection/SU/oldintentdrain, realproduceraccept, peers, CDC/routes mustcompose; no assumedperfectservice or9537serialmultiply.'},
  opt_in_prepreview={'QDQ4E_GOLDEN_SAT448':0,'CKV_COLLECTOR_BANKED':0,'CKV_SERVICE_EXACT':0,'CKV_PACKED_SIDEBAND':0,'files':['rtl/w17_runtime/l20_exact/ot_hdc_fp4qdq.sv','rtl/w17_runtime/l20_exact/ot_chip_v41x_ckv_die_service.sv'],'files_authored':False,'enabled_path_dependencies':'Bankedcollector requires reviewed exactsession/visibleACK/jointREADY/retirement/finitepeer providers. Existing128WINDOW/L0path retained. No engineRTL authored.'},
  source_citations=citations,four_targets=prev['four_targets'],new_target_applicability={'DeepSeek_ROM':'MandatorygoldenCKVfinite saturation and banked L20 candidate; actualcurrent sourcegates required.','DeepSeek_HBM':'SamegoldenCKVnumericcontract applies; ordinary GPUbankedshared-memory comparator onlywith itsownsourcebinding. No ROMcontroller timingcut transfer.','Qwen_ROM':'No direct QDQ4EcompressedCKV/L20 assumption; bankingsizing method only, needs Qwensourceparameters.','Qwen_HBM':'No QDQ4E/L20qualification transfer; only ordinaryGPUshared-memory banking where realcomparator exposes it.'},preserved_inputs={'program':prev['program'],'all125sourcepins':prev['source_manifest']},
  exact_remaining_gates=['Sourceprepreview of opt-inS3saturation feedingcodes/output/sideband together; gatedexactfinite/nonfinitefixture, notsideband-onlychange','ImplementfiniteRXready/FIFO andperbankRR/commitpresent; epoch/session oldintentdrain andcreditownership','JointWINDOW128+selected512+own9visibleACK READY andQKthenPV retirement','Reserve dedicatedhubisland andcurrentco-residentledger;36macroOBS/pins/latency/actualroutes/clockdomains inrealL20die','ClassAarithmeticrepair andbankedschedule/sourcegates beforeenginebuild; no qualificationtransfer'],
  operations={'engine_RTL_edits':0,'RTL_compiles':0,'simulations':0,'PnR':0,'checkpoint_payload_reads':0,'live_job_operations':0},pins=PINS)
 tb=baseline_quantizer_bench(saturation)
 bench_sources=['rtl/hdc/v41/ot_hdc_fp4qdq.sv','rtl/hdc/ot_hdc_delay.sv']
 bench_blobs={p:raw(REAL,p) for p in bench_sources}
 model['prepared_saturation_fixture']={'file':'tb_l20_qdq4_existing_golden.sv','sha256':hashlib.sha256(tb.encode()).hexdigest(),'negative_baseline_only':True,'corrected_sources_authored':False,'execution':'NOT_COMPILED_NOT_SIMULATED','scope':'Unchanged32value/2block quantizer, actual BF16/fault outputs assertedvsoriginaltranscription and actualgolden references. No rawports exist yet; directpacked exactness requires reviewedfuturevariant. No fullQE/blockdot elaboration.','source_files':bench_sources,'watchdog_cycles':5000,'CLK_PS_diagnostic':1000,'compile_command_not_executed':['iverilog','-g2012','-s','tb_l20_qdq4_existing_golden','-o','/tmp/l20_qdq4_baseline','tb_l20_qdq4_existing_golden.sv']+['source/'+p for p in bench_sources]}
 model['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();emit(a.output,model)
 emit(a.witness_output,{'schema':'opentallas.dsrom.L20-existing-golden-saturation-witnesses.v1','source':REAL,'model_generator_sha256':model['generator_sha256'],'arithmetic_witnesses':saturation,'pins':{k:v for k,v in PINS.items() if v['path'] in ['tools/hdc_golden.py','tools/hdc_golden_v41.py','rtl/hdc/v41/ot_hdc_fp4qdq.sv']},'engine_RTL_executed':False})
 # Copies and negative testsource are materialized only AFTER the model.
 for p,b in bench_blobs.items():
  dest=a.prepare/'source'/p;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists() and dest.read_bytes()!=b:raise SystemExit('Immutable sourcecopy differs')
  dest.write_bytes(b)
 dest=a.prepare/'tb_l20_qdq4_existing_golden.sv'
 if dest.exists() and dest.read_bytes()!=tb.encode():raise SystemExit('Immutable bench differs')
 dest.write_bytes(tb.encode())
 emit(a.prepare/'source_manifest.json',{'source_copies':[PINS[REAL+':'+p] for p in bench_sources],'model_sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),'bench_sha256':model['prepared_saturation_fixture']['sha256'],'RTL_executed':False})
 print(json.dumps({'status':model['status'],'golden_vectors':saturation['finite_vectors'],'legacy_mismatch_vectors':saturation['retained_source_mismatch_vectors'],'SRAM_macros':36,'new_full_listed_mm2':newfull,'banked_candidate_island_mm2':island,'engine_RTL_build_ready':False}))
if __name__=='__main__':main()
