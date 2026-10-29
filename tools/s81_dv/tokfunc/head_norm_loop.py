#!/usr/bin/env python3
"""Native VP/VN/VQ head publication through the real sixteen-slice xfin.

The selected beat supplies its actual partial to xfin. Other79 partials are
explicit golden boundary inputs. Actual returned rstd feeds the same native
VN/VQ; it is never replaced by a golden rstd. Scope is a component feedback
path, with explicit reference link depths, not current die transport timing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def replace_once(s, old, new):
    if s.count(old) != 1:
        raise ValueError('selected beat bench changed at '+old[:80])
    return s.replace(old, new)


def generate_tb(source):
    s = replace_once(source, 'always #0.5 clk = ~clk;', 'always #0.4165 clk = ~clk;')
    s = replace_once(s, "        c_v <= 1'b0; sw_v <= 1'b0; rb_v <= 1'b0;", "        c_v <= 1'b0; sw_v <= 1'b0;")
    s = replace_once(s, "        if (t_p >= 0 && cyc == t_p + RB_GAP) begin rb_v <= 1'b1; rb_d <= rstd[1 * blk + 0]; t_rb = cyc; t_y0 = -1; end",
                     "        if (rb_v) begin t_rb = cyc; t_y0 = -1; end")
    start = s.index('        if (t_q >= 0 && cyc == t_q + 12)')
    end = s.index('        if (cyc == 1200) begin', start)
    s = s[:start] + s[end:]
    s = s.replace('BEAT, 8\'d3,', "128 + BEAT, 8'd2,")
    if "128 + BEAT, 8'd2," not in s:
        raise ValueError('actual NORMR header patch missing')
    start = s.index('            $display("SLBEAT beat=')
    end = s.index('            $finish;', start)
    s = s[:start] + '''            $display("HEAD_NORM_LOOP beat=%0d actual_partial=%h partials=%0d y=%0d q=%0d xb=%0d rb=%0d rerr=%0d err=%0d leaf_fault=%b/%b/%b xfin_fault=%h partial_edge=%0d first_rstd=%0d last_rstd=%0d actual_xb_edge=%0d", BEAT, actual_partial, np_,ny,nq,nb,nr,rerr,err,fp,fn,fq,xflt,t_p,first_rb,last_rb,t_rb+lat_b[0]);
            if (err==0 && np_==1 && ny==8 && nq==0 && nb==1 && nr==16 && rerr==0 && !fp && !fn && !fq && xflt==0)
                $display("PASS");
            else $fatal(1,"HEAD_NORM_LOOP FAIL");
''' + s[end:]
    # Both reference partials and the native returned rstd are checked.
    s = replace_once(s, '            nb = nb + 1; lat_b[blk] = cyc - t_rb;', '''            nb = nb + 1; lat_b[blk] = cyc - t_rb;
            if (xo[20] !== 1'b1 || xo[19:13] !== 7'(BEAT)) begin err=err+1; $display("actual flagged publication header mismatch"); end''')
    marker = '    // row image to write: {row, data}'
    circuit = '''    // Boundary stimulus dates are static, independent of ready/completion.
    localparam integer NS=16,NVL=5,KW=173;
    reg [31:0] partials[0:79],eps_mem[0:0];
    reg [31:0] actual_partial=0;reg actual_seen=0;integer mut=0;
    initial begin $readmemh("partials.mem",partials);$readmemh("a_eps.mem",eps_mem);if($value$plusargs("MUT=%d",mut))begin end end
    wire[15:0]xrb_v,xflt;wire[31:0]xrb_d[0:15];
    wire[KW-1:0]xeo[0:15],xwo[0:15],xwi[0:15],xei[0:15];
    integer nr=0,rerr=0,first_rb=-1,last_rb=-1,rr;
    always@(posedge clk)begin
      if(p_v)begin actual_partial<=p_d;actual_seen<=1;end
      rb_v<=xrb_v[SID];rb_d<=xrb_d[SID];
      if(cyc==399&&!actual_seen)$fatal(1,"selected native partial missing before static exchange slot");
      for(rr=0;rr<16;rr=rr+1)if(xrb_v[rr])begin
        nr=nr+1;if(first_rb<0)first_rb=cyc;last_rb=cyc;
        if(xrb_d[rr]!==rstd[0])begin rerr=rerr+1;$display("real xfin rstd mismatch slice%0d got%h want%h",rr,xrb_d[rr],rstd[0]);end
      end
    end
    genvar g;
    generate for(g=0;g<16;g=g+1)begin:actual_xfin
      wire[7:0]li=8'(cyc-400);
      wire sv=cyc>=400&&cyc<405;
      wire[31:0]sdata=(5*g+int'(li)==BEAT)?(actual_partial ^ ((mut==1)?32'h00800000:32'd0)):partials[5*g+int'(li)];
      ot_s81dv_xfin #(.NS(16),.NVL(5),.SIW(8)) u(
       .clk(clk),.rst_n(rst_n),.go(cyc==220),.mode(1'b0),.sid(4'(g)),.eps(eps_mem[0]),.s_v(sv),.s_i(li),.s(sdata),
       .wi_v(xwi[g][KW-1]),.wi_h(xwi[g][KW-2-:4]),.wi_b(xwi[g][KW-6-:8]),.wi_d(xwi[g][159:0]),
       .ei_v(xei[g][KW-1]),.ei_h(xei[g][KW-2-:4]),.ei_b(xei[g][KW-6-:8]),.ei_d(xei[g][159:0]),
       .eo_v(xeo[g][KW-1]),.eo_h(xeo[g][KW-2-:4]),.eo_b(xeo[g][KW-6-:8]),.eo_d(xeo[g][159:0]),
       .wo_v(xwo[g][KW-1]),.wo_h(xwo[g][KW-2-:4]),.wo_b(xwo[g][KW-6-:8]),.wo_d(xwo[g][159:0]),
       .rb_v(xrb_v[g]),.rb_d(xrb_d[g]),.e_v(),.e_c(),.e_hh(),.e_kk(),.e_dd(),.fault(xflt[g]));
      localparam integer L=(g==7||g==15)?29:9;
      ot_hdc_delay #(.W(KW),.D(L),.RESET(1)) east(.clk(clk),.rst_n(rst_n),.d(xeo[g]),.q(xwi[(g+1)%16]));
      ot_hdc_delay #(.W(KW),.D(L),.RESET(1)) west(.clk(clk),.rst_n(rst_n),.d(xwo[(g+1)%16]),.q(xei[g]));
    end endgenerate

'''
    return replace_once(s, marker, circuit+marker)


def run(root, prep, out, beat=37):
    root=Path(root);prep=Path(prep);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    src=root/'rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_beat.sv'
    tb=out/'tb.sv';tb.write_text(generate_tb(src.read_text()))
    files=(root/'physical/hbm_norm_split_20261008/sources.f').read_text().split()
    files+=['rtl/hdc/v41x/ot_dsrom_su_add6.sv','rtl/hdc/v41x/ot_dsrom_su_hcpost.sv',
      'rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv','rtl/lib/ot_rst_relay.sv',
      'rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv',
      'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
      'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',
      'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v',
      *['rtl/dsrom_sys/s81_dv/slice/'+n+'.sv' for n in ['ot_s81sl_vn','ot_s81sl_vp','ot_s81sl_vq','ot_s81sl_aq12x']]]
    files=list(dict.fromkeys(files));missing=[f for f in files if not(root/f).is_file()]
    if missing:raise ValueError('source closure missing '+str(missing))
    (out/'source_hashes.json').write_text(json.dumps({f:hashlib.sha256((root/f).read_bytes()).hexdigest()for f in files},indent=1)+'\n')
    rd=out/'run';shutil.copytree(prep/f'beat/b{beat:02d}',rd)
    (rd/'partials.mem').write_text(''.join((prep/f'beat/b{b:02d}/a_bp.mem').read_text()for b in range(80)))
    cmd=['verilator','--binary','--timing','-O1','--build-jobs','4','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD',
         '-GBEAT='+str(beat),'-GNORMR=1','-GVQ_XMEM=2','--top-module','tb_s81sl_beat','-Mdir',str(out/'obj'),
         '--output-split','5000','--output-split-cfuncs','500','-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0',
         *(str(root/f)for f in files),str(tb)]
    with(out/'build.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    results={}
    for m in [0,1]:
        with(out/f'run{m}.log').open('w')as log:r=subprocess.run([str(out/'obj/Vtb_s81sl_beat'),'+MUT='+str(m)],cwd=rd,stdout=log,stderr=subprocess.STDOUT)
        text=(out/f'run{m}.log').read_text();ok=(r.returncode==0 and '\nPASS\n'in text)if m==0 else(r.returncode!=0 and 'real xfin rstd mismatch'in text)
        results[m]=dict(PASS=ok,rc=r.returncode)
        if not ok:raise ValueError('component gate mode'+str(m)+' failed: '+str(out))
    (out/'verdict.json').write_text(json.dumps(dict(PASS=True,scope='ONE_NATIVE_LEAF_REAL_16_XFIN_FEEDBACK',
        actual_native_beats=1,oracle_boundary_partials=79,reference_link_depths=dict(street=9,end=29),
        results=results,current_die_timing=False,full_token=False,added_RTL_cycles=0),indent=1)+'\n')
    print((out/'run0.log').read_text());print('corrupted actual native partial CAUGHT')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--prep',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--beat',type=int,default=37)
    a=p.parse_args();run(a.root.resolve(),a.prep.resolve(),a.out.resolve(),a.beat)
