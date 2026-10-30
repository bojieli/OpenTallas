#!/usr/bin/env python3
"""Prepare a direct current-RTL reset-depth probe, without changing RTL."""
import json, sys
from pathlib import Path
r, out = map(Path, sys.argv[1:3]); out.mkdir(parents=True,exist_ok=True)
records=json.loads((r/'results/s81_h2_interfaces_2258/interfaces.json').read_text())['masters']
tb=['`timescale 1ps/1ps','module ln_h2_rst;', 'reg clk=0; always begin #416 clk=1; #417 clk=0; end',
    'reg rs_k=1,rs_n=1; integer hold_edges=64; integer errors=0,checks=0; reg [1:0] checkmask=0;',
    'integer cold_errors;']
for idx,m in enumerate(('ot_s81_mu72_lnland_nst','ot_s81_mu72_lnland')):
    con=[]
    for n,v in records[m]['ports'].items():
        if v['direction']!='input':continue
        val='clk' if n in ('ck_k','ck_n') else n if n in ('rs_k','rs_n') else f"{v['bits']}'d0"
        con.append(f'.{n}({val})')
    tb.append(f'{m} #(.MUT(0)) dut{idx} ('+', '.join(con)+');')
    for d in ('kn','nk'):
        for j in range(70):
            for typ in ('w','r'):
                root=('k' if d=='kn' else 'n') if typ=='w' else ('n' if d=='kn' else 'k')
                path=f'dut{idx}.u_{d}.u_{typ}.g_chunk[{j}].u_local'
                cond=f'{path}.rq !== 1\'b0 || '
                if typ=='w':cond+=f'{path}.wc !== 3\'d0 || {path}.valid !== 4\'d0 || {path}.write_oh !== 4\'b0001'
                else:cond+=f'{path}.rc !== 3\'d0 || {path}.warm !== 1\'b0 || {path}.read_oh !== 4\'b0100 || {path}.o !== 0'
                bit=0 if root=='k' else 1
                tb += [f'always @(negedge clk) if(checkmask[{bit}]) begin', ' checks=checks+1;',
                       f' if ({cond}) begin errors=errors+1; if(errors<4) $display("RESET_BAD {path} rq=%b",{path}.rq); end','end']
tb += ['task check_hold; input [1:0] mask; input integer cycles; begin',
       ' @(negedge clk); rs_k=!mask[0]; rs_n=!mask[1];',
       ' repeat(cycles) begin @(posedge clk); #1; end',
       ' checkmask=mask; @(negedge clk); #1; checkmask=0;',
       'end endtask',
       'task run_release; begin @(negedge clk); rs_k=1;rs_n=1;repeat(40) @(posedge clk);end endtask',
       'initial begin',
       ' if($value$plusargs("HOLD=%d",hold_edges)) begin end',
       ' check_hold(3,hold_edges); cold_errors=errors;',
       ' if(hold_edges<64) begin $display("LN_RESET_SHORT hold=%0d checks=%0d errors=%0d",hold_edges,checks,errors); if(errors) $fatal(1,"RESET_CHECK_FAIL"); else $finish; end',
       ' run_release();check_hold(1,64);run_release();check_hold(2,64);run_release();check_hold(3,64);',
       ' $display("LN_RESET64 checks=%0d errors=%0d cold_errors=%0d independent_k=1 independent_n=1 warm_both=1",checks,errors,cold_errors);',
       ' if(errors) $fatal(1,"RESET_CHECK_FAIL");else $finish;end','endmodule']
(out/'tb_ln_h2_rst.sv').write_text('\n'.join(tb)+'\n')
spec=json.loads((r/'physical/die_plan/s81/cores/h2/ot_s81_mu72_lnland_nst/spec.json').read_text())
cmd=['/home/ubuntu/.local/opentallas-tools/bin/verilator','--binary','--timing','--x-initial','unique','--x-assign','unique','-Wno-fatal','-Wno-WIDTH','--top-module','ln_h2_rst','--Mdir',str(out/'obj'),'--build-jobs','2','-DSYNTHESIS']
cmd += ['-D'+x for x in spec.get('defines',[])]+[str(r/x) for x in spec['sources']]+[str(out/'tb_ln_h2_rst.sv')]
(out/'command.json').write_text(json.dumps(cmd,indent=1)+'\n')
import subprocess
with (out/'build.log').open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
if rc:sys.exit(rc)
res={}
for mode,edges in [('baseline64',64),('short4_control',4)]:
    with (out/f'{mode}.log').open('w') as log:rc=subprocess.run([str(out/'obj/Vln_h2_rst'),'+verilator+rand+reset+2','+verilator+seed+3',f'+HOLD={edges}'],stdout=log,stderr=subprocess.STDOUT).returncode
    res[mode]=dict(rc=rc,log=(out/f'{mode}.log').read_text())
res['verdict']='PASS' if res['baseline64']['rc']==0 and res['short4_control']['rc']!=0 else 'FAIL'
res['scope']='Current exact plain LN + _nst, both same-frequency clock roots on actual parent clk; independent resets retained. Control state only, reset-free payload not reset.'
(out/'result.json').write_text(json.dumps(res,indent=1)+'\n')
print(json.dumps(res));sys.exit(0 if res['verdict']=='PASS' else 1)
