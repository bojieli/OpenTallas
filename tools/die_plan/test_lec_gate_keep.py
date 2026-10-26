"""Preserve physical unused FF copies in formal prep; actual folded copies still fail KEEP."""
import shutil
import subprocess
from pathlib import Path
import pytest
import lec

GATE = r'''
module DFFHQNx1_ASAP7_75t_R(input CLK,D,output QN);
reg IQN;always @(posedge CLK) IQN<=~D;assign QN=IQN;
endmodule
module INVx3_ASAP7_75t_R(input A,output Y);assign Y=~A;endmodule
(* keep_hierarchy="yes" *)
module physical_copy(input C,D,output Q);
wire n;
DFFHQNx1_ASAP7_75t_R \Q$_DFF_P_ (.CLK(C),.D(D),.QN(n));
INVx3_ASAP7_75t_R inv(.A(n),.Y(Q));
endmodule
module dut(input C,D,output Q);
wire unused;
(* keep=1,keep_hierarchy="yes" *) physical_copy copy0(.C(C),.D(D),.Q(Q));
(* keep=1,keep_hierarchy="yes" *) physical_copy copy1(.C(C),.D(D),.Q(unused));
endmodule
module lec_top(input C,D,output Q);dut u_dut(C,D,Q);endmodule
'''


def test_real_physical_unused_copy_survives_and_fold_mutant_fails_KEEP(tmp_path):
    exe=shutil.which('yosys')
    if not exe:pytest.skip('yosys required')
    caps=subprocess.run([exe,'-Q','-p','help dffunmap; help flatten'],capture_output=True,text=True)
    if 'noscopeinfo' not in caps.stdout or 'No such command' in caps.stdout:
        pytest.skip('requires fleet Yosys formal-preparation commands')
    ff=tmp_path/'lecff.v';ff.write_text(lec.LECFF_V)
    results={}
    for name,keep,fold in [('old',False,False),('fixed',True,False),('physical_fold',True,True)]:
        src=GATE
        if fold:
            src=src.replace('(* keep=1,keep_hierarchy="yes" *) physical_copy copy1(.C(C),.D(D),.Q(unused));','assign unused=Q;')
        sv=tmp_path/(name+'.sv');sv.write_text(src);out=tmp_path/name
        cmds=[f'read_verilog -sv {sv}','hierarchy -check -top lec_top',
              'setattr -mod -unset keep_hierarchy','setattr -unset keep_hierarchy','proc']
        if keep:cmds.append(lec.GATE_PHYSICAL_FF_KEEP)
        cmds+=['flatten -noscopeinfo','opt_clean','techmap','opt_clean']
        cmds+=[c.format(lecff=ff,out=out) for c in lec.SEQ_TAIL]
        p=subprocess.run([exe,'-Q','-q','-p','; '.join(cmds)],capture_output=True,text=True)
        assert p.returncode==0,p.stdout+p.stderr
        results[name]=(lec.read_aig(str(out)+'.aig'),lec.read_map(str(out)+'.map'))
    gold,gmap=results['fixed']
    keepfile=tmp_path/'gold.keep';keepfile.write_text('lec_top/u_dut.copy0.Q\nlec_top/u_dut.copy1.Q\n')
    for name,want in [('fixed',0),('old',1),('physical_fold',1)]:
        aig,amap=results[name];L=lec.Lec(gold,gmap,aig,amap)
        declared,missing,const=lec.kept_registers(L,keepfile)
        assert len(declared)==2 and len(missing)==want and not const,(name,declared,missing,const)
    assert results['fixed'][0]['L']==2
    assert results['old'][0]['L']==results['physical_fold'][0]['L']==1


def test_gate_physical_state_kept_before_flatten():
    s=lec.gate_script({},'gate.v','stub.v','wrap.v','ff.v','/o/gate')
    assert s.index(lec.GATE_PHYSICAL_FF_KEEP)<s.index('flatten -noscopeinfo')
