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
    'rtl/qwen_dv/s5/s8/'+x+'.sv' for x in ['qfd_dv_s8_suvm_rp1','qfd_dv_s8_vm8q_rp1','qfd_dv_s8_crh_rp1','qfd_dv_s8_rp1','qfd_dv_s8_fdn_arf1','qfd_dv_s8_station_tail1','qfd_dv_s8_station_safe','qfd_dv_s8_station_math_g','qfd_dv_s8_tap_bounded','qfd_dv_s8_tap_bounded_helpers']]+['rtl/common/landed_parent/ot_pl_land_field_copies.sv','rtl/common/landed_parent/ot_pl_land_n32.sv']

# Exact standalone station dependencies (5de01e82f kit), including its control
# publication helpers and real32x64 macro declaration. Parent census is not
# allowed to omit these just because the future physical child is unclosed.
CHILD_SOURCES=list(dict.fromkeys(CHILD_SOURCES+[
    'rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv',
    'rtl/qwen_dv/s5/s8/qfd_dv_s8_legacy_math_g.sv',
    'rtl/qwen_dv/qfd_dv_ring_delay.sv',
    'rtl/qwen_dv/qfd_dv_reset_tree.sv',
    'rtl/common/landed_parent/ot_pl_land_physical.sv',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v',
]))

def make_flat():
    import gen_slice8_rp_source
    gen_slice8_rp_source.main()
    import gen_s8_station_tail
    gen_s8_station_tail.main()
    # Imported legacy helper modules also enter this parent readset. Their
    # original names collide with the hard controller's scalar helper defs.
    # Rename every definition/reference together; source equations/FFs unchanged.
    legacy=(ROOT/'rtl/qwen_dv/qfd_dv_station_math_g.sv').read_text()
    (ROOT/'rtl/qwen_dv/s5/s8/qfd_dv_s8_legacy_math_g.sv').write_text(
        '// Parent-only namespace closure; equations and stages are original.\n'+
        legacy.replace('qfd_bmath_', 'qfd_s8legacy_bmath_'))
    g7.make_flat()
    text=g7.FLAT6.read_text().replace('module qfd_dv_s7_flat (','module qfd_dv_s8_flat (',1)
    text=text.replace('qfd_dv_redstn2_region u_r','qfd_dv_s8_station_tail1 u_r')
    assert text.count('qfd_dv_s8_station_tail1 u_r')==8
    old='`ifndef OT_S5_HARD\n        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))\n`endif'
    new='`ifdef OT_S8_SIM\n        #(.NCH(4), .READ_PIN_PIPE(1), .FILL_PIPE(1))\n`else\n'+old+'\n`endif'
    assert text.count(old)==32
    text=text.replace(old,new)
    text=text.replace('qfd_dv_s6_fdn u_fdn','qfd_dv_s8_fdn_arf1 u_fdn').replace('qfd_dv_s5_suvm_su8p3 u_suvm','qfd_dv_s8_suvm_rp1 u_suvm')
    text=text.replace('qfd_dv_s6_tap u_tap','qfd_dv_s8_tap_bounded u_tap')
    ta=text.index('qfd_dv_s8_tap_bounded u_tap');tb=text.index(');',ta)+2
    text=text[:ta]+text[ta:tb].replace('.xt_v(xt_v)', '.xt_vcopies({6{xt_v}})')+text[tb:]
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

def kept_fdn_selectors(path,D,E):
    """Private selector copies capture exactly the existing landing0 publication edge."""
    text=path.read_text()
    # Actual hard/soft child reset terminals exceed the old one-pin bin estimate:
    # census c4=45. Split its32 callers16/16 at the SAME final reset edge.
    import re
    pat=re.compile(r'(u_lprc_\w+ \(.ck\(ck_r_su\), .d\()lpr_r_su_c4(\))')
    matches=list(pat.finditer(text))
    assert len(matches)==32,len(matches)
    seen=[0]
    def reset_half(m):
        seen[0]+=1
        return m[1]+('lpr_r_su_c4' if seen[0]<=16 else 'lpr_r_su_c4b')+m[2]
    text=pat.sub(reset_half,text)
    text=text.replace('    // ---- LANDING 0:', '    wire lpr_r_su_c4b; ot_pl_land_rst_copy #(.ID(9002)) u_lpr_r_su_c4b(.ck(ck_r_su),.d(lpr_r_su_p),.q(lpr_r_su_c4b));\n    // ---- LANDING 0:',1)
    assert 'LANDING 0: chu_q r_fe -> r_fw' in text
    assert 'ot_pl_land_field_copies' not in text
    code='    // Same landing0 read edge; <=12 data bits (~24 mapped mux loads) per kept selector.\n'
    code+='    wire fdn_sel_rst; ot_pl_land_rst_copy #(.ID(9001)) u_fdn_sel_rst(.ck(ck_r_fw),.d(lpr_r_fw_p),.q(fdn_sel_rst));\n'
    for label,bit in [('ar',1094),('dd',547)]:
        chunk=bit//24
        code+=f'    wire [45:0] fdn_{label}_copies;\n'
        code+=f'    ot_pl_land_field_copies #(.COPIES(46),.D({D}),.K((MUT==2)?{E+1}:{E})) u_fdn_{label}_copies (.ck(ck_r_fw),.rsi(fdn_sel_rst),.bank({{'+', '.join(f'lpl_0_bank[{slot}*1095+{bit}]' for slot in reversed(range(D)))+'}),'
        code+=f'.vld(lpl_0_vld[{chunk}*{D}+:{D}]),.epo(lpl_0_epo),.o(fdn_{label}_copies));\n'
    key='    qfd_dv_s8_fdn_arf1 u_fdn ('
    replacement=code+'    qfd_dv_s8_fdn_arf1 #(.USE_SEL_COPIES(1)) u_fdn (.chu_ar_sel((MUT==1)?{46{chu_q[1094]}}:fdn_ar_copies), .chu_dd_sel((MUT==1)?{46{chu_q[547]}}:fdn_dd_copies), '
    assert key in text;text=text.replace(key,replacement,1);path.write_text(text)

def kept_tap_copies(path):
    """QKO-SLICE2 10-21: six kept xt_v landing readers (census w9: landing xt_v o 66 loads + TAP qd0/svc/arm decode).
    Each copy = ot_pl_land_local_r W=1 logic on the SAME landing bank/vld/epo, same rsi (lpr_r_tap_c4), same D/K:
    identical capture edge; bounded TAP caps each copy at <=32 loads."""
    import re
    text=path.read_text()
    m=re.search(r'ot_pl_land_chunk_r #\(\.W\(1\), \.D\((\d+)\), \.K\(([^)]*\)?)\), \.CHUNK_BITS\(24\)\) u_lpl_(\d+)_r \(\.ck\(ck_r_tap\), \.rsi\((\w+)\), \.bank\(lpl_\3_bank\), \.epo\(lpl_\3_epo\), \.vld\(lpl_\3_vld\), \.o\(lpl_\3_o\)\);\n    assign xt_v__l_r_tap = lpl_\3_o;',text)
    assert m,'xt_v landing not found'
    D,K,n,rsi=m[1],m[2],m[3],m[4]
    old='.xt_vcopies({6{xt_v__l_r_tap}})'
    assert text.count(old)==1
    code=(f'    // Six kept xt_v readers on landing {n}: same bank/vld/epo, rsi, D/K -> same capture edge as u_lpl_{n}_r.\n'
          f'    wire [5:0] tap_xtv_copies;\n'
          f'    ot_pl_land_field_copies #(.COPIES(6),.D({D}),.K({K})) u_tap_xtv_copies (.ck(ck_r_tap),.rsi({rsi}),'
          f'.bank(lpl_{n}_bank),.vld(lpl_{n}_vld),.epo(lpl_{n}_epo),.o(tap_xtv_copies));\n')
    key='    qfd_dv_s8_tap_bounded u_tap ('
    assert text.count(key)==1
    text=text.replace(key,code+key,1).replace(old,'.xt_vcopies(tap_xtv_copies)')
    path.write_text(text)

def main():
    make_flat()
    for name,D,E in [('qfd_dv_s8b',8,4),('qfd_dv_s8',4,2)]:
        s=base_spec(name,D,E);s['lag_pins'],p=g7.g5.lag_pins(s)
        path=ROOT/f'tools/landed_parent/specs/{name}.json';path.write_text(json.dumps(s,indent=1)+'\n')
        if '--gen' in sys.argv:
            g7.lp.gen(g7.lp.load(str(path)))
            d=ROOT/OUT_DIR
            kept_fdn_selectors(d/f'{name}_lp.sv',D,E)
            kept_tap_copies(d/f'{name}_lp.sv')
            # Generated shell intentionally receives exact-source simulation flag.
            f=d/f'{name}_lp_bench.sh';f.write_text(f.read_text().replace('-DOT_S5_HARD','-DOT_S5_HARD -DOT_S8_SIM'))
            if name!='qfd_dv_s8':
                f=d/'qfd_dv_s8_flat_lagref.sv';(d/f'{name}_flat_lagref.sv').write_text(f.read_text().replace('module qfd_dv_s8_flat_lagref',f'module {name}_flat_lagref'))
                for f in [d/f'tb_{name}_lp.sv',d/f'{name}_lp_bench.sh']:
                    f.write_text(f.read_text().replace('qfd_dv_s8_flat_lagref',f'{name}_flat_lagref'))
        print(name,len(p['lands']),'landings; hard-leaf explicit1/1 simulation')
if __name__=='__main__':main()
