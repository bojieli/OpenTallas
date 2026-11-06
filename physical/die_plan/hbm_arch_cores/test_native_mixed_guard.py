#!/usr/bin/env python3
"""Selected internal seams use typed endpoints; every external face remains exclusive and registered."""
import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(ROOT/'tools/die_plan')]
import internal_core_guard as G
import face_guard as F
import signoff as S
NET='''module top(clk,clk_bad,a,b,c,nctrl,y,z,nout);
input clk,clk_bad,a,b,c,nctrl; output y,z,nout;
wire aq,cq,b0,b1,ctrl_q,en,local_q;
DFFHQN f_a(.CLK(clk),.D(a),.Q(aq));
DFFHQN f_y(.CLK(clk),.D(aq),.Q(y));
DFFHQN f_c(.CLK(clk),.D(c),.Q(cq));
DFFHQN f_z(.CLK(clk),.D(cq),.Q(z));
DFFHQN n0(.CLK(clk),.D(b),.Q(b0));
DFFHQN n1(.CLK(clk),.D(b),.Q(b1));
AND2x2 gate0(.A1(nctrl),.A2(aq),.Y(en));
DFFHQN nc(.CLK(clk),.D(en),.Q(ctrl_q));
AND2x2 gate1(.A1(ctrl_q),.A2(b0),.Y(local_q));
DFFHQN nf(.CLK(clk),.D(local_q),.Q());
assign nout=ctrl_q;
endmodule'''
SCOPE=['b','nctrl','nout']
CONTRACT=dict(kind='INTERNAL_CORE',partition_rule='R2_INTERNAL_TIMED_IN_PARTITION',scope_buses=SCOPE,
              port_roles=dict(b='input',nctrl='input',nout='output'))
FZ=dict(schema='opentallas.hbm_arch.core_kit.v1',design='top',clocks=['clk'],resets=[],macros=[],
        face_shell=dict(native_registered_passthrough=SCOPE,face_cycle_overrides={n:0 for n in SCOPE},
                        native_endpoint_contract=CONTRACT))
SKIP='^(clk|clk_bad)$'
with tempfile.TemporaryDirectory() as tmp:
    kd=Path(tmp)
    assert F.guard(NET,'top',skip_re=SKIP)['verdict']=='FAIL'
    r=G.mixed_guard(NET,'top',kd,FZ,SKIP)
    assert r['verdict']=='PASS',r['fails']
    assert len(r['native_endpoint_census']['ports']['b']['endpoints'])==2
    assert r['native_endpoint_census']['ports']['nctrl']['endpoints']
    assert r['native_endpoint_census']['ports']['nout']['endpoints']
    # External face and native endpoint failures are independent: neither class can hide the other.
    for name,mut in [
        ('native_wrong_clock',NET.replace('n1(.CLK(clk)','n1(.CLK(clk_bad)')),
        ('native_feedthrough',NET.replace('assign nout=ctrl_q','assign nout=nctrl')),
        ('external_unregistered',NET.replace('.Q(y)', '.Q()').replace('assign nout=ctrl_q;','assign nout=ctrl_q; assign y=a;')),
        ('external_shared',NET.replace('.D(cq)', '.D(a)'))]:
        rr=G.mixed_guard(mut,'top',kd,FZ,SKIP)
        assert rr['verdict']=='FAIL',(name,rr)
        print(name,'REJECTED',rr['fail_counts'])
    malformed=copy.deepcopy(FZ);malformed['face_shell']['face_cycle_overrides']['b']=1
    try:G.mixed_guard(NET,'top',kd,malformed,SKIP)
    except ValueError:pass
    else:raise AssertionError('incorrect cycle metadata accepted')
    # Sign-off chooses the same split checker. The second clock is excluded in this dispatch fixture only;
    # the native_wrong_clock case above proves that a capture on that unqualified clock is rejected.
    net=kd/'synth.v';net.write_text(NET.replace('clk_bad,','').replace('clk,clk_bad,','clk,'))
    fz=copy.deepcopy(FZ);(kd/'freeze.json').write_text(json.dumps(fz))
    rr=S.run_face_guard(dict(synth=str(net),kit=str(kd)))
    assert rr['verdict']=='PASS',rr
    print('signoff mixed dispatch PASS',rr['checked'],rr['ok'])
print('test_native_mixed_guard PASS')
