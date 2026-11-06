from pathlib import Path
import json,re,subprocess,hashlib
w=Path('/srv/opentallas-scratch2/claude/wt/codex-bodyctl-off4-1106');rel='rtl/hbm_accel/cores_split/reform_1105s/q3/ot_hfd_coll_q3_body_ctl.sv';p=w/rel;s=p.read_text();assert 'OT_Q3CTL_OFF4_RT' not in s
sel=json.load(open('/srv/opentallas-scratch2/claude/wt/codex-bodyctl-csa-1106/physical/die_plan/hbm/over_cap_split/reform_1103/bench/q3_body_mul8_csa/retime/selected.json'));q={x['target']:x for x in sel};assert len(q)==10
for g in ['pc','pd']:
 for ix in [3,6]:assert q[g+str(ix)]['pre_a']==q['pb'+str(ix)]['pre_a']
preit='{ '+', '.join(q[k]['pre_a'] for k in ['pb3','pb6','pa1','pa2'])+' }'
manifest=[];decl=[];instances=[];out=s
for arr,outname in [('pb','m_iaddr_l'),('pc','m_del_l'),('pd','m_rgx_l')]:
 prestep='{ '+q[arr+'6']['pre_b']+', '+q[arr+'3']['pre_b']+' }'
 pat=r'^  assign (.*?u_mul\.'+outname+r'\[.*?\}) = (_\d+_);$'
 am=re.search(pat,s,re.M);assert am,outname;reg=am[2]
 cap=re.search(r'^  always @\(posedge clk_control\)\n    '+re.escape(reg)+r' <= .*?;$',out,re.M);assert cap,(outname,reg)
 old=cap[0];name='ot_q3_off4_'+outname
 new='`ifdef OT_Q3CTL_OFF4_RT\n  always @(posedge clk_control)\n    '+reg+' <= '+name+'_d;\n`else\n'+old+'\n`endif'
 out=out[:cap.start()]+new+out[cap.end():]
 decl+=['wire[31:0] '+name+'_d;'];instances+=['ot_bodyctl_off32_split_d '+name+'(.clk(clk_control),.iteration('+preit+'),.step('+prestep+'),.out_d('+name+'_d));']
 manifest.append(dict(output=outname,register=reg,clock='clk_control',iteration_D=preit,step_D=prestep,old_capture=old,new_capture='same original phase3 register, helper output is combinational after two internal captures'))
pos=out.index(');',out.index('module '))+2;out=out[:pos]+'\n`ifdef OT_Q3CTL_OFF4_RT\n'+'\n'.join(decl)+'\n`endif'+out[pos:]
pos=out.index('\nendmodule');out=out[:pos]+'\n`ifdef OT_Q3CTL_OFF4_RT\n'+'\n'.join(instances)+'\n`endif'+out[pos:]
# Preprocess ONLY the newly added flag false; all prior conditionals stay literal.
keep=[];stack=[]
for line in out.splitlines(keepends=True):
 t=line.strip()
 if t=='`ifdef OT_Q3CTL_OFF4_RT':stack.append(False);continue
 if stack and t=='`else':stack[-1]=not stack[-1];continue
 if stack and t=='`endif':stack.pop();continue
 if not stack or all(stack):keep.append(line)
assert not stack
assert re.sub(r'\s+','', ''.join(keep))==re.sub(r'\s+','',s)
p.write_text(out)
o=w/'results/die_hbm_1106/bodyctl_off4';o.mkdir(parents=True,exist_ok=True);(o/'source_capture_manifest.json').write_text(json.dumps(dict(base='fc9ce48023f',base_source_sha256=hashlib.sha256(s.encode()).hexdigest(),added_protocol_cycles=0,default_off_token_identity=True,method='Reuse exact factor-D rewinds established by MUL4 source mapping; recombine four iteration bytes and two stride bytes; retain original phase3 output capture',outputs=manifest),indent=1)+'\n')
recipes=w/'physical/die_plan/hbm_arch_cores/recipes_b2.json';r=json.load(recipes.open());key='ot_hfd_coll_q3_body_ctl__mul4rt_rcp1_off4';assert key not in r;c=json.loads(json.dumps(r['ot_hfd_coll_q3_body_ctl__mul4rt_rcp1']));c['defines'].append('OT_Q3CTL_OFF4_RT');c['files'].append('rtl/hbm_accel/cores_split/reform_1106/ot_bodyctl_off32_split_d.sv');c['source']='Optional source-only off32 same-output-edge retiming:26nibbleproducts then split16carry-save on existing captures;0addedcycles. Mechanism stream+mutants and all-three-stage mapping recorded. No P&R/adoption.';r[key]=c;recipes.write_text(json.dumps(r,indent=2)+'\n');print([(m['output'],m['register']) for m in manifest])
