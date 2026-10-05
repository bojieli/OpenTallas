#!/usr/bin/env python3
"""Extract actual companion issue gates and exercise the production KV block producer/drain."""
import pathlib,re,subprocess,json,hashlib,sys
root=pathlib.Path(__file__).resolve().parents[1]
core=root/(sys.argv[2] if len(sys.argv)>2 else 'rtl/w17_runtime/hdc/v41x/pc21/ot_hdc_core_v41x.sv')
text=core.read_text()
# Bind actual shared predicate usage; no hand-maintained gate replica.
assert 'S_DEC: if (win_admit) st <= S_ISSUE;' in text
assert 'win_admit)) begin' in text
parts=[re.search(r'    wire '+name+r'\s*=.*?;',text,re.S).group(0) for name in ['win_su_match','win_admit','kv_gate']]
work=pathlib.Path(sys.argv[1]);work.mkdir(exist_ok=False)
records=[]
for mutant in [False,True]:
 tag='legacy_gate_mutant' if mutant else 'corrected'
 fragment='\n'.join(parts)
 if mutant:fragment=fragment.replace('                   win_admit;','                   (!FULL_SHAPE || win_idle);')
 case=work/tag;case.mkdir();(case/'actual_admission.svh').write_text(fragment+'\n')
 cmd=['iverilog','-g2012','-s','tb_pc21_window_admission','-I'+str(case),'-o',str(case/'sim'),str(root/'rtl/test/w17/tb_pc21_window_admission.sv'),str(root/'rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv')]
 c=subprocess.run(cmd,capture_output=True,text=True);(case/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
 p=subprocess.run(['timeout','15s','vvp',str(case/'sim')],capture_output=True,text=True);(case/'run.log').write_text(p.stdout+p.stderr)
 assert (p.returncode!=0 and 'matching FULL producer drain blocked' in p.stdout) if mutant else (p.returncode==0 and 'PASS PC21' in p.stdout),p.stdout+p.stderr
 records.append(dict(case=tag,returncode=p.returncode,output=p.stdout,expected_rejection=mutant))
inputs=[core,root/'rtl/test/w17/tb_pc21_window_admission.sv',root/'rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv',pathlib.Path(__file__)]
r=dict(verdict='PASS_FOCUSED_CONTROL_AND_BLOCK_EXACT',legacy_mutant_rejected=True,cases=records,pins={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},scope='actual companion gate expressions + production16-block producer/drain; not fullcore/currentL0/L20/token/P&R',adopt=False)
(work/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
