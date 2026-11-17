from pathlib import Path
import subprocess,re,json,hashlib
L=Path('/srv/opentallas-scratch2/claude/head-die-r');O=L/'reset_entry_handoff_model_1117';O.mkdir(exist_ok=True)
N=30;lines=['module handoff(input clk,input d0,input d1,output q0,output q1);','wire '+','.join(f'c{i}' for i in range(N))+';','wire z0,z1;']
for i in range(N):lines.append(f'BUFx4_ASAP7_75t_R b{i}(.A({"clk" if i==0 else "c"+str(i-1)}),.Y(c{i}));')
for k in range(2):lines += [f'DFFHQNx1_ASAP7_75t_R capture{k}(.CLK(c29),.D(d{k}),.QN(z{k}));',f'DFFHQNx1_ASAP7_75t_R hand{k}(.CLK(clk),.D(z{k}),.QN(q{k}));']
lines.append('endmodule');(O/'handoff.v').write_text('\n'.join(lines)+'\n');rows=[]
def spef(cp,dp):
 s=['*SPEF "ieee 1481-1999"','*DESIGN "handoff"','*DATE "2026-11-17"','*VENDOR "OpenTallas"','*PROGRAM "model"','*VERSION "1"','*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"','*DIVIDER /','*DELIMITER :','*BUS_DELIMITER []','*T_UNIT 1 PS','*C_UNIT 1 FF','*R_UNIT 1 OHM','*L_UNIT 1 HENRY']
 def net(n,src,dests,lengths):
  cs=[x*.186*1.13 for x in lengths];rs=[x*29.7127 for x in lengths]
  s.extend([f'*D_NET {n} {sum(cs)}','*CONN',f'*I {src} O']+[f'*I {d} I' for d in dests]+['*CAP',f'1 {src} {sum(cs)/2}']+[f'{i+2} {d} {c/2}' for i,(d,c) in enumerate(zip(dests,cs))]+['*RES']+[f'{i+1} {src} {d} {rr}' for i,(d,rr) in enumerate(zip(dests,rs))]+['*END'])
 for i in range(N-1):net(f'c{i}',f'b{i}:Y',[f'b{i+1}:A'],[cp])
 net('c29','b29:Y',['capture0:CLK','capture1:CLK'],[dp,dp])
 for k in range(2):net(f'z{k}',f'capture{k}:QN',[f'hand{k}:D'],[dp])
 return '\n'.join(s)+'\n'
for cp in [0,.81,1.35]:
 for dp in [.81,2.7,5.4]:
  tag=f'c{cp}_d{dp}';sp=O/f'{tag}.spef';sp.write_text(spef(cp,dp))
  for corner in ['TT','FF']:
   lib=Path('/home/ubuntu/.cache/opentallas/asap7_nldm');tcl=O/f'{tag}_{corner}.tcl';log=tcl.with_suffix('.log')
   tcl.write_text(f'''read_liberty {lib}/asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz
read_liberty {lib}/asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib
read_verilog {O}/handoff.v
link_design handoff
create_clock -name clk -period 833 [get_ports clk]
set_clock_transition 57.46 [all_clocks]
set_input_transition 57.46 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty 0 -setup [all_clocks]
set_clock_uncertainty 25 -hold [all_clocks]
read_spef {sp}
set pins [get_pins [list hand0/D hand1/D]]
foreach p $pins {{puts "HANDOFF {corner} [get_full_name $p] setup [get_property $p slack_max] hold [get_property $p slack_min]"}}
report_checks -from [get_pins [list capture0/QN capture1/QN]] -to $pins -path_delay min_max -format full_clock_expanded -digits 6 -fields {{slew cap fanout}}
''')
   rc=subprocess.run(['/home/ubuntu/.local/opentallas-tools/bin/sta','-no_splash','-threads','1','-exit',str(tcl)],stdout=log.open('w'),stderr=subprocess.STDOUT).returncode
   txt=log.read_text();vals=[]
   for m in re.finditer(r'HANDOFF (\w+) (\S+) setup ([-+\w.]+) hold ([-+\w.]+)',txt):
    try:vals.append(dict(pin=m[2],setup_ps=float(m[3]),hold_ps=float(m[4])))
    except ValueError:pass
   rows.append(dict(clock_pitch_um=cp,data_and_last_clock_hop_um=dp,corner=corner,returncode=rc,paths=vals,log=str(log)))
r=dict(schema='opentallas.reset_entry_handoff_model.v1',status='COMPONENT_MODEL_ONLY',scope='N30 shared late-clock capture2FF plus2newlocalhandoffFF. Source root clock transition57.46ps,833psperiod,0setup25hold. M2perlengthR29.7127ohm/um,C.186*1.13fF/um. PureNLDM+pi-RC,not routedphysicalevidence. Real incoming sourceclockphase and outgoinghandofffanout mustgate fullshape; no clockuncertainty/IO exception.',added_handoff_ff=2,added_handoff_area_um2=.5832,shared_clock_buffer_cells=30,shared_clock_buffer_area_um2=3.0618,added_boot_control_cycles=1,added_arithmetic_cycles=0,rows=rows)
(O/'result.json').write_text(json.dumps(r,indent=1)+'\n');print('MODEL',len(rows),'rc_fail',sum(x['returncode']!=0 for x in rows));print(json.dumps(rows[-4:],indent=1))
