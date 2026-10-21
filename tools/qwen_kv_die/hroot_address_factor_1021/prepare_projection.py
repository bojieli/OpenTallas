#!/usr/bin/env python3
"""Extract actual changed production address expressions, no hand proxy equations."""
from pathlib import Path
import re,sys,hashlib,json,difflib
old=Path(sys.argv[1]).read_text();new=Path(sys.argv[2]).read_text();out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
helper='\n'.join(re.findall(r'    function automatic \[31:0\] af_.*?    endfunction',new,re.S));assert len(re.findall('function automatic',helper))==3
header='module NAME(input[255:0] st_d,input[31:0] st_row,s_gs,input[2:0] s_stk,st_ph,input[4:0] st_sec,output[319:0] addresses); localparam AW=32;\n'
recs=[]
for name,s in [('original',old),('candidate',new)]:
 body=s[s.index('    wire [31:0] s_ring ='):s.index('    // APIPE: per-row address terms registered')]
 # Four actual st_wa RHS assignments in RAW/ROWS/IKEY code/IKEY scale order.
 section=s[s.index('    always @* begin\n        st_pop'):s.index('    wire [5:0] ra_pop') if '    wire [5:0] ra_pop' in s else s.index('    assign w_addr')]
 rhs=re.findall(r'st_wa = (.*?);',section);assert len(rhs)==5,len(rhs);rhs=rhs[1:]
 body+='\nwire[31:0] u_raddr=s_raddr,u_kcode=k_code,u_kscal=k_scal;\n'
 for i,x in enumerate(rhs):body+=f'wire[31:0] final{i} = {x};\n'
 body+='assign addresses={s_local,s_rbase,s_raddr,k_blk,k_code,k_scal,final0,final1,final2,final3};\nendmodule\n'
 (out/(name+'.sv')).write_text(header.replace('NAME',name)+(helper+'\n' if name=='candidate' else '')+body)
# Source edit audit: only helper insertion and these ten address-expression lines.
stripped=new[:new.index('    // HROOT address factoring:')]+new[new.index('    wire [31:0] s_ring ='):]
a=old.splitlines(keepends=True);b=stripped.splitlines(keepends=True);pairs=[]
for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
 if tag=='equal':continue
 assert tag=='replace' and j-i==l-k
 for x,y in zip(a[i:j],b[k:l]):
  assert ('wire [31:0] ' in x and any(f' {v} =' in x for v in ['s_local','s_rbase','s_raddr','k_blk','k_code','k_scal'])) or 'st_wa =' in x
  assert 'af_' in y;pairs.append({'original':x.rstrip(),'candidate':y.rstrip()})
assert len(pairs)==10
rec={'original_sha256':hashlib.sha256(old.encode()).hexdigest(),'candidate_sha256':hashlib.sha256(new.encode()).hexdigest(),'changed_expression_lines':pairs,'other_source_bytes_identical_after_replacement':True,'scope':'actual production combinational address projection over arbitrary state cutpoints; not native copy convergence, CDC or timing'}
(out/'source_edit_audit.json').write_text(json.dumps(rec,indent=2)+'\n')
