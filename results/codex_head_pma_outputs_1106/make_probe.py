from pathlib import Path
import json,sys
r=Path(sys.argv[1]).resolve();sys.path[:0]=[str(r/'tools/die_plan')]
import gen_phys as GP
import sdc_lint as SL
from test_pad_output_clock import output_plan
p=output_plan();t=p.types['mid'];ctx=SL.kit_context(p,'mid');sdc=GP.sdc(p,'mid',GP.type_pins(p,'mid'))
assert not SL.lint(sdc,**ctx)
o=Path(sys.argv[2]).resolve();o.mkdir(parents=True,exist_ok=True);(o/'constraint.sdc').write_text(sdc);(o/'context.json').write_text(json.dumps(ctx,indent=1)+'\n')
width={b['name']:b['width']+int(b.get('ep',False)) for b in t.get('buses',[])}
for q in t.get('ft_slots',[]):
 for k in ['_i','_o']:width[q['name']+k]=q['width']+1
width.update({q['name']:q['width'] for q in t.get('pads',[])})
ins=list(dict.fromkeys(ctx['clock_ports']+ctx['inputs']));outs=list(dict.fromkeys(ctx['outputs']+['pma_tck']));ports=ins+outs
lines=['module top('+','.join(ports)+');']
for di,ns in [('input',ins),('output',outs)]:
 for n in ns:
  vec=f'[{width[n]-1}:0] ' if n in width else ''
  lines.append(f'{di} {vec}{n};')
a=next(n for n in ctx['inputs'] if n not in ('arst_n','start_i'));src=a+'[0]' if a in width else a
for k in range(4):lines.append(f'DFFHQNx1_ASAP7_75t_R tx{k}(.CLK(clk),.D({src}),.QN(pma_tx[{k}]));')
lines+=['wire rx_unused;','DFFHQNx1_ASAP7_75t_R rx(.CLK(pma_rck[0]),.D('+src+'),.QN(rx_unused));','BUFx2_ASAP7_75t_R tx_clk_export(.A(clk),.Y(pma_tck[0]));']
for n in outs:
 if n not in ['pma_tx','pma_tck']:
  if n in width:
   lines.extend(f'assign {n}[{k}] = {src};' for k in range(width[n]))
  else:lines.append(f'assign {n} = {src};')
lines.append('endmodule');(o/'top.v').write_text('\n'.join(lines)+'\n')
(o/'probe.tcl').write_text('''read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f {
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
} {read_liberty $f}
read_verilog /work/top.v
link_design top
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
set tx [get_ports {pma_tx[*]}]
if {[llength $tx] != 4} {error "native TX selector is not four real ports"}
set tc [get_clocks pma_tck]
if {[llength $tc] != 1 || ![$tc is_generated]} {error "missing actual exported generated clock"}
set maxp [find_timing_paths -to $tx -path_delay max -group_path_count 1]
set minp [find_timing_paths -to $tx -path_delay min -group_path_count 1]
if {![llength $maxp] || ![llength $minp]} {error "native TX has no actual setup/hold timing path"}
puts "PHY_OUTPUT_MAX_BEGIN"
report_checks -to $tx -path_delay max -format full_clock_expanded -digits 3
puts "PHY_OUTPUT_MIN_BEGIN"
report_checks -to $tx -path_delay min -format full_clock_expanded -digits 3
puts "PHY_OUTPUT_ASSOC_READ_PASS tx_ports [llength $tx] setup_paths [llength $maxp] hold_paths [llength $minp]"
exit
''')
print(o,len(ins),len(outs))
