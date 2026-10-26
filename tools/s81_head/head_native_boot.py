"""Real native-B control witness; run via ot-run. No head-die provider is invented.

The component accepts its own GO command after its delivered reset. Die START
releases mission controls; it is not a substitute for the controller's GO.
"""
import argparse
import json
import subprocess
from pathlib import Path
from prepare_head_native_l4 import stage_sources

TB = r'''`timescale 1ns/1ps
module tb_head_boot;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,go=0; wire ov,f; wire [31:0] d;
ot_s81hd_elemB_l4_native dut(.clk(clk),.rst_n(rst_n),.go(go),.x(256'd0),.o_v(ov),.o_d(d),.fault(f));
task tick; begin @(posedge clk); #1; end endtask
initial begin
repeat(5) tick();
@(negedge clk); rst_n=1;
tick(); if(dut.ready!==0) $fatal(1,"release edge1 ready early");
@(negedge clk); go=1;
tick(); if(dut.ready!==1 || dut.command_go!==0) $fatal(1,"early GO admitted");
@(negedge clk); go=0;
tick();
tick(); if(f!==1) $fatal(1,"early GO missing fault");
@(negedge clk); rst_n=0;
tick(); if(dut.ready!==1) $fatal(1,"assertion skipped delivery register");
tick(); if(dut.ready!==0 || f!==0 || ov!==0) $fatal(1,"warm reset did not clear controls");
repeat(3) tick();
@(negedge clk); rst_n=1;
tick(); if(dut.ready!==0) $fatal(1,"release edge1");
tick(); if(dut.ready!==1 || dut.ready_d!==0) $fatal(1,"release edge2");
@(negedge clk); go=1;
tick(); if(dut.go_q!==1 || dut.command_go!==1) $fatal(1,"GO capture edge3");
@(negedge clk); go=0;
// The core samples command_go at release edge4 (one cycle after pin capture).
tick(); if(dut.go_q!==0 || f!==0) $fatal(1,"legal GO acceptance edge4");
repeat(12) begin tick(); if(f!==0) $fatal(1,"legal boot fault"); end
$display("PASS native-B cold/warm reset delivery2 ready2 GO_pin3 GO_accept4 early_GO_fault");
$finish;
end
endmodule
'''

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--offsets',type=Path)
    args=ap.parse_args(); repo=Path(__file__).resolve().parents[2]
    out=args.out.resolve(); out.mkdir(parents=True,exist_ok=False); rtl=out/'rtl'; rtl.mkdir()
    _,reports,hashes=stage_sources(repo,rtl)
    macro='physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v'
    (rtl/'ot_rom_4096x274_m8.v').write_bytes(subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+macro]))
    (rtl/'tb_head_boot.sv').write_text(TB)
    results={}
    for name,define in [('positive',None),('mut_early','OT_S81HD_MUT_START_EARLY'),('mut_reset','OT_S81HD_MUT_RST_ASYNC')]:
        command=['verilator','--binary','--timing','-j','8','-O1','-Wno-fatal','--top-module','tb_head_boot','--Mdir',str(out/('obj_'+name))]
        if define: command += ['+define+'+define]
        command += [str(f) for f in sorted(rtl.iterdir())]
        with (out/('build_'+name+'.log')).open('w') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        with (out/('run_'+name+'.log')).open('w') as log:
            proc=subprocess.run([str(out/('obj_'+name)/'Vtb_head_boot')],stdout=log,stderr=subprocess.STDOUT)
        output=(out/('run_'+name+'.log')).read_text()
        ok=(proc.returncode==0 and 'PASS native-B' in output) if not define else (proc.returncode!=0 and 'Assertion failed' in output)
        results[name]={'pass':ok,'returncode':proc.returncode,'output':output}
        if not ok: raise RuntimeError(f'{name} failed; see {out}')
    contract=dict(kind='NATIVE_B_COMPONENT_BOOT_ONLY',source_hashes=hashes,transformations=reports,results=results,
        reset_delivery_cycles=1,ready_edge_after_input_release=2,go_pin_capture_edge=3,go_accept_edge=4,
        activation_word_a_edge_after_go_pin='6+a',steady_state_added_cycles=0,die_start_is_element_go=False,
        mission_release='max(R[p], S+R[p])',bootstrap_release='R[p]; separate local START mission admission required',
        die_boot_status='BLOCKED: actual controller/host/mesh providers and selected source composition required',
        rom_scope='real behavioral ROM zero initialization; control-only, no numerical or token claim')
    if args.offsets:
        offsets=json.loads(args.offsets.read_text()); contract['published_offsets']=offsets
    (out/'boot_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    print(json.dumps({'pass':True,'contract':str(out/'boot_contract.json'),'results':list(results)}))
if __name__=='__main__': main()
