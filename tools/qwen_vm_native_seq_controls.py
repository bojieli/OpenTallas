#!/usr/bin/env python3
"""Actual Qwen sequencer VM controls; synthetic descriptors, no arithmetic claim."""
import argparse, hashlib, json, pathlib, subprocess
p=argparse.ArgumentParser();p.add_argument('--repo',type=pathlib.Path,default=pathlib.Path('/home/ubuntu/OpenTallas'));p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('/tmp/qwen-vm-seq-evidence-20261007/run'));a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
tb=r'''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,start=0,core_done=0;
wire core_start,desc_re,vm_re,vm_we,c_valid,c_last,done,fault;
wire [5:0] desc_addr; wire [7:0] vm_raddr,vm_waddr;
reg [63:0] desc_q=0;reg [511:0] vm_rq=0;
wire [511:0] c_data,vm_wdata;
reg c_ready=0,r_valid=0,r_last=0;reg [511:0] r_data=0;
integer cycle=0,base,n,stall,ri=0,wi=0,tx=0,simultaneous=0;
reg [63:0] descriptor;
MODULE #(.ENABLE_AR256(1)) dut(
.clk(clk),.rst_n(rst_n),.start(start),.token(16'd0),.pos(16'd0),.done(done),.fault(fault),
.core_start(core_start),.core_done(core_done),.core_next_token(16'd0),.core_next_val(32'd0),.core_fault(1'b0),
.desc_re(desc_re),.desc_addr(desc_addr),.desc_q(desc_q),
.vm_re(vm_re),.vm_raddr(vm_raddr),.vm_rq(vm_rq),.vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),
.c_valid(c_valid),.c_ready(c_ready),.c_data(c_data),.c_last(c_last),
.r_valid(r_valid),.r_data(r_data),.r_last(r_last),.r_rank(2'd0),.r_err(1'b0));
always @(negedge clk) c_ready = rst_n && (!stall || ((cycle%7)!=1 && (cycle%7)!=2 && (cycle%7)!=3));
always @(posedge clk) begin
cycle=cycle+1;
core_done <= core_start;
if(desc_re) desc_q <= desc_addr==0 ? descriptor : 64'd0;
if(vm_re) vm_rq <= {504'd0,vm_raddr};
r_valid <= c_valid && c_ready;
r_last <= c_last;
r_data <= c_data;
if(rst_n) begin
if(vm_re) begin
if(vm_raddr !== ((base+ri+($test$plusargs("WRONG_EXPECTED") ? 1 : 0))&255)) $fatal(1,"read sequence");
$display("VM,%0d,R,%0d,65535",cycle,vm_raddr);ri=ri+1;
end
if(vm_we) begin
if(vm_waddr !== ((base+wi)&255)) $fatal(1,"write sequence");
if(vm_wdata !== {504'd0,vm_waddr}) $fatal(1,"transport payload");
$display("VM,%0d,W,%0d,65535",cycle,vm_waddr);wi=wi+1;
end
if(vm_re && vm_we) simultaneous=simultaneous+1;
if(c_valid && c_ready) tx=tx+1;
if(fault) $fatal(1,"native fault");
if(done) begin
if(ri!=n || wi!=n || tx!=n) $fatal(1,"count");
$display("PASS,%0d,%0d,%0d,%0d",ri,wi,simultaneous,cycle);$finish;
end
end
if(cycle>4000) $fatal(1,"bench finite expected protocol failed");
end
initial begin
if(!$value$plusargs("BASE=%d",base)) base=32;
if(!$value$plusargs("N=%d",n)) n=16;
if(!$value$plusargs("STALL=%d",stall)) stall=0;
descriptor=1 | (base<<2) | ((n&255)<<10);
repeat(3) @(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;
end
endmodule
'''
results=[];sources=['tools/qwen_rom_rt_core_emit_w12.py','rtl/rom/ot_qwen_tp_seq_w12.sv','rtl/rom/ot_qwen_tp_seq_w12_vp.sv','rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv','rtl/hdc/ot_qwen_w12_matvec.sv','rtl/hdc/ot_hdc_vstream.sv','rtl/hdc/ot_hdc_vreduce.sv','results/rtl/qwen_rom_finite_vm_schedule_20261005/inputs/core.sv','results/rtl/qwen_rom_finite_vm_schedule_20261005/inputs/top.sv']
for module in ['ot_qwen_tp_seq_w12','ot_qwen_tp_seq_w12_vp']:
    d=a.out/module;d.mkdir(exist_ok=True);(d/'tb.sv').write_text(tb.replace('MODULE',module))
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'sim'),str(d/'tb.sv'),str(a.repo/'rtl/rom'/f'{module}.sv')],check=True,capture_output=True)
    neg=subprocess.run(['vvp',str(d/'sim'),'+WRONG_EXPECTED'],text=True,capture_output=True)
    assert neg.returncode!=0 and 'read sequence' in neg.stdout
    (d/'wrong_expected.log').write_text(neg.stdout+neg.stderr)
    for base,n in [(0,16),(32,16),(240,16),(0,256)]:
      for stall in [0,1]:
        log=subprocess.check_output(['vvp',str(d/'sim'),f'+BASE={base}',f'+N={n}',f'+STALL={stall}'],text=True)
        name=f'b{base}_n{n}_stall{stall}';(d/f'{name}.log').write_text(log)
        events=[]
        for line in log.splitlines():
          if line.startswith('VM,'):
            _,cycle,kind,word,mask=line.split(',');word=int(word);events.append(dict(cycle=int(cycle),kind=kind,word=word,mask=int(mask),bank=(word^(word>>7))&127,row=word>>7))
        for kind in 'RW':
          assert [e['word'] for e in events if e['kind']==kind]==list(range(base,base+n))
        mutated=[e.copy() for e in events];mutated[0]['word']^=1
        assert [e['word'] for e in mutated if e['kind']=='R']!=list(range(base,base+n))
        (d/f'{name}.json').write_text(json.dumps(events,indent=2)+'\n')
        results.append(dict(module=module,base=base,n=n,stall=stall,pass_line=log.splitlines()[-1],events=len(events),address_checker_negative_rejected=True))
for base,n in [(0,16),(32,16),(240,16),(0,256)]:
 for stall in [0,1]:
  name=f'b{base}_n{n}_stall{stall}.json'
  assert (a.out/'ot_qwen_tp_seq_w12'/name).read_bytes()==(a.out/'ot_qwen_tp_seq_w12_vp'/name).read_bytes()
report=dict(actual_simulator_negative_controls=2,default_vp_baseline_trace_pairs_equal=8,scope='Native sequencer actual-module control and opaque-payload transport; synthetic legal descriptors, core_done handshake and collective loopback. No whole workload, arithmetic, ME/SU overlap, bank timing or performance claim.',sources={s:hashlib.sha256((a.repo/s).read_bytes()).hexdigest() for s in sources},cases=results)
(a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(results,indent=2))
