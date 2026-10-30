"""Source-authoritative mapped combinational equivalence of exact flit functions."""
from pathlib import Path
import re,subprocess,json,hashlib
from pure_flit import fix
P=Path(__file__).resolve().parent;O=P/'flit_boolean';O.mkdir(exist_ok=True)
old=(P/'native_ring_api.sv').read_text();new=fix(old)
receipts={}
for label,text in [('old',old),('new',new)]:
 f=re.search(r'function automatic \[279:0\] flit\b.*?endfunction',text,re.S)[0]
 header=f'''module fn_{label}(
 input wire gath,tx_result,input wire[1:0]qid,tx_dst,input wire[3:0]tx_ttl,
 input wire[2:0]tag,input wire[255:0]data,input wire signed[31:0]MUT_TAG,
 output wire[279:0]y0,y1);
'''
 args=',gath,tx_result,qid,tx_dst,tx_ttl,MUT_TAG'if label=='new'else''
 s=header+f+'\n'+f'assign y0=flit(0,tag,data{args});\nassign y1=flit(1,tag,data{args});\nendmodule\n'
 (O/(label+'.sv')).write_text(s);receipts[label]={'function_sha256':hashlib.sha256(f.encode()).hexdigest(),'source_sha256':hashlib.sha256(text.encode()).hexdigest()}
ys=[]
for label in ('old','new'):
 ys += [f'read_verilog -sv /work/flit_boolean/{label}.sv',f'prep -top fn_{label}','techmap','opt','abc -g simple','opt_clean',f'write_json /work/flit_boolean/{label}_mapped.json',f'design -stash {label}']
ys += ['design -reset','design -copy-from old -as gold fn_old','design -copy-from new -as gate fn_new','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple -undef','equiv_status -assert']
(O/'equiv.ys').write_text('\n'.join(ys)+'\n')
cmd=['docker','run','--rm','--name','hbm-face-flit-0336','--cpus','2','--memory','4g','-v',str(P)+':/work','openroad/orfs:asap7lock','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec yosys -Q -s /work/flit_boolean/equiv.ys']
r=subprocess.run(cmd,text=True,capture_output=True);log=r.stdout+r.stderr;(O/'equiv.log').write_text(log)
passed=r.returncode==0 and'Equivalence successfully proven!'in log
(O/'receipt.json').write_text(json.dumps({'returncode':r.returncode,'verdict':'PASS'if passed else'FAIL','scope':'exact actualold/new flit sourcefunctions, mappedcombinational, d0/1, symbolicALLruntimeinputs and32bitMUT_TAG; notwholemoduleformal','outputs':560,'source':receipts},indent=2)+'\n')
print('FLIT_MAPPED_EQ',r.returncode,'PASS'if passed else'FAIL');print(log[-600:])
if not passed:raise SystemExit(1)
