#!/usr/bin/env python3
"""Trace frozen named native leaf/node/relay words to exact S8 post inputs.

Membership/arithmetic order only. No clock alias, time/phase or executed L6 proof.
"""
import argparse,gzip,hashlib,json,re,sys
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('fabric','cluster','die','faces','parts','station','logic','node','asbuilt','relay','stn','landing','reference','tools','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();s=a.fabric.read_text().split('endmodule')[0];c=a.cluster.read_text();die=gzip.decompress(a.die.read_bytes()).decode()if a.die.suffix=='.gz'else a.die.read_text()
 assert re.search(r'parameter\s+integer\s+MUT\s*=\s*0',s)
 assert 'parameter integer TG = 4' in a.logic.read_text()and '.i_gbase({16\'d0, tile_id_i} * TG)'in a.logic.read_text()
 for text in [a.faces.read_text(),a.parts.read_text()]:
  compact=re.sub(r'\s+','',text)
  assert ('{rs_s1,rs_s0}'in compact and '{rs_n1,rs_n0}'in compact)
 st=a.station.read_text();assert 'fs_d = rs_s_hi, fn_d = rs_n_hi' in st and '.d(rs_s_lo)'in st and '.d(rs_n_lo)'in st
 assert '.a(fs_d[32*l +: 32]), .b(ns_d[32*l +: 32])'in st and '.a(fn_d[32*l +: 32]), .b(nn_d[32*l +: 32])'in st
 assert '.a(ylo[32*l +: 32]), .b(yhi[32*l +: 32])'in st and '.a(h9_q[32*l +: 32]), .b(nb_d[32*l +: 32])'in st
 node=a.node.read_text()
 assert 'ot_qwen_tile_node u_node' in a.logic.read_text() and 'assign na_x = n_a;' in a.logic.read_text()
 assert 'ot_qwen_w12_tadd #(.LAT(7), .ANR(2))' in node and 'ad[32*p +: 32], bd[32*p +: 32]' in node
 # These are the exact frozen821 WT bytes, independently read on Epyc2.
 frozen={a.faces:'26c6b9ca0388b5ddb377b729490280de55830dbe8b3a6a0c012541ce726da6a6',a.parts:'20bdc4cf6da6970bf75e866266334249959ac9116339b53e51d511a81fc9f057',a.node:'f40676e8db499d7c1b146eb33d3e474721116a202fad4c633e8c4ce331e3e71c',a.logic:'019e19dedcab454a9853a9d41e04dca72e51ad9044e7c36f66a11f8599fe829c',a.station:'f8b88f24b6b03f34749f6d79fb72ffb1ba7d280c328b26c4558c11052891f709'}
 for path,digest in frozen.items():assert sha(path)==digest,('FROZEN_SOURCE_DIFF',str(path))
 # Exact whole-word transport semantics, not port-name inference.
 transport_sources={a.relay:'94469b77dd96768ece5c82ea654c739d62a8d4ccc6dc3a0878799c759b178cc8',a.stn:'1adc9f32e59ecd5faedeb65ba2e308602cfbc2a7409439a2e31e0c1deafe11e5',a.landing:'04392bcb9a1fc4022f29faebbab8d6a8505957e3ef16f147d080e6ac665ececb'}
 for path,digest in transport_sources.items():assert sha(path)==digest,('FROZEN_TRANSPORT_DIFF',str(path))
 assert 'q_r <= d;' in a.relay.read_text() and 'assign q = {N{q_r}};' in a.relay.read_text()
 assert '.d(s[i]), .q(s[i+1])' in a.relay.read_text() and 'assign q = s[D];' in a.relay.read_text()
 assert a.stn.read_text().count('q_r <= d;')==2 and a.stn.read_text().count('assign q = q_r;')==2
 assert 'b[s] <= i;' in a.landing.read_text() and 'assign bank[s*W +: W] = b[s];' in a.landing.read_text()
 assert 'bank[sel*W +: W]' in a.landing.read_text()
 asbuilt=json.loads(a.asbuilt.read_text());rules=[x for x in asbuilt['transport'] if x['module']==r'qfd_landh0_\d+_\w+']
 assert len(rules)==1 and rules[0]['map']=={'b':'a'}
 allowed_fabric={'qfd_q3h_stn','qfd_q3h_run','qfd_c_stn514','qfd_c_stn516','qfd_c_land_w','qfd_c_land_r'}
 used_fabric=set();used_die=set()
 flow={};writers={};readers=[];edge_records={}
 for m in re.finditer(r'\bassign\s+(\w+)\s*=\s*(\w+)\s*;',s):flow[m[1]]=m[2]
 for m in re.finditer(r'assign\s+(msw_\w+)\s*=.*?:\s*(\w+)\s*\)\s*;',s):flow[m[1]]=m[2]
 assert 'wire [513:0] rs_i_m5 = (MUT == 5)'in s;flow['rs_i_m5']='rs_i'
 for ln,line in enumerate(s.splitlines(),1):
  if not re.search(r'\bqfd_\w+\s*(?:#\s*\(|\w+\s*\()',line):continue
  ports=dict(re.findall(r'\.(\w+)\((\w+)\)',line))
  mod=re.search(r'\b(qfd_\w+)',line)[1]
  if ('d'in ports and'q'in ports)or('i'in ports and'bank'in ports)or('bank'in ports and'o'in ports):
   assert mod in allowed_fabric,('UNREVIEWED_TRANSPORT',mod);used_fabric.add(mod)
  if 'd'in ports and 'q'in ports:flow[ports['q']]=ports['d'];edge_records[ports['q']]=dict(input=ports['d'],line=ln,kind='named_d_q_register_or_run')
  if 'i'in ports and 'bank'in ports:writers[ports['bank']]=ports['i']
  if 'bank'in ports and 'o'in ports:readers.append((ports['o'],ports['bank'],ln))
 for o,b,ln in readers:flow[o]=writers[b];edge_records[o]=dict(input=writers[b],line=ln,kind='same_bank_writer_i_to_reader_o')
 leaf={};nodes={};local_ids={}
 for m in re.finditer(r'qfd_tile_(?:nk|nl)_rp2_romleaf_rr\s+(u_t_(\d)_(\d))\s*\((.*?)\);',c,re.S):
  coord=m[2]+'_'+m[3];bits=re.search(r'\.tile_id\(\{cid,([^}]+)\}\)',m[4])[1]
  assert all(x.strip().startswith(('th_','tl_'))for x in bits.split(','))
  tid=int(''.join('1'if x.strip().startswith('th')else'0'for x in bits.split(',')),2);local_ids[m[1]]=tid
  leaf['t_out_'+coord]=tuple(range(4*tid,4*tid+4))
  if '.n_y('in m[4]:nodes['n_y_'+coord]=['n_a_'+coord,'n_b_'+coord]
 assert len(leaf)==16 and set(local_ids.values())==set(range(16))and len(nodes)==15
 node_proofs={}
 def cluster_trace(n,stack=()):
  if n in leaf:return leaf[n]
  if n=='rs_i':return ('FAR_INPUT',)
  assert n not in stack,('CYCLE',n)
  if n in nodes:
   left,right=[cluster_trace(v,stack+(n,))for v in nodes[n]]
   assert len(left)==len(right)and not(set(left)&set(right))and left[-1]+1==right[0],n
   assert left==tuple(range(left[0],left[-1]+1))and right==tuple(range(right[0],right[-1]+1))
   node_proofs[n]=dict(inputs=nodes[n],left=list(left),right=list(right));return left+right
  assert n in flow,('MISSING_CLUSTER_WORD',n);return cluster_trace(flow[n],stack+(n,))
 root=cluster_trace('rs');assert root==tuple(range(64))and cluster_trace('rs_o')==('FAR_INPUT',)
 instances={}
 for m in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\((.*?)\);',die,re.M|re.S):instances[m[2]]=(m[1],dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[3])))
 topflow={};topnodes={};toprecords={}
 for name,(mod,ports)in instances.items():
  if mod=='qfd_c_b16_dv':
   cid=int(ports['cid'].split("'h")[1],16);topnodes[ports['rs']]=tuple(64*cid+x for x in root)
   toprecords[ports['rs']]=dict(instance=name,port='rs',cid=cid,tile_id_range=[16*cid,16*(cid+1)],group_range=[64*cid,64*(cid+1)])
   if 'rs_o'in ports:topflow[ports['rs_o']]=ports['rs_i'];toprecords[ports['rs_o']]=dict(instance=name,port='rs_o',input=ports['rs_i'],kind='verified_same_cluster_far_feedthrough')
  elif 'a'in ports and 'b'in ports and(mod.startswith('qfd_land')or mod.startswith('qfd_ft')):
   topflow[ports['b']]=ports['a'];toprecords[ports['b']]=dict(instance=name,module=mod,input=ports['a'],kind='named_same_word_transport')
 for m in re.finditer(r'\bassign\s+(\w+)\s*=\s*(\w+)\s*;',die):topflow[m[1]]=m[2]
 def top_trace(n):
  trail=[]
  while n not in topnodes:
   assert n in topflow and n not in trail,('MISSING_TOP_WORD',n,trail);trail.append(n)
   if 'module' in toprecords.get(n,{}):
    mod=toprecords[n]['module'];assert mod in {'qfd_landh0_514_NS_90x30','qfd_landh0_514_SN_90x30'};used_die.add(mod)
   n=topflow[n]
  return topnodes[n],[toprecords.get(x,dict(net=x,input=topflow.get(x)))for x in trail]+[toprecords[n]]
 mappings=[]
 for block,sender,receiver,codebase in [(0,'W5','W4',0),(148,'E3','E2',2048)]:
  sides={};domains=[]
  for role,sl in [('sender',sender),('receiver',receiver)]:
   ports=instances['dvs_'+sl][1];side={}
   for port,st_port in [('rs_s0','ns_rs_s_lo'),('rs_s1','fs_rs_s_hi'),('rs_n0','nn_rs_n_lo'),('rs_n1','fn_rs_n_hi')]:
    groups,path=top_trace(ports[port]);assert len(groups)==64
    lo,hi=groups[0]-codebase,groups[-1]+1-codebase;assert 0<=lo<hi<=512 and lo%64==0
    side[st_port]=dict(slice_pin=port,group_interval=[lo,hi],absolute_code_group_interval=[groups[0],groups[-1]+1],logical_stream=lo//64,path=path);domains.append(set(range(lo,hi)))
   sides[role]=dict(slice=sl,ports=side,own_bracket=[[side['fs_rs_s_hi']['logical_stream'],side['ns_rs_s_lo']['logical_stream']],[side['fn_rs_n_hi']['logical_stream'],side['nn_rs_n_lo']['logical_stream']]])
  assert len(domains)==8 and sum(map(len,domains))==512 and set.union(*domains)==set(range(512))
  for i,x in enumerate(domains):assert all(not(x&y)for y in domains[i+1:])
  mappings.append(dict(block=block,code_group_base=codebase,sides=sides,result_bracket=[sides['receiver']['own_bracket'],sides['sender']['own_bracket']],operation='receiver_h9_held_own_L8 + real_neighbor_sender_L8'))
 # Compare selected L7/L8/L9 bracket literally against unchanged canonical
 # logical-tree REFERENCE input data at EVERY K prefix, not just final values.
 sys.path.insert(0,str(a.tools));import hdc_golden as G
 import numpy as np
 data={}
 for line in a.reference.read_text().splitlines():
  if line.startswith('#'):continue
  b,stream,k,slot,value=line.split();v=int(value,16);data[(int(b),int(stream),int(k),int(slot))]=G.from_bits(np.array([(v>>(32*l))&0xffffffff for l in range(16)],dtype=np.uint32))
 checked=0
 for m in mappings:
  b=m['block'];slots=8 if b==0 else 3
  for k in range(8):
   for slot in range(slots):
    def ev(node):
     if isinstance(node,int):return data[(b,node,k,slot)]
     return G.add(ev(node[0]),ev(node[1]))
    selected=ev(m['result_bracket']);canonical=ev([[[0,1],[2,3]],[[4,5],[6,7]]]);assert np.array_equal(G.bits(selected),G.bits(canonical)),(b,k,slot);checked+=16
 result=dict(transport_identity_authority=dict(fabric_types=sorted(used_fabric),fabric_payload='whole word registered, repeated intact or ring slot selection; epoch/control separate',top_traversed_types=sorted(used_die),top_authority='exact frozen final_asbuilt transport b:a declaration',top_rule=rules[0],original_placeholder_body='ABSENT; no body or latency/phase claim; selected binder declared identity only'),status='PASS_SOURCE_MEMBERSHIP_AND_LITERAL_BRACKET_REFERENCE_COMPARE',profile='selected frozen821/f79 MUT0 TG4 GBASE=4*tile_id',native_cluster_leaf_local_ids=local_ids,native_cluster_node_proofs=node_proofs,cluster_result_group_order=list(root),cluster_dataflow_edges=edge_records,post_mappings=mappings,partition_assertions='eight disjoint64split domains union0..511 for each row block',literal_bracket_compared_FP32_values=checked,literal_bracket_compare='all88 full512splitKprefixvectors/1408FP32 compare selectedliteralbracket vs unchangedcanonicalREFERENCEtree bitwise',scope='source membership/order and reference arithmetic only; no executedL6/post/STN, no arrival/phase/clock proof',boundary_contract='near lo must precede corresponding far hi by actualstation SKEW14; selectedneighbor positivelead/transport andsharedBTAB timing remain separately sourced',readset={str(x):sha(x)for x in [a.fabric,a.cluster,a.die,a.faces,a.parts,a.station,a.logic,a.node,a.asbuilt,a.relay,a.stn,a.landing,a.reference,a.tools/'hdc_golden.py']})
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],'values',checked)
 for m in mappings:print(m['block'],m['result_bracket'])
if __name__=='__main__':main()
