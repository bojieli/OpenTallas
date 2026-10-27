# q5 zh-pair drop: die island buffer at the new ahub clock pin drives the zh pair directly (stubs from the pin).
# Also: M7-RC bound on the q4 centre-entry delivery (R/C of M7 calibrated table) for the NUMBER-CHECK.
import os
Rc,Cc=2.14161e-2,1.13298e-1   # set_wire_rc -clock (kit setRC_rcx.tcl)
R7,C7=1.25096e-2,9.25000e-2   # M7 set_layer_rc (kit)
hdr=['*SPEF "IEEE 1481-1998"','*DESIGN "x"','*DATE "x"','*VENDOR "x"','*PROGRAM "x"','*VERSION "1"','*DESIGN_FLOW "x"','*DIVIDER /','*DELIMITER :','*BUS_DELIMITER [ ]','*T_UNIT 1 PS','*C_UNIT 1 FF','*R_UNIT 1 KOHM','*L_UNIT 1 HENRY','']
tcl=['set P /OpenROAD-flow-scripts/flow/platforms/asap7','set c $::env(CORNER)','set lo [string tolower $c]',
 'read_liberty [glob $P/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${c}_nldm_*.lib*]','read_liberty /work/ot_nhb_zh_${lo}.lib']
os.makedirs('c2',exist_ok=True)
# pair: S pair stubs from pin (190.08,73.44): zh0 pin (177.078,71.94) -> 14.502; zh1 (198.762,71.94) -> 10.182 (Manhattan)
for cell in ['BUFx12f_ASAP7_75t_R','BUFx24_ASAP7_75t_R']:
  n=f'pair_{cell[:7]}'
  open(f'c2/{n}.v','w').write(f'module {n} (ck);\ninput ck;\nwire n0;\n{cell} b0 (.A(ck), .Y(n0));\not_nhb_zh u0 (.clk(n0));\not_nhb_zh u1 (.clk(n0));\nendmodule\n')
  L0,L1=14.502,10.182
  sp=hdr+[f'*D_NET n0 {Cc*(L0+L1):.5f}','*CONN','*I b0:Y O','*I u0:clk I','*I u1:clk I','*CAP',f'1 b0:Y {Cc*(L0+L1)/2:.5f}',f'2 u0:clk {Cc*L0/2:.5f}',f'3 u1:clk {Cc*L1/2:.5f}','*RES',f'1 b0:Y u0:clk {Rc*L0:.5f}',f'2 b0:Y u1:clk {Rc*L1:.5f}','*END','']
  open(f'c2/{n}.spef','w').write('\n'.join(sp)+'\n')
  tcl+=[f'read_verilog /work/c2/{n}.v',f'link_design {n}',f'read_spef /work/c2/{n}.spef','set_input_transition 20 [get_ports ck]','set_input_delay 0 [get_ports ck]',
        f'puts "ROW2 {n} u0 $c"','report_checks -unconstrained -to [get_pins u0/clk] -digits 2 -fields {slew cap}',f'puts "ROW2 {n} u1 $c"','report_checks -unconstrained -to [get_pins u1/clk] -digits 2 -fields {slew cap}']
# M7-RC bound on centre-entry delivery
for L,s in [(273.62,'zh1'),(295.3,'zh0')]:
  for N in [2,3,4]:
    n=f'm7_{s}_{N}'; cell='BUFx12f_ASAP7_75t_R'
    v=[f'module {n} (ck);','input ck;']+[f'wire n{j};' for j in range(N)]+[f'{cell} b0 (.A(ck), .Y(n0));']+[f'{cell} b{j} (.A(n{j-1}), .Y(n{j}));' for j in range(1,N)]+[f'ot_nhb_zh u (.clk(n{N-1}));','endmodule']
    open(f'c2/{n}.v','w').write('\n'.join(v)+'\n'); seg=L/N; sp=list(hdr)
    for j in range(N):
      d=f'b{j}:Y'; l=f'b{j+1}:A' if j<N-1 else 'u:clk'
      sp+=[f'*D_NET n{j} {C7*seg:.5f}','*CONN',f'*I {d} O',f'*I {l} I','*CAP',f'1 {d} {C7*seg/2:.5f}',f'2 {l} {C7*seg/2:.5f}','*RES',f'1 {d} {l} {R7*seg:.5f}','*END','']
    open(f'c2/{n}.spef','w').write('\n'.join(sp)+'\n')
    tcl+=[f'read_verilog /work/c2/{n}.v',f'link_design {n}',f'read_spef /work/c2/{n}.spef','set_input_transition 20 [get_ports ck]','set_input_delay 0 [get_ports ck]',
          f'puts "ROW2 {n} u $c"','report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}']
open('sta2.tcl','w').write('\n'.join(tcl)+'\n')
