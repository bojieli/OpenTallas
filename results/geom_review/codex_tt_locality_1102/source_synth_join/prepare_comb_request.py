"""Prepare only the residual actual D-function miter; no solver invocation."""
from pathlib import Path
import argparse,json,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--cone',type=Path,required=True);ap.add_argument('--leaf-join',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();x=json.loads(a.cone.read_text());j=json.loads(a.leaf_join.read_text())
if j['status']!='PASS_STATIC_LEAF_PIN_SOURCE_JOIN_ONLY' or j['leaf_count']!=133 or j['anonymous_alias_dependencies']!=0:raise ValueError('Actual leaf pin/source join is required first')
def freeze(e):return tuple(freeze(z) if isinstance(z,list) else z for z in e)
def leaves(e):
 if e[0]=='ff_output':return {e}
 if e[0] in ('and','or'):return set().union(*(leaves(z) for z in e[1]))
 if e[0] in ('not','xor'):return set().union(*(leaves(z) for z in e[1:]))
 if e[0]=='const':return set()
 raise ValueError('Unsupported residual AST '+e[0])
o,n=freeze(x['old_ast']),freeze(x['new_ast']);ol,nl=leaves(o),leaves(n)
if ol!=nl or len(ol)!=133 or {z[1] for z in ol}!={r['name'] for r in j['rows']}:raise ValueError('Actual free leaf interface differs')
ordered=sorted(ol,key=repr);index={z:i for i,z in enumerate(ordered)};memo={};lines=[]
def emit(e):
 if e in index:return f'leaf[{index[e]}]'
 if e[0]=='const':return "1'b"+str(int(e[1]))
 if e in memo:return memo[e]
 if e[0]=='not':rhs='~('+emit(e[1])+')'
 elif e[0] in ('and','or'):rhs=(' & ' if e[0]=='and' else ' | ').join('('+emit(z)+')' for z in e[1])
 elif e[0]=='xor':rhs='('+emit(e[1])+') ^ ('+emit(e[2])+')'
 else:raise ValueError('Unsupported function')
 name='n'+str(len(lines));lines.append(f'  wire {name} = {rhs};');memo[e]=name;return name
old,new=emit(o),emit(n);a.out.mkdir(parents=True,exist_ok=True)
text='// PREP ONLY: all133 actual boundary bits unconstrained; no reset/initial/valid assumptions.\nmodule tt_residual_anon_d_comb(input wire [132:0] leaf, output wire mismatch, output wire mutant_mismatch);\n'+'\n'.join(lines)+f'\n  assign mismatch=({old}) ^ ({new});\n  assign mutant_mismatch=({old}) ^ ~({new});\nendmodule\n'
(a.out/'miter.v').write_text(text);(a.out/'leaf_bits.json').write_text(json.dumps([dict(bit=i,actual_leaf=list(z)) for i,z in enumerate(ordered)],indent=1)+'\n')
request=dict(status='PREP_NOT_RUN',scope='ONE actual old50820/new50942 D-function combinational miter',free_boundary_bits=133,combinational_nodes=len(lines),miter_sha256=hashlib.sha256(text.encode()).hexdigest(),source_cone_sha256=hashlib.sha256(a.cone.read_bytes()).hexdigest(),leaf_join_sha256=hashlib.sha256(a.leaf_join.read_bytes()).hexdigest(),proposed_resource=dict(mem_gb=2,threads=2),proposed_commands=['read_verilog miter.v; prep -top tt_residual_anon_d_comb; sat -verify -prove mismatch 0 -show-inputs','read_verilog miter.v; prep -top tt_residual_anon_d_comb; sat -verify -prove mutant_mismatch 0 -show-inputs'],mutant_expectation='FAIL_WITH_COUNTEREXAMPLE',initial_state_or_reset_constraints=[],native_base_proved=False,aliases_accepted=False,full_source_credit=False,physical_release=False,required_parent_decision='Authorize bounded combinational-only solver after reviewing exact leaf join; no new source/RTL SYNTH/full LEC/CAD')
(a.out/'request.json').write_text(json.dumps(request,indent=1)+'\n');print('PREP_COMB_REQUEST133 freebits',len(lines),'nodes; NOT_RUN')
