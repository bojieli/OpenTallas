#!/usr/bin/env python3
"""Small native diagnostic-join exact age/reset proof, two required mutants."""
import json
from pathlib import Path
import subprocess
import tempfile
from area_model_1417 import ROOT, LOCK, checked_write, sha

tb='''`timescale 1ns/1ps
module tb;
reg ck=0;always #5 ck=~ck;reg rst=0;reg [9:0] x=0;wire y;
s81_area_id_fault_join dut(ck,rst,x,y);
task tick;begin @(posedge ck);#1;end endtask
initial begin
repeat(5)tick();if(y!==0)$fatal(1,"held reset");
@(negedge ck);rst=1;repeat(5)tick();
for(integer b=0;b<10;b=b+1)begin
 @(negedge ck);x=10'b1<<b;tick();if(y!==0)$fatal(1,"fault arrived early bit%0d",b);
 @(negedge ck);x=0;tick();if(y!==1)$fatal(1,"fault missing bit%0d",b);
 tick();if(y!==0)$fatal(1,"fault stale bit%0d",b);
end
@(negedge ck);rst=0;x=1023;repeat(5)tick();if(y!==0)$fatal(1,"synchronous clear");
$display("PASS tenfaultpins age2physicaledges syncreset");$finish;
end endmodule
'''
source=ROOT/'tools/s81_vm/area_id_native_join.sv';rows=[]
with tempfile.TemporaryDirectory(prefix='s81-a2-fault-') as td:
    td=Path(td);(td/'tb.sv').write_text(tb)
    for variant,replacement in [('gold','|pin_fault'),('early','|i_fault'),('omit9','|pin_fault[8:0]')]:
        assert json.loads(LOCK.read_text())['owner'] in ('claude','codex')
        sv=source.read_text().replace('|pin_fault;',replacement+';');(td/'dut.sv').write_text(sv)
        r=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(td/'test'),str(td/'dut.sv'),str(td/'tb.sv')],capture_output=True,text=True)
        assert r.returncode==0,r.stderr
        r=subprocess.run(['vvp',str(td/'test')],capture_output=True,text=True)
        rows.append(dict(variant=variant,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        assert (r.returncode==0)==(variant=='gold'),rows[-1]
checked_write(ROOT/'results/arch/s81_vm_area_1417/fault_join_proof.json',dict(
    status='COMPONENT_EXACTNESS_ONLY_NO_NATIVE_TIMING',source=str(source.relative_to(ROOT)),source_sha256=sha(source),
    gate_sha256=sha(Path(__file__)),rows=rows))
print(json.dumps(rows,indent=2))
