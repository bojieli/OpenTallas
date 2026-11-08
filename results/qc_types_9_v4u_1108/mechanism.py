#!/usr/bin/env python3
"""Exercise the current START emitter and real CA ring with active START/reset."""
import argparse, json, subprocess, sys
from pathlib import Path

def execute(work, repo, name, files, expect=True):
    target=work/name
    cmd=['iverilog','-g2012','-s','tb','-o',str(target),*map(str,files)]
    p=subprocess.run(cmd,text=True,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr[-4000:])
    p=subprocess.run(['vvp',str(target)],text=True,capture_output=True)
    good=p.returncode==0 and 'PASS' in p.stdout
    if good!=expect:raise RuntimeError(f'{name}: unexpected result {p.returncode}\n{p.stdout}\n{p.stderr}')
    print(name, 'PASS' if good else 'MUTANT CAUGHT',p.stdout.strip()[-180:])

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--repo',type=Path,required=True);a.add_argument('--candidate',type=Path,required=True);a.add_argument('--bound',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    args.out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(args.repo/'tools/die_plan'))
    from clock_landings import Landings
    plan=json.loads(args.candidate.read_text());typ=plan['partition_types']['sle_fw_v3'];branches=typ['clock']['landing_writer_start']['branches']
    land=Landings.__new__(Landings);land.plan=plan;land.types=plan['partition_types'];land.ca_type={};land.reset_placements={}
    body=args.bound.read_text();head=body[:body.index(');')+2];logic=[];faces=[]
    for i,bus in enumerate(sorted(branches)):
        prev=land._writer_start_rtl('sle_fw_v3',bus,head,body,logic)
        faces.append(f'ot_dp_landing_relay face_{i} (.clk(clk), .rst_raw_n(raw), .d({prev}), .q(q[{i}]));')
    raws=sorted({s['raw_reset'] for b in branches.values() for s in b['stages']})
    rawlogic='\n'.join(f'wire {r}; assign {r}=raw;' for r in raws)
    emitted='\n'.join(logic+faces)
    module=f'module candidate(input clk,input start,input raw,output [{len(branches)-1}:0] q); wire cland_start_d=start;\n{rawlogic}\n{emitted}\nendmodule\n'
    dut=args.out/'candidate.sv';dut.write_text(module)
    cells=args.repo/'rtl/common/ot_dp_clk_landing_ca.sv';fifo=args.repo/'rtl/common/ot_meso_fifo.sv'
    tb=args.out/'tb_start.sv';tb.write_text('''module tb;
 reg clk=0; always #5 clk=~clk; reg root=0,start=0; reg raw=0; reg [3:0] model=0;
 wire [10:0] q; integer cycle=0,checked=0;
 candidate dut(clk,start,raw,q);
 always @(posedge clk) begin
  raw<=root; if(!raw) model<=0; else model<={model[2:0],start};
  #1; if(cycle>5) begin if(q!=={11{model[3]}}) $fatal(1,"START/reset mismatch cycle %0d",cycle);checked=checked+1;end
 end
 initial begin
  repeat(320) begin @(negedge clk);cycle=cycle+1;root=(cycle%160>=10 && cycle%160<150 && cycle%160!=80);start=(cycle%160>=20 && cycle%160<153);end
  if(checked<250)$fatal(1,"no coverage");$display("PASS active START/reset %0d cycles",checked);$finish;
 end
 endmodule\n''')
    execute(args.out,args.repo,'start',[dut,tb,cells,fifo])
    bypass=args.out/'candidate_bypass.sv';bypass.write_text(module.replace('.d(cland_writer_start_ag_eo_2), .q(q[0])','.d(cland_writer_start_ag_eo_1), .q(q[0])'))
    if bypass.read_text()==module:raise RuntimeError('bypass mutant did not modify emitted RTL')
    execute(args.out,args.repo,'start_bypass',[bypass,tb,cells,fifo],False)
    late=args.out/'candidate_wrong_reset_phase.sv';late.write_text(module.replace('wire cland_start_d=start;','wire cland_start_d=start; reg raw2=0,raw3=0;always @(posedge clk)begin raw2<=raw;raw3<=raw2;end').replace(f'assign {raws[0]}=raw;',f'assign {raws[0]}=raw3;'))
    execute(args.out,args.repo,'reset_wrong_phase',[late,tb,cells,fifo],False)
    # Real flop-ring data path: changing only writer START latency and K must
    # retain the payload stream. Both existing W=0 and W=1 are exercised.
    for old in (0,1):
        for mutant in (False,True):
            k_old=(-2+old)%64;k_new=k_old if mutant else (-2+3)%64
            oldwire='start'
            relays=[]
            for i in range(old+1):
                out=f'o{i}';relays.append(f'wire {out};ot_dp_landing_relay ro{i}(clk,raw,{oldwire},{out});');oldwire=out
            newwire='start'
            for i in range(4):
                out=f'n{i}';relays.append(f'wire {out};ot_dp_landing_relay rn{i}(clk,raw,{newwire},{out});');newwire=out
            ringtb=args.out/f'tb_ring_{old}_{int(mutant)}.sv'
            ringtb.write_text(f'''module tb;
 reg clk=0;always #5 clk=~clk;reg root=0,start=0,raw=0,receive=0;reg [7:0] data=1;
 always @(posedge clk)begin raw<=root;data<={{data[6:0],data[7]^data[5]^data[4]^data[3]}};end
 {''.join(relays)}
 wire [7:0] a,b;wire ar,br,af,bf;
 ot_dp_clk_landing_cas #(.W(8),.DEPTH(4),.WFALL(1),.WREG(1)) gold(.fclk(clk),.t_rst_n({oldwire}),.clk(clk),.rst_n(receive),.strap_k(6'd{k_old}),.d(data),.q(a),.ready(ar),.fault(af));
 ot_dp_clk_landing_cas #(.W(8),.DEPTH(4),.WFALL(1),.WREG(1)) gate(.fclk(clk),.t_rst_n({newwire}),.clk(clk),.rst_n(receive),.strap_k(6'd{k_new}),.d(data),.q(b),.ready(br),.fault(bf));
 integer cycle=0,checked=0;
 always @(posedge clk)begin #1;if(ar&&br)begin if(a!==b||af||bf)$fatal(1,"payload/K mismatch cycle %0d",cycle);checked=checked+1;end end
 initial begin repeat(640)begin @(negedge clk);cycle=cycle+1;root=(cycle%160>=10 && cycle%160<150);start=(cycle%160>=20 && cycle%160<150);receive=(cycle%160>=25 && cycle%160<150);end
 if(checked<200)$fatal(1,"no healthy payload comparison: %0d",checked);$display("PASS real CA payload %0d cycles",checked);$finish;end
 endmodule\n''')
            execute(args.out,args.repo,f'ring_W{old}_'+('badK' if mutant else 'priced'),[ringtb,cells,fifo,args.repo/'rtl/common/ot_dp_clk_landing.sv'],not mutant)
    (args.out/'emitted_reset_placements.json').write_text(json.dumps(land.reset_placements,indent=1)+'\n')
if __name__=='__main__':main()
