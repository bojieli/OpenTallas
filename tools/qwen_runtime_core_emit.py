import pathlib,re,json,hashlib,argparse,subprocess
ap=argparse.ArgumentParser(description="Export simulation-only u_me boundary without changing hardware")
ap.add_argument('--source-root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1])
ap.add_argument('--revision',default='a80d6a30')
ap.add_argument('--out',type=pathlib.Path,required=True)
args=ap.parse_args();root=args.source_root;out=args.out;out.mkdir(parents=True,exist_ok=True)
def source(p):return subprocess.check_output(['git','show',f'{args.revision}:{p}'],cwd=root)
core=source('rtl/hdc/ot_hdc_core_vector_weight.sv').decode();mat=source('rtl/hdc/ot_hdc_matvec.sv').decode()
header=mat[mat.index(') (')+3:mat.index('\n);')]
ports=re.findall(r'\b(input|output)\s+(?:wire|reg)\s*(\[[^\n]+?\])?\s*(\w+)\s*[,\n]',header+'\n')
start=core.index('    ot_hdc_matvec #(');end=core.index(');',start)+2
instance=core[start:end]
bindings=dict(re.findall(r'\.(\w+)\((\w+)\)',instance[instance.index('u_me ('):]))
assert set(bindings)=={p[2] for p in ports},(set(bindings)-{p[2] for p in ports},{p[2] for p in ports}-set(bindings))
newports=[];assign=[];contract=[]
for direction,width,name in ports:
 if name in ('clk','rst_n'):continue
 flow='output' if direction=='input' else 'input'
 newports.append(f'    ,{flow} wire {width or ""} ext_me_{name}')
 assign.append(f'    assign '+(f'ext_me_{name} = {bindings[name]}' if direction=='input' else f'{bindings[name]} = ext_me_{name}')+';')
 contract.append({'name':'ext_me_'+name,'direction':flow,'width_expression':width or '1','original_core_net':bindings[name],'matvec_port':name})
core=core[:start]+'\n'.join(assign)+core[end:]
core=core.replace('module ot_hdc_core_vector_weight #(','module replay_core_control #(',1)
core=core.replace('\n);','\n'+'\n'.join(newports)+'\n);',1)
(out/'replay_core_control.sv').write_text(core)
(out/'port_contract.json').write_text(json.dumps({'status':'generated_not_yet_compiled','ports':contract,'source_sha256':{p:hashlib.sha256(source(p)).hexdigest() for p in ['rtl/hdc/ot_hdc_core_vector_weight.sv','rtl/hdc/ot_hdc_matvec.sv']},'semantics':'u_me removed only from generated simulation controller; each original net exported without registers or queues; host drives all clocks simultaneously'},indent=2)+'\n')
print('ports',len(contract))
