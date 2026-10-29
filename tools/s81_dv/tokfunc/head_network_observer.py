#!/usr/bin/env python3
"""Read-only diagnostics around an existing exact Verilated HEAD component.

Retains every original compiled RTL object. Only main is renamed in a new
archive and replaced with the same event loop plus read-only state logging.
No RTL, timing, signal assignment or existing failed result is modified.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path

def build(obj,out):
    obj=obj.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    main=(obj/'Vtb_s81sl_beat__main.cpp').read_text()
    main=main.replace('#include "Vtb_s81sl_beat.h"','#include "Vtb_s81sl_beat.h"\n#include "Vtb_s81sl_beat___024root.h"\n#include "Vtb_s81sl_beat_ot_s81dv_xfin.h"\n#include <cstring>')
    main=main.replace('    // Simulate until $finish','''    int previous=-1; bool observed[16]={}; bool stop=false;
    for(int arg=1;arg<argc;arg++) if(!strcmp(argv[arg],"+DIAG_STOP_ON_FAULT=1"))stop=true;
    // Simulate until $finish''')
    ptrs=','.join(f'topp->rootp->__PVT__tb_s81sl_beat__DOT__xf{i}'for i in range(16))
    code='''
        if(int(topp->rootp->tb_s81sl_beat__DOT__cyc)!=previous){
          previous=topp->rootp->tb_s81sl_beat__DOT__cyc;
          Vtb_s81sl_beat_ot_s81dv_xfin* nodes[16]={PTRS};
          for(int sid=0;sid<16;sid++){
            auto p=nodes[sid];
            if(p->__PVT__go_c)printf("OBS_GO sid%d cycle%d\\n",sid,previous);
            if(p->__PVT__inj_v)printf("OBS_INJECT sid%d cycle%d\\n",sid,previous);
            if(p->__PVT__u_x__DOT__jv&&(p->__PVT__u_x__DOT__fe||p->__PVT__u_x__DOT__fw))
              printf("OBS_NX_COLLISION sid%d cycle%d jv%d fe%d fw%d base%d\\n",sid,previous,p->__PVT__u_x__DOT__jv,p->__PVT__u_x__DOT__fe,p->__PVT__u_x__DOT__fw,p->__PVT__u_x__DOT__jb);
            if(p->rb_v)printf("OBS_RSTD sid%d cycle%d\\n",sid,previous);
            if(p->fault&&!observed[sid]){
              printf("OBS_XFIN_FAULT sid%d cycle%d exchangefault%d collectorflag%d\\n",sid,previous,p->__PVT__xf,p->__PVT__eflt);
              observed[sid]=true;fflush(stdout);if(stop)return 17;
            }
          }
          fflush(stdout);
        }
'''.replace('PTRS',ptrs)
    assert main.count('        topp->eval();')==1
    main=main.replace('        topp->eval();','        topp->eval();'+code)
    (out/'observer_main.cpp').write_text(main)
    inc=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
    commands=[['objcopy','--redefine-sym','main=original_component_main',str(obj/'Vtb_s81sl_beat__ALL.a'),str(out/'rtl_original_objects.a')],
              ['g++','-std=c++20','-O0','-I'+str(obj),'-I'+str(inc),'-I'+str(inc/'vltstd'),'-c',str(out/'observer_main.cpp'),'-o',str(out/'observer_main.o')],
              ['g++',str(out/'observer_main.o'),*[str(obj/f)for f in('verilated.o','verilated_timing.o','verilated_threads.o')],str(out/'rtl_original_objects.a'),'-pthread','-latomic','-o',str(out/'observe')]]
    with(out/'build.log').open('w')as log:
        for command in commands:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    record=dict(scope='READ_ONLY_CPP_OBSERVER_UNCHANGED_RTL_OBJECTS',original_object_archive=str(obj/'Vtb_s81sl_beat__ALL.a'),
        original_archive_sha256=hashlib.sha256((obj/'Vtb_s81sl_beat__ALL.a').read_bytes()).hexdigest(),
        original_binary_sha256=hashlib.sha256((obj/'Vtb_s81sl_beat').read_bytes()).hexdigest(),
        modifications='only main entry symbol renamed in copied archive; original main replaced by identical event loop plus reads/prints; optional diagnostic stop',rtl_assignments_changed=False)
    (out/'observer_record.json').write_text(json.dumps(record,indent=1)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--obj',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.obj,a.out)
