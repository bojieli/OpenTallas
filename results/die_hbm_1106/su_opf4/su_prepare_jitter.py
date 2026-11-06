import pathlib,random,sys,shutil,json
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-hbm-su-opf4-1106');B=pathlib.Path('/srv/opentallas-scratch2/claude/hbm-bind-6/tip2');sys.path.insert(0,str(B/'tools/hbm_static'));from su_arith_generate import FIELDS
ofs=0
for n,w in reversed(FIELDS):
 if n=='emit':emitofs=ofs
 ofs+=w
assert ofs==1742
m=sum(1<<(q*1742+emitofs) for q in range(4));raw=[int(s,16) for s in (R/'vec/control.mem').read_text().splitlines()];out=R/'vec_jitter';out.mkdir(exist_ok=True);N=240;rom=[];cycles=[]
for op in range(31):
 rng=random.Random(0x1106+op);issue=[];c=8
 for k in range(64):issue.append(c);c+=1+rng.randrange(3)
 assert issue[-1]+40<N
 cycles+=issue;idx={c:k for k,c in enumerate(issue)};nextk=0
 for c in range(N):
  if c<8:v=raw[op*176+c]
  elif c in idx:nextk=idx[c];v=raw[op*176+8+nextk]
  else:v=raw[op*176+8+nextk]&~m
  rom.append(v)
(out/'control.mem').write_text('\n'.join(f'{v:01742x}' for v in rom)+'\n');(out/'issue_cycles.mem').write_text('\n'.join(f'{v:08x}' for v in cycles)+'\n')
for n in ['seed.mem','gold.mem']:shutil.copyfile(R/'vec'/n,out/n)
(out/'programme.json').write_text(json.dumps(dict(ops=31,issues=64,cycles=240,holes='seeded0..2emptyissueedges',seed_order='row=(197*r+17)%512;gapsafterr%7==3',expected_issue_to_pin_output=40),indent=1)+'\n')
s=(R/'tb_local_enable.sv').read_text();s=s.replace('NOPS*176','NOPS*240').replace('c<176','c<240').replace('j*176','j*240');s=s.replace('string dir;','reg [31:0] issue_cycles[0:NOPS*64-1];\n bit reset_between;\n string dir;');s=s.replace('$readmemh({dir,"/control.mem"},programme);','$readmemh({dir,"/control.mem"},programme);$readmemh({dir,"/issue_cycles.mem"},issue_cycles); reset_between=$test$plusargs("RESET_BETWEEN");');s=s.replace('if(count>=64)fail("extra output");','if(count<64 && cycle!=integer\'(issue_cycles[op*64+count])+40)fail("per-word selected-profile edge");\n   if(count>=64)fail("extra output");');s=s.replace("seed_row=9'(r);@(negedge clk);","seed_row=9'((197*r+17)%512);@(negedge clk);if(r%7==3)begin seed_v=0;repeat((r%3)+1)@(negedge clk);seed_v=1;end ")
anchor='op=j;count=0;';reset='''op=j;count=0;
   if(reset_between)begin
    seed_v=1;control=0;rst_n=0;repeat(12)@(negedge clk);
    if(vm_we||ro_v)fail("reset did not flush outputs");
    rst_n=1;repeat(12)@(negedge clk);
    for(integer sr=0;sr<512;sr=sr+1)begin seed_row=9'((197*sr+17)%512);@(negedge clk);if(sr%7==3)begin seed_v=0;repeat((sr%3)+1)@(negedge clk);seed_v=1;end end
    seed_v=0;repeat(5)@(negedge clk);
   end''';assert anchor in s;s=s.replace(anchor,reset);(R/'tb_jitter.sv').write_text(s)
job='''#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-su-opf4-1106
baseline_root=/srv/opentallas-scratch2/claude/hbm-bind-6/tip2
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_su_static_lane_leaf --Mdir "$PWD/obj_jitter" "$PWD/tb_jitter.sv" "$PWD/rtl_positive"/*.sv "$baseline_root/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11/sram_bench_model.sv" > build_jitter.log 2>&1
./obj_jitter/Vtb_su_static_lane_leaf +DIR="$PWD/vec_jitter" > jitter.log 2>&1
./obj_jitter/Vtb_su_static_lane_leaf +DIR="$PWD/vec_jitter" +RESET_BETWEEN > jitter_reset.log 2>&1
tail -5 jitter.log
tail -5 jitter_reset.log
''';(R/'run_jitter.sh').write_text(job);print('prepared emit holes/shuffled bank writes/program gaps/reset gate')
