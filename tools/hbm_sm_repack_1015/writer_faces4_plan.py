#!/usr/bin/env python3
"""Literal face plan for a source-exact, half-face-clock writer candidate.
All data cuts use the die lead's two-track0.096um allocation and0.60 limit.
"""
from pathlib import Path
import json,sys,math,hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ref_tile'))
from spread_face_pins import port_widths
base=json.loads((ROOT/'physical/ref_tile/hsm_smvm_wrq_t_r3/spec.json').read_text())
s=base;s['name']='hsm_smvm_wrq_t_r4';s['top']='ot_hbm_sm_vm_wr_q_t_faces4';s['outline']={'w':142.56,'h':388.8}
s['sources']=[p.replace('ot_hbm_sm_vm_wr_q_t_faces.sv','ot_hbm_sm_vm_wr_q_t_faces4.sv').replace('ot_hbm_sm_vm_wr_q_faces.sv','ot_hbm_sm_vm_wr_q_faces4.sv') for p in s['sources']]
s['clock_ports']=['clk','clk_in_lo','clk_in_hi','clk_out_lo','clk_out_hi','clk_cal'];s['clock_cts_roots']=s['clock_ports'][:-1]
s['macros'][0]['at']=[23.328,302.4]
low=['rv_lo','rrow_lo','rdata_lo','sm_fault_lo','sm_sched_fault_lo'];high=[x.replace('_lo','_hi') for x in low]
north=[x for x in s['pins']['N'] if x!='clk']
s['pins']={'W':low+['clk_in_lo']+high+['clk_in_hi','clk_cal'],'E':['wq_lo','clk_out_lo','wq_hi','clk_out_hi'],'N':['clk']+north}
s.pop('pin_ranges',None)
s['clock_entry_domains']={
 'core':{'ratio':[1,1],'ports':['clk'],'inputs':[x for x in north if x not in ['configured','fault','active']],'outputs':['configured','fault','active']},
 'inp_lo':{'ratio':[1,1],'ports':['clk_in_lo'],'inputs':low,'outputs':[]},
 'inp_hi':{'ratio':[1,1],'ports':['clk_in_hi'],'inputs':high,'outputs':[]},
 'out_lo':{'ratio':[1,1],'ports':['clk_out_lo'],'inputs':[],'outputs':['wq_lo']},
 'out_hi':{'ratio':[1,1],'ports':['clk_out_hi'],'inputs':[],'outputs':['wq_hi']},
 'cal':{'ratio':[1,1],'ports':['clk_cal'],'inputs':[],'outputs':[]}}
s['job'].update(tag='faces4',purpose='Candidate within original142.56x388.8 envelope: two actual local capture roots and two actual launch roots by half-face, core + raw calendar. Zero normal data edges added; fresh typed grant/route/native proof required.',views_to='physical/ref_tile/hsm_smvm_wrq_t_r4/views',record_to='results/rtl/ref_tile/hsm_smvm_wrq_t_r4')
s['job']['benches'][0]['cmd']=s['job']['benches'][0]['cmd'].replace('run_sm_vm_wr_q_t_faces.sh','run_sm_vm_wr_q_t_faces4.sh')
s['job']['benches'][0]['pass_regex']='SM_VM_WR_Q_T BENCH PASS'
s['structural_change']='The compactr3 failed the authoritative0.096um/0.60 pin-capacity audit before adoption. r4 returns to original388.8um face, and partitions each face clock into two actual half-face roots. Input control fields split at4SMs to preserve unique source-clock ownership. Body/core and one raw calendar clock are separate. Literal windows reserve all six clock entries; every data window cut<=0.60. Zero ordinary data/calendar stages added. Physical/native/typed grant still pending.'
widths=port_widths(s,ROOT)
clocks={'clk':('N',71.292),'clk_in_lo':('W',97.212),'clk_in_hi':('W',291.612),'clk_out_lo':('E',97.212),'clk_out_hi':('E',291.612),'clk_cal':('W',300.012)}
windows=[('W_lower','W',low,4.332,191.244),('W_upper','W',high,197.556,384.468),('E_lower','E',['wq_lo'],4.332,191.244),('E_upper','E',['wq_hi'],197.556,384.468),('N_core','N',north,4.332,138.228)]
lines=['# Candidate exact source-derived plan. Allocation:0.096um/bit, max cut0.60.'];pins={};metrics=[]
def emit(name,face,pos,clock=False):
 layer='M4' if face in ['W','E'] else 'M5'
 x=0 if face=='W' else s['outline']['w'] if face=='E' else pos
 y=0 if face=='S' else s['outline']['h'] if face=='N' else pos
 size=(.084,.024) if clock and face in ['W','E'] else (.192,.024) if face in ['W','E'] else (.024,.084)
 assert name not in pins,name
 rect=[x-size[0]/2,y-size[1]/2,x+size[0]/2,y+size[1]/2]
 if face=='W':rect[0]=0;rect[2]=size[0]
 if face=='E':rect[0]=x-size[0];rect[2]=x
 if face=='N':rect[1]=y-size[1];rect[3]=y
 pins[name]={'face':face,'layer':layer,'position_um':pos,'clock':clock,'rectangle_um':[round(z,6) for z in rect]}
 lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{size[0]:.3f} {size[1]:.3f}}} -force_to_die_boundary')
for label,face,ports,a,b in windows:
 bits=[]
 for p in ports:
  n,vec=widths[p];bits += [f'{p}[{i}]' if vec else p for i in range(n)]
 notches=[v for f,v in clocks.values() if f==face and a<=v<=b]
 phase=.012 # Actual current-generator ODB readback, M4 Y and M5 X.
 tracks=[round(phase+.048*k,3) for k in range(math.ceil((a-phase)/.048),math.floor((b-phase)/.048)+1)]
 tracks=[x for x in tracks if all(abs(x-v)>=1.08-1e-8 for v in notches)]
 usable=b-a-len(notches)*2.16;cut=len(bits)*.096/usable
 assert cut<=.60,(label,len(bits),usable,cut)
 chosen=[tracks[round(i*(len(tracks)-1)/(len(bits)-1))] for i in range(len(bits))] if len(bits)>1 else [tracks[len(tracks)//2]]
 assert len(chosen)==len(set(chosen));assert all(y-x>=.096-1e-7 for x,y in zip(chosen,chosen[1:]))
 for p,x in zip(bits,chosen):emit(p,face,x)
 metrics.append({'window':label,'data_bits':len(bits),'span_um':[a,b],'reserved_clock_centres_um':notches,'usable_face_um':round(usable,6),'allocation_um_per_bit':.096,'cut':cut,'minimum_physical_pin_pitch_um':round(min(y-x for x,y in zip(chosen,chosen[1:])),6)})
for p,(face,pos) in clocks.items():emit(p,face,pos,True)
# Verify the actual DB after literal placement, including the actual layer grid.
lines += ['set fp_b [ord::get_db_block]', 'set fp_u [$fp_b getDbUnitsPerMicron]', 'set fp_bad 0', 'set fp_checked 0', '''
proc writer_pin_check {name layer axis pos rect} {
 global fp_b fp_u fp_bad fp_checked
 set t [$fp_b findBTerm $name]
 if {$t eq "NULL" || $t eq ""} {incr fp_bad; puts "WRITER_FACE_PIN_MISSING $name";return}
 if {[llength [$t getBPins]] != 1} {incr fp_bad; puts "WRITER_FACE_BPIN_COUNT $name";return}
 set p [lindex [$t getBPins] 0]
 if {[llength [$p getBoxes]] != 1} {incr fp_bad; puts "WRITER_FACE_BOX_COUNT $name";return}
 set q [lindex [$p getBoxes] 0]
 incr fp_checked
 set l [$q getTechLayer]
 set actual [list [expr {[$q xMin]/double($fp_u)}] [expr {[$q yMin]/double($fp_u)}] [expr {[$q xMax]/double($fp_u)}] [expr {[$q yMax]/double($fp_u)}]]
 foreach a $actual e $rect {if {abs($a-$e)>0.0001} {incr fp_bad; puts "WRITER_FACE_RECT_ERROR $name $actual expected $rect";break}}
 if {$axis eq "Y"} {set c [expr {([$q yMin]+[$q yMax])/2.0}]} else {set c [expr {([$q xMin]+[$q xMax])/2.0}]}
 set g [[$fp_b findTrackGrid $l] getGrid$axis]
 if {abs($c/double($fp_u)-$pos)>0.0001 || [$l getName] ne $layer || [lsearch -exact $g [expr {int(round($c))}]]<0} {
  incr fp_bad; puts "WRITER_FACE_PIN_ERROR $name"
 }
}
''']
for name,v in pins.items():
 face=v['face'];pos=v['position_um'];layer=v['layer'];axis='Y' if face in ['W','E'] else 'X'
 rect=' '.join(f'{x:.3f}' for x in v['rectangle_um'])
 lines += [f'writer_pin_check {{{name}}} {layer} {axis} {pos:.3f} {{{rect}}}']
lines += [f'if {{$fp_checked != {len(pins)}}} {{incr fp_bad}}', 'puts "WRITER_FACE_PIN_READBACK checked=$fp_checked violations=$fp_bad"', 'if {$fp_bad} {error "Writer literal pins violate actual track/location"}']
expected=sum(n for n,_ in widths.values());assert len(pins)==expected,(len(pins),expected)
pf=ROOT/'physical/ref_tile_specs/smh/smvm_writer_faces4_pins.tcl';pf.write_text('\n'.join(lines)+'\n');s['io_tcl']=str(pf.relative_to(ROOT))
p=ROOT/'physical/ref_tile/hsm_smvm_wrq_t_r4';p.mkdir(exist_ok=True);(p/'spec.json').write_text(json.dumps(s,indent=2)+'\n')
r={'schema':'opentallas.writer_faces4_pin_candidate.v1','status':'CANDIDATE_REQUIRES_TYPED_GRANT_AND_PHYSICAL_PROOF','actual_top':s['top'],'actual_clock_ports':s['clock_ports'],'outline_um':[142.56,388.8],'normal_data_edges_added':0,'windows':metrics,'full_face_bits':{f:sum(1 for v in pins.values() if v['face']==f) for f in ['W','E','N']},'all_ports_accounted':expected,'pinfile_sha256':hashlib.sha256(pf.read_bytes()).hexdigest(),'pins':pins}
(ROOT/'results/physical/hsm_takeover_0825/writer_faces4_pins.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='pins'},indent=2))
