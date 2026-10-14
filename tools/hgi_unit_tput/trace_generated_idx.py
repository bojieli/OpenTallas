#!/usr/bin/env python3
"""Observe an already compiled Verilator IDX native model without changing RTL.
Run through ot-run on the host holding OBJ. Outputs a separate observer binary,
original/model hashes and phase CSV. Generated RTL objects remain untouched.
Usage: trace_generated_idx.py OBJ VECTOR OUT
"""
import hashlib,json,re,subprocess,sys
from pathlib import Path
obj,vec,out=map(lambda s:Path(s).resolve(),sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
header=(obj/'Vtb_hgi_e2e___024root.h').read_text()
watch=[]
for typ,width,name in re.findall(r'(CData|SData|IData|QData)/\*(\d+):0\*/ (\w+);',header):
 if name.startswith('__V'):continue
 short=name.removeprefix('tb_hgi_e2e__DOT__g_idx__DOT__')
 if not name.startswith('tb_hgi_e2e__DOT__g_idx__DOT__'):continue
 tails=('u_kc__DOT__u_ct__DOT__go','u_kc__DOT__u_ct__DOT__st','u_qa__DOT__wts_ok','u_qa__DOT__swp','u_qa__DOT__qa_done','u_pk__DOT__dcred','u_pk__DOT__cfn','u_pk__DOT__c_pop','u_wp__DOT__dqn','u_wp__DOT__d_go','u_wp__DOT__dc_pending','u_wp__DOT__w_used','u_wp__DOT__w_out','u_wp__DOT__fl_done','u_tk2__DOT__st','u_sel__DOT__core__DOT__qbv','u_sel__DOT__core__DOT__fsv','u_sel__DOT__core__DOT__c_take','u_sel__DOT__core__DOT__ccr','u_sel__DOT__core__DOT__fire','u_sel__DOT__core__DOT__active','u_sel__DOT__core__DOT__ev','u_index__DOT__pk_done','u_index__DOT__wp_idle','u_index__DOT__flush')
 if any(short.endswith(x) for x in tails) or ('u_idxn__DOT__gs__' in short and short.endswith('u_s__DOT__core__DOT__qloaded')):watch.append((short,name))
if len(watch)<20:raise SystemExit('missing compiled model phase fields: '+str(len(watch)))
main=(obj/'Vtb_hgi_e2e__main.cpp').read_text().replace('#include "Vtb_hgi_e2e.h"','#include "Vtb_hgi_e2e.h"\n#include "Vtb_hgi_e2e___024root.h"\n#include <cstdio>')
main=main.replace('    // Simulate until $finish',f'    FILE* phase = fopen({json.dumps(str(out/"phase.csv"))}, "w");\n    uint64_t lastcyc=UINT64_MAX;\n    // Simulate until $finish')
cols='cycle,'+','.join(a for a,b in watch)
main=main.replace('    uint64_t lastcyc',f'    fprintf(phase, "%s\\n", {json.dumps(cols)});\n    uint64_t lastcyc')
vals=', '.join('static_cast<unsigned long long>(topp->rootp->'+b+')' for a,b in watch)
fmt='%llu,'+','.join('%llu' for a,b in watch)+'\\n'
observe=f'\n        auto* r=topp->rootp;\n        if (r->tb_hgi_e2e__DOT__clk && r->tb_hgi_e2e__DOT__cyc!=lastcyc) {{\n            lastcyc=r->tb_hgi_e2e__DOT__cyc;\n            fprintf(phase, "{fmt}", static_cast<unsigned long long>(lastcyc), {vals});\n        }}\n'
main=main.replace('        topp->eval();','        topp->eval();'+observe).replace('    topp->final();','    topp->final();\n    fclose(phase);')
cpp=out/'trace_main.cpp';cpp.write_text(main)
mk=(obj/'Vtb_hgi_e2e.mk').read_text()
ver=Path(re.search(r'^VERILATOR_ROOT\s*:?=\s*(.+)$',mk,re.M).group(1).strip())/'include'
subprocess.run(['g++','-std=c++20','-Os','-pthread','-I'+str(ver),'-I'+str(ver/'vltstd'),'-I'+str(obj),'-c',str(cpp),'-o',str(out/'trace_main.o')],check=True)
objects=[obj/x for x in ['hgi_e2e_dpi.o','verilated.o','verilated_dpi.o','verilated_timing.o','verilated_threads.o','Vtb_hgi_e2e__ALL.a']]
subprocess.run(['g++','-pthread',str(out/'trace_main.o'),*map(str,objects),'-latomic','-o',str(out/'tb_trace')],check=True)
provenance={'obj':str(obj),'vector':str(vec),'observer_fields':[a for a,b in watch],'sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in objects+[cpp,obj/'Vtb_hgi_e2e__main.cpp',obj/'Vtb_hgi_e2e___024root.h']}}
(out/'provenance.json').write_text(json.dumps(provenance,indent=1)+'\n')
with (out/'run.log').open('w') as f:rc=subprocess.run([str(out/'tb_trace'),'+DIR='+str(vec),'+OUT='+str(out/'e2e_records.txt')],cwd=out,stdout=f,stderr=subprocess.STDOUT).returncode
raise SystemExit(rc)
