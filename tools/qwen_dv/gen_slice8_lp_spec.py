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
    'rtl/qwen_dv/s5/s8/'+x+'.sv' for x in ['qfd_dv_s8_suvm_rp1','qfd_dv_s8_vm8q_rp1','qfd_dv_s8_crh_rp1','qfd_dv_s8_rp1','qfd_dv_s8_fdn_arf1','qfd_dv_s8_station_tail1','qfd_dv_s8_tap_bounded','qfd_dv_s8_tap_bounded_helpers','qfd_dv_s8_kept']]+['rtl/common/landed_parent/ot_pl_land_field_copies.sv']

def make_flat():
    import gen_slice8_rp_source
    gen_slice8_rp_source.main()
    # The regional station is selected and qualified independently of this parent.
    # Regenerating it here silently restored the legacy SCALE_LAT=6/generic
    # arithmetic over the p7 SCALE_LAT=7/BZ16 implementation.
    station = ROOT / 'rtl/qwen_dv/s5/s8/qfd_dv_s8_station_tail1.sv'
    if not station.is_file():
        raise SystemExit('selected station_tail1 source absent; select a qualified child first')
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
    # QE3-SLICE2B 10-21 (w13cb census: rs_s/rs_n[1027,1026,513,512] 57/64 loads, l9_i[513,512] 64 loads = the same
    # shared control bits copied into 8 per-station nets -> 8 landing rings x D slots on one input pin). The shared
    # bits now leave as ONE net each (rss_c/rsn_c/nb_c): share_rings gives one write ring per (net, source region),
    # read by every station region. Same bits, same regions, same landing ages; per-station nets keep their data.
    old_decl='wire [8*132-1:0] rss_r, rsn_r; wire [8*66-1:0] nb_r; wire [131:0] rss_r0, rsn_r0, rss_r1, rsn_r1, rss_r2, rsn_r2, rss_r3, rsn_r3, rss_r4, rsn_r4, rss_r5, rsn_r5, rss_r6, rsn_r6, rss_r7, rsn_r7; wire [65:0] nb_r0, nb_r1, nb_r2, nb_r3, nb_r4, nb_r5, nb_r6, nb_r7;'
    assert text.count(old_decl)==1
    text=text.replace(old_decl,old_decl.replace('8*132','8*128').replace('8*66','8*64').replace('[131:0]','[127:0]').replace('[65:0]','[63:0]')
                      +' wire [3:0] rss_c, rsn_c; wire [1:0] nb_c;')
    for o,n in [('qfd_dv_s5_fn u_fn (','qfd_dv_s8_fn u_fn (.rs_n_c(rsn_c), '),('qfd_dv_s5_frs u_frs (','qfd_dv_s8_frs u_frs (.rs_s_c(rss_c), '),
                ('.l9_i(l9_i), .l9_r0(nb_r0),','.l9_i(l9_i), .l9_c(nb_c), .l9_r0(nb_r0),')]:
        assert text.count(o)==1,o;text=text.replace(o,n)
    for k in range(8):
        for o,n in [(f'.rs_s_c_p(rss_r{k}[131:128])','.rs_s_c_p(rss_c)'),(f'.rs_n_c_p(rsn_r{k}[131:128])','.rs_n_c_p(rsn_c)'),
                    (f'.nb_c_p(nb_r{k}[65:64])','.nb_c_p(nb_c)')]:
            assert text.count(o)==1,o;text=text.replace(o,n)
    # Optional exact S8 VM/CROM response alignment. Hard views with this switch must be re-closed.
    text=text.replace('qfd_dv_lane_h_safe2 u_head',
                      'qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(S8_MEMORY_ALIGNMENT)) u_head')
    pos=text.index(');')+2
    text=text[:pos]+'\n`ifdef OT_S8_CROM_ALIGN\n    localparam integer S8_MEMORY_ALIGNMENT = 3;\n`else\n    localparam integer S8_MEMORY_ALIGNMENT = 0;\n`endif\n'+text[pos:]
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

def kept_rp_copies(path,D):
    """QE3-SLICE2B 10-21 (census rp_w 1052/527 loads): 89 kept copies each of chd_q[519]/[518] for u_rp, captured on the
    SAME landing as u_rp.chd_q (ring 12 bank/vld/epo, same D/K as the r_ctl reader, rsi = a new kept copy of the same
    lpr_r_ctl_p stage as the reader's rsi copies) -> bit-identical to chd_q__l_r_ctl[519]/[518] every cycle."""
    import re
    text=path.read_text()
    m=re.search(r'ot_pl_land_split_r #\(\.W\(\(\(1037\) - \(0\) \+ 1\)\), \.D\((\d+)\), \.K\(([^)]*\)?)\), \.CHUNK_BITS\(24\)\) u_lpl_(\d+)_r \(\.ck\(ck_r_ctl\), \.rsi\(\{[^}]*\}\), \.bank\(lpl_(\d+)_bank\)',text)
    assert m,'chd_q r_ctl landing not found'
    Dm,K,n,ring=m[1],m[2],m[3],m[4];assert int(Dm)==D
    assert f'assign chd_q__l_r_ctl = lpl_{n}_o;' in text
    assert 'wire lpr_r_ctl_p;' in text
    code=f'    // u_rp write-select copies on landing {n} (ring {ring}): same bank/vld/epo, D/K, reader reset stage.\n'
    code+='    wire rp_w_rst; ot_pl_land_rst_copy #(.ID(9003)) u_rp_w_rst(.ck(ck_r_ctl),.d(lpr_r_ctl_p),.q(rp_w_rst));\n'
    for bit in (519,518):
        code+=f'    wire [88:0] rp_c{bit};\n'
        code+=(f'    ot_pl_land_field_copies #(.COPIES(89),.D({D}),.K({K})) u_rp_c{bit} (.ck(ck_r_ctl),.rsi(rp_w_rst),.bank({{'
               +', '.join(f'lpl_{ring}_bank[{s}*1038+{bit}]' for s in reversed(range(D)))+f'}}),.vld(lpl_{ring}_vld[{bit//24}*{D}+:{D}]),.epo(lpl_{ring}_epo),.o(rp_c{bit}));\n')
    key='    qfd_dv_s8_rp1 u_rp ('
    assert text.count(key)==1
    text=text.replace(key,code+'    qfd_dv_s8_rp1 #(.USE_W_COPIES(1)) u_rp (.w519_cp(rp_c519), .w518_cp(rp_c518), ',1)
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
            kept_rp_copies(d/f'{name}_lp.sv',D)
            # Generated shell intentionally receives exact-source simulation flag.
            f=d/f'{name}_lp_bench.sh';f.write_text(f.read_text().replace('-DOT_S5_HARD','-DOT_S5_HARD -DOT_S8_SIM'))
            if name!='qfd_dv_s8':
                f=d/'qfd_dv_s8_flat_lagref.sv';(d/f'{name}_flat_lagref.sv').write_text(f.read_text().replace('module qfd_dv_s8_flat_lagref',f'module {name}_flat_lagref'))
                for f in [d/f'tb_{name}_lp.sv',d/f'{name}_lp_bench.sh']:
                    f.write_text(f.read_text().replace('qfd_dv_s8_flat_lagref',f'{name}_flat_lagref'))
        print(name,len(p['lands']),'landings; hard-leaf explicit1/1 simulation')
if __name__=='__main__':main()
