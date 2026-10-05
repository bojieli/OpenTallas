#!/usr/bin/env python3
"""Prepare a passive host relink against retained TP4 archives. Never build/run."""
import argparse,base64,gzip,json,re
from pathlib import Path
from qwen_rom_program_identity import ROOT,sha,decoded
from qwen_rom_kv_launch_readiness import FIELDS
B=ROOT/'results/uarch/qwen_rom_source_observer_20261002'
CAP=ROOT/'results/rtl/qwen_rom_TP4_terminal_20261002/capture.json'
def once(text,anchor,value):
 if text.count(anchor)!=1:raise ValueError('unique host/source anchor: '+anchor)
 return text.replace(anchor,value)
def prepare(out):
 cap=json.loads(CAP.read_text());src=decoded(cap['files']['source/rtl/test/qwen_rom_runtime/qwen_rom_rt.cpp']).decode()
 header=gzip.decompress((B/'inputs/Vdie___024root.h.gz').read_bytes()).decode()
 prefix='ot_qwen_rom_rt_die__DOT__';core=prefix+'core__DOT__';seq=prefix+'seq__DOT__'
 names=[core+'issue',core+'me_go',core+'d_unit',core+'pc',seq+'st',seq+'seg',prefix+'core_done',core+'me_idle',core+'su_idle',core+'su_ready']+[core+'me_'+n for n,w in FIELDS]
 for name in names:
  if not re.search(r'\b'+re.escape(name)+r';',header):raise ValueError('actual generated endpoint absent: '+name)
 literal=decoded(cap['files']['source/rtl/rom/ot_rom_tp_seq.sv']).decode()
 if 'assign core_start = (st == S_RUN);' not in literal or 'S_RUN = 3' not in literal:raise ValueError('actual source core_start predicate')
 core_src=decoded(cap['files']['source/rtl/hdc/ot_hdc_core_vector_weight.sv']).decode()
 for anchor in ["assign su_go = issue && (d_unit == 2'd2);","assign me_go = issue && (d_unit == 2'd1);","if (issue) pc <= pc + 1'b1;"]:
  if anchor not in core_src:raise ValueError('actual source issue/PC contract')
 fields=','.join('r->'+core+'me_'+n for n,w in FIELDS)
 accessor=f'''\n#if QROM_OBSERVER
static void qrom_pre(QromObserver& obs, Vdie& t,long edge,size_t stage,int rank) {{
 if(stage>=36)return;
 auto* r=t.rootp;
 obs.control(edge,stage,rank,r->{core}me_idle | (r->{core}su_idle<<1) | (r->{core}su_ready<<2));
 const unsigned seg=r->{seq}seg,base=t.prog_base;
 const bool start=r->{seq}st==3; // exact captured assign core_start = st==S_RUN
 if(start) {{if(obs.active[rank])throw std::runtime_error("overlapping source core_start");obs.active[rank]=true;obs.dispatch('S',edge,stage,rank,seg,base,t.desc_q);}}
 else if(obs.active[rank] && r->{prefix}core_done){{obs.dispatch('D',edge,stage,rank,seg,base,t.desc_q);obs.active[rank]=false;}}
 if(r->{core}issue) {{
  if(!obs.active[rank])throw std::runtime_error("accepted issue without dispatch");
  unsigned fields[24]={{{fields}}};
  const unsigned unit=r->{core}d_unit;
  if(bool(r->{core}me_go)!=(unit==1))throw std::runtime_error("actual ME go mismatch");
  obs.issue(edge,stage,rank,seg,base,r->{core}pc,unit,fields);
 }}
}}
#endif
'''
 src=once(src,'#include "Vdie.h"','#include "Vdie.h"\n#include "qwen_rom_observer.hpp"')
 src=once(src,'int main(int argc, char** argv) {',accessor+'\nint main(int argc, char** argv) {\n#if QROM_OBSERVER\n    static_assert(D==4 && G==6144 && W==16 && TG==4 && SW==64 && TCUT==7 && CB==5 && XVM==1, "observer frozen TP4 source geometry");\n    QromObserver observer;\n#endif')
 src=once(src,'                stage_done = true;','''                stage_done = true;
#if QROM_OBSERVER
                if(cur<36)for(int d=0;d<D;++d)observer.snapshot(edges,cur,d,mem[d].kv);
#endif''')
 src=once(src,'            Vdie& t = *die[d];\n            auto& m = mem[d];', '''            Vdie& t = *die[d];
#if QROM_OBSERVER
            qrom_pre(observer,t,edges,cur,d);
#endif
            auto& m = mem[d];''')
 src=once(src,'            for (auto& w : kvw[d]) if (w.a < KV_ELEMS) m.kv[w.a] = w.v;', '''            for (auto& w : kvw[d]) if (w.a < KV_ELEMS) {
                m.kv[w.a] = w.v;
#if QROM_OBSERVER
                if(cur<36)observer.write(edges-1,cur,d,w.a,w.v);
#endif
            }''')
 src=once(src,'                            for (int j = 0; j < W; j++) r.kv_q[(i * TG + g) * W + j] = (a < KV_ELEMS / W) ? m.kv[a * W + j] : 0;', '                            for (int j = 0; j < W; j++) r.kv_q[(i * TG + g) * W + j] = (a < KV_ELEMS / W) ? m.kv[a * W + j] : 0;\n#if QROM_OBSERVER\n                            if(cur<36)observer.read(edges,cur,d,i,g,a,&r.kv_q[(i * TG + g) * W]);\n#endif')
 out.mkdir(exist_ok=False)
 stage_bytes=decoded(cap['files']['stages.txt'])
 rows=stage_bytes.decode().splitlines()
 if [r.split()[0] for r in rows]!=[f'L{i}' for i in range(36)]+['head']:raise ValueError('exact original37stage sequence')
 # No repeated head/token campaign: retain all36 connected layers only.
 (out/'stages.txt').write_text('\n'.join(rows[:36])+'\n')
 preload=gzip.decompress((B/'inputs/retained-preload.hex.gz').read_bytes())
 oracle=json.loads(decoded(cap['files']['oracle.json']))
 if sha(preload)!=oracle['x_preload_sha256']:raise ValueError('exact captured input preload')
 (out/'preload.hex').write_bytes(preload)
 (out/'qwen_rom_rt_observed.cpp').write_text(src)
 (out/'qwen_rom_observer.hpp').write_bytes((ROOT/'rtl/test/qwen_rom_runtime/observer/qwen_rom_observer.hpp').read_bytes())
 record={'status':'PREPARED_NOT_BUILD_OR_RUN_ADMITTED','historical_only':True,'source_program_scope':'TP4pos0/SU64/SMIN7/BD41 frozen captured source; connectedL0..L35 only, no head replay','original_host_sha256':cap['files']['source/rtl/test/qwen_rom_runtime/qwen_rom_rt.cpp']['sha256'],'instrumented_host_sha256':sha(src.encode()),'preload_sha256':sha(preload),'stages_sha256':sha((out/'stages.txt').read_bytes()),'generated_root_endpoints':names,'source_predicates':{'core_start':'seq.st==3, source literal assign','su_go':'actual issue&&d_unit==2, source literal assign','me_go':'actual retained wire, checked against accepted d_unit'},'RTL_or_model_changed':False,'default_enabled':False,'build_launched':False,'runtime_launched':False,'required_preprocessor_flag':'-DQROM_OBSERVER=1','required_environment':'RT_QROM_JOURNAL=<exclusive-new-path>'}
 (out/'preparation.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');return record

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)
if __name__=='__main__':main()
