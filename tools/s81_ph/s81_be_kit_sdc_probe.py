#!/usr/bin/env python3
"""Validate successor SDCTcl against actual BE pin identities, without P&R."""
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import child_lint as C

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,default=Path('/tmp/be_m7_sdc_syntax'));ap.add_argument('--log',type=Path,required=True);a=ap.parse_args()
    w=a.work.resolve();w.mkdir(exist_ok=True)
    m=C.parse_lef((ROOT/'results/arch/s81_be_native_mc_placement_1014/inputs/be_sl_c15e2bf6a.lef').read_text());groups={}
    for n,p in m['pins'].items():
        if C.is_pg(n,p):continue
        base=n.split('[')[0];bit=int(n.split('[')[1][:-1]) if '[' in n else None
        groups.setdefault(base,dict(direction=p['direction'],bits=[]))['bits'].append(bit)
    ports=[];con=[]
    for n,g in groups.items():
        width='' if g['bits']==[None] else f'[{max(g["bits"])}:0] '
        ports.append(g['direction'].lower()+' wire '+width+n);con.append(f'.{n}({n})')
    (w/'top.v').write_text('module sdc_top('+',\n'.join(ports)+');\ndsfd_vm_be_sl u('+','.join(con)+');\nendmodule\n')
    (w/'check.tcl').write_text('''read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/results/arch/s81_be_native_mc_placement_1014/inputs/be_sl_c15e2bf6a.lef
read_liberty /src/physical/s81_ph_views/vm_master/routes/s81vm-besl4-c15e2bf6a-tc-rd-pd45/dsfd_vm_be_sl/dsfd_vm_be_sl_tt.lib
read_verilog /work/top.v
link_design sdc_top
create_clock -name core_clk -period 1111.1 [get_ports {ck*}]
source /src/physical/s81_be_access_m7_candidate/margin.sdc
foreach name {core_clk str_clk ot_lb_v_core_clk ot_lb_v_str_clk} { puts "KIT_CLOCK $name [get_property [get_clocks $name] period]" }
puts KIT_SDC_OK
exit
''')
    cmd=['docker','run','--rm','-u',f'{os.getuid()}:{os.getgid()}','-v',f'{ROOT}:/src:ro','-v',f'{w}:/work','openroad/orfs:asap7lock','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/work/check.tcl']
    with a.log.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    ok=r.returncode==0 and 'KIT_SDC_OK' in a.log.read_text()
    print(json.dumps(dict(sdc_syntax_pass=ok,physical_timing_qualification=False)));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
