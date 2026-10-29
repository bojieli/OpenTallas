import hashlib,json,os,pathlib,shutil,subprocess,sys
W=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-s81-frame-sub-1028')
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-tok-s81-1028/cfg_alias_native');R.mkdir(exist_ok=True)
sys.path.insert(0,str(W/'tools/s81_dv'));import frame_cfg_identity as F
src=pathlib.Path('/srv/opentallas-scratch2/claude/tok17-gb/slice/vec/u_f_0L01')
for p in src.glob('u_f_0L01_c*.viamap.hex'):shutil.copyfile(p,R/p.name)
report=pathlib.Path('/srv/opentallas-scratch2/claude/tok-s81-1/b2/out/bind_report.json')
rows=F.emit_bound_aliases(F.bind_elab.module_body(W/'rtl/dsrom_sys/s81_dv/frame_lp/col_h10_l4_lp.sv','col_h10_l4_lp'),F.bind_elab.module_body(W/'rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h10_l4_lp_plan_kit.sv','col_h10_l4_lp_r0'),'u_f_0L01','u_r0',json.loads(report.read_text()),R)
a=rows[0];b=next(x for x in rows if x['image_sha256']!=a['image_sha256'])
tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #0.4165 clk=~clk;
reg [11:0] addr=0;wire[71:0]r0,r1,c0,c1,good,bad;integer mut=0;
ot_rom_4096x72_m8 #(.INSTANCE("SOURCE0")) ref0(clk,1'b1,addr,r0);
ot_rom_4096x72_m8 #(.INSTANCE("SOURCE1")) ref1(clk,1'b1,addr,r1);
ot_rom_4096x72_m8 #(.INSTANCE("ALIAS0")) actual0(clk,1'b1,addr,c0);
ot_rom_4096x72_m8 #(.INSTANCE("ALIAS1")) actual1(clk,1'b1,addr,good);
ot_rom_4096x72_m8 #(.INSTANCE("ALIAS0")) wrong_identity(clk,1'b1,addr,bad);
assign c1=mut?bad:good;
initial begin
if($value$plusargs("MUT=%d",mut))begin end
for(integer n=0;n<4096;n=n+1)begin
 @(negedge clk);addr=12'(n);@(posedge clk);#0.001;
 if(c0!==r0 || c1!==r1)$fatal(1,"BOUND_CFG_ALIAS_DIFF addr%0d mutant%0d",n,mut);
end
$display("BOUND_CFG_ALIAS_PASS 8192words 72bits 833ps");$finish;
end endmodule
'''
for key,val in [('SOURCE0',a['image']),('SOURCE1',b['image']),('ALIAS0',a['alias']),('ALIAS1',b['alias'])]:tb=tb.replace(key,val.removesuffix('.viamap.hex'))
(R/'tb.sv').write_text(tb)
with(R/'build.log').open('w')as f:subprocess.run(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','-j','2','--Mdir',str(R/'obj'),str(W/'physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v'),str(R/'tb.sv')],stdout=f,stderr=subprocess.STDOUT,check=True)
for m in (0,1):
 with(R/f'run{m}.log').open('w')as f:r=subprocess.run([str(R/'obj/Vtb'),f'+MUT={m}',f'+OT_ROM_DIR={R}'],stdout=f,stderr=subprocess.STDOUT)
 log=(R/f'run{m}.log').read_text();assert(r.returncode==0 and'BOUND_CFG_ALIAS_PASS'in log)if m==0 else(r.returncode!=0 and'BOUND_CFG_ALIAS_DIFF'in log),log
rec=dict(scope='Namespace mechanism only; exact current source/split macro pins and legacy b2 selector audit, no current s13 bind or provider qualification',source_commit=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip(),aliases=len(rows),tested_rows=[a,b],native_words=8192,bits=72,clock_ps=833,wrong_identity_mutant='CAUGHT',original_images_unchanged=True,bind_report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),full_frame_qualified=False)
(R/'check.json').write_text(json.dumps(rec,indent=1)+'\n');print('BOUND_CFG_ALIAS_NATIVE PASS 8192x72 833ps wrongidentity CAUGHT',flush=True)
