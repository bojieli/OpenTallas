from pathlib import Path
import json
B=Path(__file__).resolve().parent
pdn='''add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name stdcell -voltage_domains CORE -pins {M7}
add_pdn_stripe -grid stdcell -layer M1 -width 0.018 -pitch 0.54 -offset 0 -followpins
add_pdn_stripe -grid stdcell -layer M2 -width 0.018 -pitch 0.54 -offset 0 -followpins
add_pdn_stripe -grid stdcell -layer M5 -width 0.12 -pitch 4.32 -offset 2.064
add_pdn_stripe -grid stdcell -layer M6 -width 0.288 -pitch 4.32 -offset 1.968
add_pdn_stripe -grid stdcell -layer M7 -width 0.288 -pitch 8.64 -offset 4.128
add_pdn_connect -grid stdcell -layers {M1 M2}
add_pdn_connect -grid stdcell -layers {M2 M5}
add_pdn_connect -grid stdcell -layers {M5 M6}
add_pdn_connect -grid stdcell -layers {M6 M7}
'''
srcs={'hold_tx':'''module hold_tx(input wire clk,input wire [3:0] din,output reg [1:0] a,b);
always @(posedge clk) begin a<=din[1:0]; b<=din[3:2]; end
endmodule
''','hold_rx':'''module hold_rx(input wire clk,input wire [1:0] a,b,output reg [1:0] q);
reg [1:0] ar,br;
always @(posedge clk) begin ar<=a; br<=b; q<=ar^br; end
endmodule
''','hold_parent':'''(* blackbox *) module hold_tx(input wire clk,input wire[3:0]din,output wire[1:0]a,b); endmodule
(* blackbox *) module hold_rx(input wire clk,input wire[1:0]a,b,output wire[1:0]q); endmodule
module hold_parent(input wire clk_send,clk_recv,input wire[3:0] seed,output wire[1:0] q,q_wrong,probe_b);
wire[1:0] sa,sb; reg[1:0] glue_b;
always @(posedge clk_send) glue_b<=seed[3:2]^2'b10;
hold_tx u_send(.clk(clk_send),.din(seed),.a(sa),.b(sb));
hold_rx \\u_r0.u_bs0 (.clk(clk_recv),.a(sa),.b(glue_b),.q(q));
hold_tx u_other(.clk(clk_recv),.din({glue_b,sb}),.a(q_wrong),.b(probe_b));
endmodule
'''}
for n,src in srcs.items():
 k=B/n;k.mkdir(exist_ok=True);(k/'rtl.v').write_text(src)
 parent=n=='hold_parent';W,H=(120.96,60.48) if parent else (17.28,17.28)
 (k/'constraint.sdc').write_text('''create_clock -name clk -period 833 [get_ports clk]
create_clock -name vclk -period 833
set_clock_uncertainty -setup 0 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -clock vclk -max 150 [all_inputs -no_clocks]
set_input_delay -clock vclk -min 100 [all_inputs -no_clocks]
set_output_delay -clock vclk -max 150 [all_outputs]
set_output_delay -clock vclk -min 0 [all_outputs]
''')
 cfg=f'''export DESIGN_NICKNAME = {n}
export DESIGN_NAME = {n}
export PLATFORM = asap7
export VERILOG_FILES = /work/rtl.v
export SDC_FILE = /work/constraint.sdc
export DIE_AREA = 0 0 {W} {H}
export CORE_AREA = 1.08 1.08 {W-1.08} {H-1.08}
export IO_CONSTRAINTS = /work/io.tcl
export PDN_TCL = /work/pdn.tcl
export MIN_ROUTING_LAYER = M2
export MAX_ROUTING_LAYER = M5
export PLACE_DENSITY = 0.4
export GPL_TIMING_DRIVEN = 0
export GPL_ROUTABILITY_DRIVEN = 0
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export LEC_CHECK = 0
export CORNER = TC
export CORNERS = tc
export TC_LIB_FILES = $(TC_NLDM_LIB_FILES)
export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)
export HOLD_SLACK_MARGIN = 15
export SETUP_SLACK_MARGIN = 0
export TNS_END_PERCENT = 100
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets
'''
 if parent:
  cfg+='''export ADDITIONAL_LEFS = /work/macros/hold_tx.lef /work/macros/hold_rx.lef
export ADDITIONAL_LIBS = /work/macros/hold_tx_tt.lib /work/macros/hold_rx_tt.lib
export ADDITIONAL_GDS = /work/macros/hold_tx.gds /work/macros/hold_rx.gds
export TC_LIB_FILES = $(TC_NLDM_LIB_FILES) /work/macros/hold_tx_tt.lib /work/macros/hold_rx_tt.lib
export MACRO_PLACEMENT_TCL = /work/macro_placement.tcl
'''
  (k/'macro_placement.tcl').write_text('''place_macro -macro_name {u_send} -location {17.28 17.28} -orientation R0 -exact
place_macro -macro_name {u_r0.u_bs0} -location {51.84 17.28} -orientation R0 -exact
place_macro -macro_name {u_other} -location {86.4 17.28} -orientation R0 -exact
''')
  (k/'pdn.tcl').write_text(pdn+'''add_pdn_stripe -grid stdcell -layer M8 -width 0.288 -pitch 8.64 -offset 4.128
add_pdn_connect -grid stdcell -layers {M7 M8}
define_pdn_grid -macro -name core_pg_M7 -instances {u_send u_r0.u_bs0 u_other} -voltage_domains {CORE} -halo {0}
add_pdn_connect -grid core_pg_M7 -layers {M7 M8}
''')
 else:(k/'pdn.tcl').write_text(pdn)
 (k/'config.mk').write_text(cfg)
 pins=[('clk_send',17.28,.096,'M5'),('clk_recv',77.76,.096,'M5')] if parent else [('clk',8.64,.096,'M5')]
 if n=='hold_tx':
  pins += [(f'din[{i}]',.096,6.912+i*.864,'M4') for i in range(4)]
  pins += [(f'a[{i}]',W-.096,6.912+i*.864,'M4') for i in range(2)]
  pins += [(f'b[{i}]',W-.096,9.504+i*.864,'M4') for i in range(2)]
 elif n=='hold_rx':
  pins += [(f'a[{i}]',.096,6.912+i*.864,'M4') for i in range(2)]
  pins += [(f'b[{i}]',.096,9.504+i*.864,'M4') for i in range(2)]
  pins += [(f'q[{i}]',W-.096,8.64+i*.864,'M4') for i in range(2)]
 else:
  pins += [(f'seed[{i}]',.096,20+i*.864,'M4') for i in range(4)]
  pins += [(f'{bus}[{i}]',W-.096,15+j*8+i*.864,'M4') for j,bus in enumerate(['q','q_wrong','probe_b']) for i in range(2)]
 pins=[(pn,round(.024+round((x-.024)/.048)*.048,6) if l=='M5' else x,
        round(.024+round((y-.024)/.048)*.048,6) if l=='M4' else y,l) for pn,x,y,l in pins]
 (k/'io.tcl').write_text('\n'.join(f'place_pin -pin_name {{{pn}}} -layer {l} -location {{{x} {y}}} -pin_size {{{"0.192 0.048" if l=="M4" else "0.048 0.192"}}}' for pn,x,y,l in pins)+'\n')
 (k/'planned_pins.json').write_text(json.dumps(pins,indent=1)+'\n')
 (k/'freeze.json').write_text(json.dumps(dict(schema='opentallas.parent-hold-test-vehicle.v1',top=n,outline_um=[W,H],scope='physical hierarchical exporter diagnostic only; minimum logic chosen to test every input bit and distinct source kinds'),indent=1)+'\n')

p=B/'hold_parent'/'constraint.sdc'
s=p.read_text().replace('create_clock -name clk -period 833 [get_ports clk]', 'create_clock -name clk -period 833 [get_ports {clk_send clk_recv}]\nset_clock_latency -source -early -clock clk -35 [get_ports clk_send]\nset_clock_latency -source -late -clock clk 0 [get_ports clk_send]\nset_clock_latency -source -early -clock clk -85 [get_ports clk_recv]\nset_clock_latency -source -late -clock clk 0 [get_ports clk_recv]')
p.write_text(s)
