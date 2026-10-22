#!/usr/bin/env python3
"""Actual-image, standalone read-only interpolation/envelope calibration."""
import pathlib,subprocess,json,re,hashlib
P=pathlib.Path(__file__).resolve().parent
IMAGE='openroad/orfs:asap7lock'
OR='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
PLAT='/OpenROAD-flow-scripts/flow/platforms/asap7'
LIB=PLAT+'/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz'
M='ot_sram_1r1w_32x546_m1'
def docker(args):
 r=subprocess.run(['docker','run','--rm','-v',str(P)+':/work',IMAGE,*args],text=True,capture_output=True)
 if r.returncode:
  (P/('diagnostic_'+str(len(list(P.glob('diagnostic_*.log'))))+'.log')).write_text(r.stdout+r.stderr)
  raise RuntimeError(r.stdout+r.stderr)
 return r.stdout+r.stderr
headers=['TableModel.hh','TimingArc.hh','Liberty.hh']
meta=docker(['sh','-ec','sha256sum '+OR+' '+LIB+' '+' '.join('/OpenROAD-flow-scripts/tools/install/OpenROAD/include/sta/'+h for h in headers)+'; '+OR+' -version'])
(P/'native_identity.log').write_text(meta)
compile='''mkdir -p /work/fmtinclude; ln -sfn /usr/local/include/spdlog/fmt/bundled /work/fmtinclude/fmt; g++ -std=c++20 -shared -fPIC -I/OpenROAD-flow-scripts/tools/install/OpenROAD/include -I/usr/include/tcl -I/work/fmtinclude /work/envelope.cc -o /work/native_accessor.so'''
(P/'compile.log').write_text(docker(['sh','-ec',compile]))
(P/'probe.v').write_text(f'module probe(input clk,input en,output [545:0] q); wire [545:0] mid; wire dep; {M} launch(.clk(clk),.r_ce_in(en),.rd_out(mid)); INVx1_ASAP7_75t_R dependent(.A(mid[0]),.Y(dep)); {M} capture(.clk(clk),.r_ce_in(en),.wd_in({{545\'b0,dep}}),.rd_out(q)); endmodule\n')
script=f'''read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/{M}.lef
read_liberty {LIB}
read_liberty /work/{M}_tt.lib
read_verilog /work/probe.v
link_design probe
set_mode calibration
create_clock -name core -period 2000 [get_ports clk]
set_clock_transition 20 [all_clocks]
define_scene TT -mode calibration -liberty_min [list {LIB} /work/{M}_tt.lib] -liberty_max [list {LIB} /work/{M}_tt.lib]
set_scene TT
load /work/native_accessor.so Otenvelope
set stream [open /work/tables.ndjson w]
'''
# Native coordinates are SI seconds/farads, independently visible in raw axes.
for bound in ('min','max'):
 for inst,fr,to in (('dependent','A','Y'),('launch','clk','rd_out[0]'),('capture','clk','wd_in[0]')):
  for x,y in ((0,0),(0,0.72e-15),(5e-12,.72e-15),(2.5e-12,1e-15),(20e-12,2.88e-15),(320e-12,46.08e-15),(800e-12,46.08e-15)):
   script+=f'puts $stream "TABLE {inst} {bound} [ot_envelope_query {inst} {bound} {x} {y} {{{fr}}} {{{to}}}]"\n'
script+='close $stream\n'
script+='report_checks -path_delay min_max -from [get_pins {launch/rd_out[0]}] -to [get_pins {capture/wd_in[0]}] -format full_clock_expanded -digits 6\n'
script+='puts "MIN_ARR [get_property [get_pins dependent/Y] arrival_min_rise]"\nputs "MAX_ARR [get_property [get_pins dependent/Y] arrival_max_rise]"\nexit\n'
(P/'native.tcl').write_text(script)
out=docker([OR,'-no_init','-exit','/work/native.tcl']);(P/'native.log').write_text(out)
if '[ERROR' in out or 'Error:' in out:raise RuntimeError(out[-3000:])
records=[]
for line in (P/'tables.ndjson').read_text().splitlines():
 if line.startswith('TABLE '):
  _,inst,bound,data=line.split(' ',3)
  records.append(dict(instance=inst,bound=bound,arcs=json.loads(data)))
assert len(records)==42
(P/'native_tables.json').write_text(json.dumps(records,indent=2)+'\n')
image=subprocess.check_output(['docker','image','inspect',IMAGE,'--format','{{.Id}}'],text=True).strip()
(P/'receipt.json').write_text(json.dumps(dict(image_id=image,scope='Same-corner TT native NLDM API research; unchanged legacy macro and native INV. Not SC2 characterization.',queries=len(records),image_tag=IMAGE),indent=2)+'\n')
print('NATIVE_ENVELOPE_CALIBRATION_PASS')
