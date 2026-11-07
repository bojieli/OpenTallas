from pathlib import Path
import re,shutil
r=Path('/srv/opentallas-scratch/claude/codex-hbm-0615/src');p=r/'rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_body.sv';base=Path('/tmp/codex-hbm-0615/f512_vCF1d/rtl/ot_vms_bank_q0_faces_body.sv').read_text()
assert 'WRITE_PREDECODE' in p.read_text() or p.read_text().split('    // ------------------------------------------------------------------ SECDED',1)[1]==base.split('    // ------------------------------------------------------------------ SECDED',1)[1]
s=base.replace('parameter integer MUT = 0','parameter integer WRITE_PREDECODE = 0, // opt-in, zero new calendar edges\n    parameter integer MUT = 0',1)
block='''    // Decode at the existing payload capture using same-edge raw packet and straps.
    // This is the exact prior post-register decode, with no added cycle.
    reg [WG*12-1:0] wq_predec;
    reg [11:0] kq_predec, dq_predec;
    always @(posedge clk) begin
        for (integer g=0;g<WG;g=g+1)
            wq_predec[g*12+:12] <= wq[g*281+280] ? dsec(wq[g*281+264+:16],bid,sid) : 12'd0;
        kq_predec <= kq[280] ? dsec(kq[279:264],bid,sid) : 12'd0;
        dq_predec <= dq[280] ? dsec(dq[279:264] ^ (MUT==2?16'h0008:16'h0000),bid,sid) : 12'd0;
    end
'''
s=s.replace('    // output registers: control valid + payload',block+'    // output registers: control valid + payload',1)
for a,b in [('dsec(wq_r[wl*281+264+:16],COMPILED_BID,COMPILED_SID)','wq_predec[wl*12+:12]'),('dsec(kq_r[279:264],COMPILED_BID,COMPILED_SID)','kq_predec'),("dsec(dq_r[279:264] ^ (MUT==2?16'h0008:16'h0000),COMPILED_BID,COMPILED_SID)",'dq_predec')]:
 assert s.count(a)==1;s=s.replace(a,'(WRITE_PREDECODE!=0 ? '+b+' : '+a+')',1)
p.write_text(s)
d=Path('/tmp/codex-hbm-1209/f512_predec_bench3');d.mkdir(exist_ok=True);(d/'.keep').touch()
files=list(Path('/tmp/codex-hbm-0615/f512_vCF1d/rtl').glob('*.sv'));mods=set()
for f in files:mods.update(re.findall(r'\bmodule\s+([a-zA-Z_][\w$]*)\s*(?:#\s*\(|\()',f.read_text(),re.M))
pat=re.compile(r'\b(?:'+'|'.join(map(re.escape,sorted(mods,key=len,reverse=True)))+r')\b')
for v in ['G','N','M']:
 out=d/v;out.mkdir(exist_ok=True)
 for f in files:
  t=s if v!='G' and f.name==p.name else f.read_text()
  if v!='G' and f.name=='ot_vms_bank_q0_faces_core.sv':t=t.replace('.EG_WIDE(1)', '.EG_WIDE(1),.WRITE_PREDECODE(1)')
  if v=='M' and f.name==p.name:t=t.replace("dsec(wq[g*281+264+:16],bid,sid)","(dsec(wq[g*281+264+:16],bid,sid) ^ 12'h800)")
  t=pat.sub(lambda m:v+'_'+m[0],t);(out/f.name).write_text(t)
for n in ['sram.v','reset.sv']:shutil.copy2('/tmp/codex-hbm-0615/f512bench/'+n,d/n)
tb=Path('/tmp/codex-hbm-0615/f512bench/tb.sv').read_text().replace('f512_gold gold','G_hnx_vms_bank_q0_faces__vecd4ae gold').replace('f512_new0 dut','N_hnx_vms_bank_q0_faces__vecd4ae dut').replace('f512_new1 dut','M_hnx_vms_bank_q0_faces__vecd4ae dut')
tb=re.sub(r'b_(\w+)!==prev_\1',r'b_\1!==a_\1',tb)
extra="if(t>=160&&t<168)begin row=t-160;i_wslot_v=1;if(t%2==0)begin i_wslot=2;i_kq={1'b1,1'b0,2'd0,10'(row),3'd0,data(row,round),8'hff};end else begin i_wslot=6;i_dq={1'b1,1'b0,2'd0,10'(row),3'd0,data(row,round),8'hff};end end\nif(t>=168&&t<176)begin i_wslot_v=1;i_wslot=0;i_wq0={1'b1,1'b0,2'd0,10'(t),3'd1,data(t,round),8'hff};end\n"
tb=tb.replace('if(t>=176&&t<816)',extra+'if(t>=176&&t<816)');(d/'tb.sv').write_text(tb)
(d/'run.sh').write_text('''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for m in 0 1; do /usr/bin/iverilog -g2012 -s tb -Ptb.MUT=$m -o test$m.vvp G/*.sv N/*.sv M/*.sv reset.sv sram.v tb.sv; /usr/bin/vvp test$m.vvp > result$m.log 2>&1; done
''')
print('source',p,'modules',len(mods),'bench',d)
