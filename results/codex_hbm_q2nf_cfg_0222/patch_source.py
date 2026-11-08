#!/usr/bin/env python3
"""Opt-in same-cycle replacement of the proved Q2NF issuer_cfg D cone."""
from pathlib import Path
import re,sys
P='u_body.g_q2.n_u_fj.u_fj.u.u_program.'
def patch(s):
 prefix='\\'+P
 old=[l for l in s.splitlines()if l.strip().startswith('assign { _24896_')and prefix+'draining'in l]
 assert len(old)==1, 'expected actual37-bit issuer_cfg next-state driver'
 old=old[0];lhs=old.split(' = ',1)[0].strip()[len('assign '):]
 assert '_24867_'in lhs and 'reg [36:0] _55059_;'in s
 def vec(n,w):return '{ '+', '.join('\\'+P+n+'['+str(i)+'] 'for i in reversed(range(w)))+' }'
 block='\n'.join(['`ifdef OT_Q2NF_CFG_CASE',
 '  // Same combinational function,1615free inputs proved against the extracted native D cone;0newcycles.',
 '  wire [36:0] ot_q2nf_cfg_y;',
 '  ot_q2nf_cfg_case u_q2nf_cfg_case (',
 '    .step('+vec('step',6)+'),',
 '    .row('+vec('row',8)+'),',
 '    .assembly('+vec('assembly',1536)+'),',
 '    .metadata('+vec('metadata',64)+'),',
 '    .draining('+prefix+'draining ), .y(ot_q2nf_cfg_y));',
 '  assign '+lhs+' = ot_q2nf_cfg_y;',
 '`else',old,'`endif'])
 out=s.replace(old,block,1);assert out.replace(block,old,1)==s
 return out
if __name__=='__main__':
 src,dst=map(Path,sys.argv[1:]);assert not dst.exists();dst.write_text(patch(src.read_text()))
