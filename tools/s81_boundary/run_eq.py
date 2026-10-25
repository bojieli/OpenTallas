#!/usr/bin/env python3
"""Same-cycle boundary duplication miter against the pinned pre-fix RTL."""
import argparse, pathlib, re, subprocess
p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();root=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
ref='ca0e38135'; files=['rtl/v41die/ot_s81_cfg7_seq.sv','rtl/v41die/ot_s81_cfg7_seq_bfp.sv','rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l0r.sv']
for f in files:
 s=subprocess.check_output(['git','show',f'{ref}:{f}'],cwd=root,text=True)
 for m in ['ot_s81_cfg7_seq_bfp','ot_s81_cfg7_seq_bf','ot_s81_cfg7_seq','dsdv_gunit_l0r']:
  s=re.sub(r'\b'+m+r'\b',m+'_old',s)
 (out/pathlib.Path(f).name).write_text(s)
s=(root/'rtl/v41die/test/tb_ot_s81_cfg7_seq_bfp.sv').read_text();start=s.index('    ot_s81_cfg7_seq_bfp #');end=s.index('));',start)+3;inst=s[start:end];inst=inst.replace('ot_s81_cfg7_seq_bfp #','ot_s81_cfg7_seq_bfp_old #').replace(' dut (',' old_dut (')
for old,new in [('a','oa'),('ce','oce'),('cfg','ocfg'),('ge','oge'),('st','ost'),('fp','ofp')]:
 inst=re.sub(r'\('+old+r'(?=\)|\[)', '('+new, inst)
# Original test compares the production reference schedule; this adds pre-fix lockstep on every output.
s=s[:end]+'''\n    wire [11:0] oa; wire [6:0] oce; wire [53:0] ocfg; wire oge; wire [1:0] ost; wire [37:0] ofp;\n'''+inst+'''\n    always @(negedge clk) if (rst_n && {a,ce,cfg,ge,st,fp} !== {oa,oce,ocfg,oge,ost,ofp}) $fatal(1,"OLD_NEW_MISMATCH");\n'''+s[end:];(out/'tb_cfg.sv').write_text(s)
common=['rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_die_bind/ot_s81_bf_prog_seq.sv']
for mode,defs,want in [('pinreg',['-DTB_BFP_PINREG'],True),('mutant',['-DTB_BFP_PINREG','-DOT_S81_CFG7_BFP_MUT_ROW'],False),('base',[],True)]:
 cmd=['iverilog','-g2012','-s','tb_ot_s81_cfg7_seq_bfp',*defs,'-o',str(out/(mode+'.vvp')),*[str(root/x) for x in common+files[:2]],str(out/'ot_s81_cfg7_seq.sv'),str(out/'ot_s81_cfg7_seq_bfp.sv'),str(out/'tb_cfg.sv')]
 cp=subprocess.run(cmd,capture_output=True,text=True);(out/(mode+'.build.log')).write_text(cp.stdout+cp.stderr)
 if cp.returncode:raise SystemExit(cp.stderr)
 cp=subprocess.run(['vvp',str(out/(mode+'.vvp'))],capture_output=True,text=True);(out/(mode+'.run.log')).write_text(cp.stdout+cp.stderr);good=cp.returncode==0 and 'PASS ' in cp.stdout
 print(mode,'PASS' if good==want else 'FAIL',cp.stdout.splitlines()[-1]);assert good==want
# L0r: both instances see random writes, stream restarts, and resets. Case equality includes invalid payload bits.
ports={'wr_av':1,'wr_agh':5,'wr_ad':192,'wr_bv':1,'wr_bgh':5,'wr_bd':192,'wr_b':1,'go_a':1,'go_acc':5,'go_b':1};outs={'r_v':1,'r_i':4,'r_acc':5,'r_d':320,'r_f':1}
s='module tb; reg clk=0; always #1 clk=~clk; reg rst_n=0; integer i,k;\n'
for n,w in ports.items():s+=f'reg [{w-1}:0] {n}=0;\n'
for n,w in outs.items():s+=f'wire [{w-1}:0] n_{n},o_{n};\n'
for mod,prefix in [('dsdv_gunit_l0r','n'),('dsdv_gunit_l0r_old','o')]:s+=mod+f' {prefix}(.clk(clk),.rst_n(rst_n),'+','.join(f'.{n}({n})' for n in ports)+','+','.join(f'.{n}({prefix}_{n})' for n in outs)+');\n'
s+='initial begin repeat(4) @(negedge clk); rst_n=1; for(i=0;i<4000;i=i+1) begin @(negedge clk);\n'
for n,w in ports.items():s+=f'{n}='+ ('($random & 7)==0' if n=='go_a' else ('{'+','.join(['$random']*((w+31)//32))+'}' if w>32 else '$random'))+';\n'
s+='if(i==2000) rst_n=0; if(i==2005) rst_n=1; #0.1; if ({'+','.join('n_'+n for n in outs)+'} !== {'+','.join('o_'+n for n in outs)+'}) $fatal(1,"L0R_MISMATCH"); end $display("PASS L0R 4000 cycles"); $finish; end endmodule\n';(out/'tb_l0r.sv').write_text(s)
cmd=['iverilog','-g2012','-s','tb','-o',str(out/'l0r.vvp'),str(root/common[0]),str(root/files[2]),str(out/'dsdv_gunit_l0r.sv'),str(out/'tb_l0r.sv')];subprocess.run(cmd,check=True);cp=subprocess.run(['vvp',str(out/'l0r.vvp')],capture_output=True,text=True);(out/'l0r.run.log').write_text(cp.stdout+cp.stderr);print(cp.stdout);assert cp.returncode==0
# Existing lane-order mutation must break the same lockstep comparator.
mut=s.replace('dsdv_gunit_l0r n(', 'dsdv_gunit_l0r #(.MUT(6)) n(');(out/'tb_l0r_mut.sv').write_text(mut)
cmd[-1]=str(out/'tb_l0r_mut.sv');cmd[5]=str(out/'l0r_mut.vvp');subprocess.run(cmd,check=True);cp=subprocess.run(['vvp',str(out/'l0r_mut.vvp')],capture_output=True,text=True);(out/'l0r_mut.run.log').write_text(cp.stdout+cp.stderr);print('l0r mutant',cp.stdout);assert cp.returncode!=0 and 'L0R_MISMATCH' in cp.stdout
