#!/usr/bin/env python3
"""Opt-in exact CLOSED NCH4/READ1/FILL1 source simulation, including HARD mode.

Legacy s7 HARD simulation remains diagnostic0/0. Physical synthesis still has no
parameter override: its named closed leaf is baked1/1. This successor emits the
same explicit1/1 under OT_S5_HARD only when OT_S8_SIM is set by its bench.
"""
import json,sys
from pathlib import Path
import gen_slice7_lp_spec as g7
ROOT=g7.ROOT
OUT_DIR='rtl/qwen_dv/s5/s8/lp'
REC_DIR='results/arch/codex_slice2_native_1021/s8'
CHILD_SOURCES=[x for x in g7.CHILD_SOURCES if x not in ['rtl/qwen_dv/s5/p3/qfd_dv_s5_suvm_su8p3.sv','rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q.sv']]+[
    'rtl/qwen_dv/s5/s8/'+x+'.sv' for x in ['qfd_dv_s8_suvm_rp1','qfd_dv_s8_vm8q_rp1','qfd_dv_s8_crh_rp1','qfd_dv_s8_rp1','qfd_dv_s8_fdn_arf1']]

def make_flat():
    import gen_slice8_rp_source
    gen_slice8_rp_source.main()
    g7.make_flat()
    text=g7.FLAT6.read_text().replace('module qfd_dv_s7_flat (','module qfd_dv_s8_flat (',1)
    old='`ifndef OT_S5_HARD\n        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))\n`endif'
    new='`ifdef OT_S8_SIM\n        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))\n`else\n'+old+'\n`endif'
    assert text.count(old)==32
    text=text.replace(old,new)
    text=text.replace('qfd_dv_s6_fdn u_fdn','qfd_dv_s8_fdn_arf1 u_fdn').replace('qfd_dv_s5_suvm_su8p3 u_suvm','qfd_dv_s8_suvm_rp1 u_suvm')
    ctl='qfd_dv_s5_ctl_repair4_leaf u_ctl (.ck(ck), .rst_n(rst_n), .cmd_q(cmd_q), .chd_q(chd_q),'
    assert ctl in text
    adapter="""wire[115:0]rp_ctl_cmd;wire[1037:0]rp_ctl_chd;wire rp_fault,rp_tw_we;
    wire[1:0]rp_tw_kind;wire[23:0]rp_tw_addr;wire[1023:0]rp_tw_data;
    qfd_dv_s8_rp1 u_rp(.ck(ck),.rst_n(rst_n),.cmd_q(cmd_q),.chd_q(chd_q),
      .tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data),
      .ctl_cmd(rp_ctl_cmd),.ctl_chd(rp_ctl_chd),.vtw_we(rp_tw_we),.vtw_kind(rp_tw_kind),
      .vtw_addr(rp_tw_addr),.vtw_data(rp_tw_data),.fault(rp_fault));
    """
    text=text.replace(ctl,adapter+ctl.replace('.cmd_q(cmd_q), .chd_q(chd_q)','.cmd_q(rp_ctl_cmd), .chd_q(rp_ctl_chd)'))
    text=text.replace('.hd_fault(fch0), .pc_bad(pc_bad)', '.hd_fault(fch0), .pc_bad(pc_bad | rp_fault)')
    # Only suvm gets multiplexed writes; stream retains its original independent write outputs.
    a=text.index('qfd_dv_s8_suvm_rp1 u_suvm');b=text.index('qfd_dv_s5_red2_leaf u_red',a)
    sub=text[a:b]
    for port in ['tw_we','tw_kind','tw_addr','tw_data']:sub=sub.replace('.'+port+'('+port+')','.'+port+'(rp_'+port+')')
    text=text[:a]+sub+text[b:]
    path=ROOT/'rtl/qwen_dv/s5/s8/qfd_dv_s8_flat.sv' ;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('// Opt-in s8: actual CLOSED hard-leaf1/1 simulation; physical baked1/1.\n'+text)

def base_spec(name,D,E):
    s=g7.base_spec(name,D,E)
    s.update(top='qfd_dv_s8_flat',sources=['rtl/qwen_dv/s5/s8/qfd_dv_s8_flat.sv'],out_dir=OUT_DIR,record_dir=REC_DIR,child_sources=CHILD_SOURCES)
    for reg in s['regions']:
        if reg['name']=='r_ctl':reg['insts'].append('u_rp')
    s['why']='Opt-in s8 hard-leaf actual1/1; same stages/regions as s7; compiler ages require measured selected benchmark.'
    return s

def main():
    make_flat()
    for name,D,E in [('qfd_dv_s8b',8,4),('qfd_dv_s8',4,2)]:
        s=base_spec(name,D,E);s['lag_pins'],p=g7.g5.lag_pins(s)
        path=ROOT/f'tools/landed_parent/specs/{name}.json';path.write_text(json.dumps(s,indent=1)+'\n')
        if '--gen' in sys.argv:
            g7.lp.gen(g7.lp.load(str(path)))
            d=ROOT/OUT_DIR
            # Generated shell intentionally receives exact-source simulation flag.
            f=d/f'{name}_lp_bench.sh';f.write_text(f.read_text().replace('-DOT_S5_HARD','-DOT_S5_HARD -DOT_S8_SIM'))
            if name!='qfd_dv_s8':
                f=d/'qfd_dv_s8_flat_lagref.sv';(d/f'{name}_flat_lagref.sv').write_text(f.read_text().replace('module qfd_dv_s8_flat_lagref',f'module {name}_flat_lagref'))
                for f in [d/f'tb_{name}_lp.sv',d/f'{name}_lp_bench.sh']:
                    f.write_text(f.read_text().replace('qfd_dv_s8_flat_lagref',f'{name}_flat_lagref'))
        print(name,len(p['lands']),'landings; hard-leaf explicit1/1 simulation')
if __name__=='__main__':main()
