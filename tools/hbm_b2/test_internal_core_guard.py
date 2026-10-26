"""Contract mutants for internal tiles; strict partition face guard is unchanged."""
import importlib.util,json,sys,tempfile
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'physical/die_plan/hbm_arch_cores';sys.path[:0]=[str(p),str(p.parents[2]/'tools/die_plan')]
import internal_core_guard as G
import face_guard as F
contract=dict(kind='INTERNAL_CORE',partition_rule='R2_INTERNAL_TIMED_IN_PARTITION')
net='''module top(clk,clk_bad,a,y,z); input clk,clk_bad,a; output y,z;
DFFHQN ff(.CLK(clk),.D(a),.Q(y)); mem ram(.clk(clk),.d(a),.q(z)); endmodule'''
lib='''library(x){cell(mem){pin(clk){direction:input;clock:true;} pin(d){direction:input; timing(){related_pin:"clk";timing_type:setup_rising;} timing(){related_pin:"clk";timing_type:hold_rising;}} pin(q){direction:output;timing(){related_pin:"clk";timing_type:rising_edge;}}}}'''
with tempfile.TemporaryDirectory() as tmp:
 kd=Path(tmp);(kd/'macros').mkdir()
 for c in ('tt','ff'):(kd/'macros'/('mem_'+c+'.lib')).write_text(lib)
 fz=dict(source_profile=dict(endpoint_contract=contract),face_shell=None,macros=['mem'],clocks=['clk'],resets=[])
 skip='^(clk|clk_bad)$'
 r=G.guard(net,'top',kd,fz,skip);assert r['verdict']=='PASS',r['fails'];assert len(r['ports']['a']['endpoints'])==2
 assert F.guard(net,'top',skip_re=skip)['verdict']=='FAIL' # shared/direct memory remains strict on partition faces
 for mutant in [net.replace('.clk(clk)', '.clk(clk_bad)'),net.replace('.Q(y)', '.Q(z)'),net.replace('.q(z)', '.q(y)')]:
  assert G.guard(mutant,'top',kd,fz,skip)['verdict']=='FAIL'
 (kd/'macros/mem_ff.lib').write_text(lib.replace('hold_rising','combinational'))
 assert G.guard(net,'top',kd,fz,skip)['verdict']=='FAIL'
 print('PASS internal shared FF+SRAM; strict partition unchanged; crossclock, missing endpoint, multiple-source, missing-hold mutants rejected')
