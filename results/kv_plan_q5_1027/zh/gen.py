# NUMBER-CHECK qkd_ahub zh/recip macro clk delivery: entry -> repeated clock wire -> macro clk pin, NLDM + Elmore pi SPEF
import itertools,os,json
R=2.14161e-2; C=1.13298e-1   # kit setRC_rcx.tcl set_wire_rc -clock (kohm/um, fF/um)
cases=[]
for L,sink,master in [(273.62,'zh1','ot_nhb_zh'),(295.3,'zh0','ot_nhb_zh'),(75.08,'recip','ot_qkh_recip_leaf')]:
  for cell in ['BUFx12f_ASAP7_75t_R','BUFx16f_ASAP7_75t_R','BUFx24_ASAP7_75t_R']:
    for N in [1,2,3,4]:
      cases.append((L,sink,master,cell,N))
tcl=['set P /OpenROAD-flow-scripts/flow/platforms/asap7','set c $::env(CORNER)','set lo [string tolower $c]',
 'read_liberty [glob $P/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${c}_nldm_*.lib*]','read_liberty /work/ot_nhb_zh_${lo}.lib','read_liberty /work/ot_qkh_recip_leaf_${lo}.lib']
os.makedirs('cases',exist_ok=True)
for i,(L,sink,master,cell,N) in enumerate(cases):
  v=[f'module m{i} (ck);','input ck;']+[f'wire n{j};' for j in range(N+1)]
  v.append(f'{cell} b0 (.A(ck), .Y(n0));')
  for j in range(1,N): v.append(f'{cell} b{j} (.A(n{j-1}), .Y(n{j}));')
  v.append(f'{master} u (.clk(n{N-1}));'); v.append('endmodule')
  open(f'cases/m{i}.v','w').write('\n'.join(v)+'\n')
  seg=L/N
  sp=['*SPEF "IEEE 1481-1998"','*DESIGN "m%d"'%i,'*DATE "x"','*VENDOR "x"','*PROGRAM "x"','*VERSION "1"','*DESIGN_FLOW "x"','*DIVIDER /','*DELIMITER :','*BUS_DELIMITER [ ]','*T_UNIT 1 PS','*C_UNIT 1 FF','*R_UNIT 1 KOHM','*L_UNIT 1 HENRY','']
  for j in range(N):
    drv=f'b{j}:Y'; ld=f'b{j+1}:A' if j<N-1 else 'u:clk'
    sp+= [f'*D_NET n{j} {C*seg:.5f}','*CONN',f'*I {drv} O',f'*I {ld} I','*CAP',f'1 {drv} {C*seg/2:.5f}',f'2 {ld} {C*seg/2:.5f}','*RES',f'1 {drv} {ld} {R*seg:.5f}','*END','']
  open(f'cases/m{i}.spef','w').write('\n'.join(sp)+'\n')
  tcl+=[f'read_verilog /work/cases/m{i}.v',f'link_design m{i}',f'read_spef /work/cases/m{i}.spef','set_input_transition 20 [get_ports ck]',
        'set_input_delay 0 [get_ports ck]',
        f'set a [sta::format_time [[sta::worst_slack_vertex] arrival] 3]' if False else
        f'set pth [find_timing_paths -unconstrained -to [get_pins u/clk] -path_delay max]',
        f'set ar [get_property [lindex $pth 0] arrival]',
        f'puts "ROW {i} {L} {sink} {cell} {N} $c $ar"']
open('sta.tcl','w').write('\n'.join(tcl)+'\n')
json.dump(cases,open('cases.json','w'))
