from pathlib import Path
import sys,json,hashlib,shutil,re,subprocess
R=Path('/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106');S=R/'ft_src';sys.path.insert(0,str(S/'tools/die_plan'));import gen_phys as G,core_ft_physical as F,kit_core_clocks as K
E=S/'physical/die_plan/qwen_compute/ft_physical_1106';W=R/'east_pilot_packet';out=R/'ft_actual_headers';out.mkdir(exist_ok=True);rtl=out/'rtl';rtl.mkdir(exist_ok=True)
raw=json.loads((R/'pilot_src/physical/die_plan/qwen_compute/plan_of_record/plan_east_suc_81_b2.json').read_text());cores=[dict(c) for c in raw['partition_types']['sle_su_c']['hard_cores'] if c['module'] in F.SUPPORTED];mac=[];headers={}
for c in cores:
 short='vmr' if c['module']=='qfd_dv_s8x_vmr' else 'crh';d=E/short;m=c['module'];p=d/'proof.json';c['physical_ft']={'proof':str(p),'proof_sha256':F.sha(p),'unconsumed_outputs':['ft_ck_o','ft_rst_o']};c['native_port_adapter']={'merge':{},'cycles':0,'tie':{'ft_ck_i':"1'b0",'ft_rst_i':"1'b0"}}
 c['pins_file']=str(R/'pilot_src/physical/die_plan/qwen_compute/plan_of_record'/c['pins_file']);mac.append((c['inst'],m,str(d/(m+'.lef')),str(d/(m+'_tt.lib')),*c['origin_um'],c['orient']));headers[m]=(d/'core_header.txt').read_text()+'\nendmodule\n'
old=(W/'native_su2/rtl/qfd_qc_sle_su_c.sv').read_text();new,receipts=K.adapt_core_ports(old,cores)
for c in cores:
 inst='u_'+c['inst'];pat=r'^\s*'+re.escape(c['module'])+r'(?:\s+#\([^\n]*\))?\s+'+re.escape(inst)+r'\s*\((.*?)^\s*\);'
 def con(txt):return dict(re.findall(r'\.(\w+)\(([^()]*)\)',re.findall(pat,txt,re.M|re.S)[0]))
 a,b=con(old),con(new);assert set(b)-set(a)=={'ft_ck_i','ft_rst_i'} and all(b[n]==v for n,v in a.items())
text='\n'.join(headers.values())+'\n'+new;inp=out/'input.sv';inp.write_text(text);shutil.copy2(inp,rtl/inp.name)
files=G.macro_param_blackboxes(mac,[inp],rtl,None,cores,None)
for f in files:subprocess.run(['iverilog','-g2012','-tnull',str(f)],check=True)
contracts=F.contracts(cores,mac,text)
mut=text.replace(".ft_ck_i(1'b0)",".ft_ck_i(1'b1)",1)
try:F.contracts(cores,mac,mut)
except ValueError:tie_mutant=True
else:raise ValueError('tie mutant escaped')
first=cores[0];needle=".ft_ck_i(1'b0)";mut=text.replace(needle,needle+",\n        .ft_ck_o(rogue_net)",1)
try:F.contracts(cores,mac,mut)
except ValueError:out_mutant=True
else:raise ValueError('consumed output escaped')
result={'schema':'opentallas.actual_physical_ft_header_evidence.v1','scope':'actual approved SU2/SUc five native instances; static source/header integration only, no GEN/P&R','instances':len(cores),'existing_port_connections_unchanged':True,'input_ties_added':10,'outputs_explicitly_unconsumed':10,'cycles_changed':0,'headers':[str(f) for f in files],'header_compile':'PASS iverilog','tie_mutant_caught':tie_mutant,'consumed_output_mutant_caught':out_mutant,'receipts':receipts,'contracts':contracts}
(out/'actual.json').write_text(json.dumps(result,indent=1)+'\n');(out/'core_metadata.json').write_text(json.dumps(cores,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['receipts','contracts']},indent=1))
