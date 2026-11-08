"""Private exact hierarchical FDI extraction and isolated core plan, never a POR write."""
import argparse,json,subprocess,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4] if HERE.name=='fdi_1108' else Path('/srv/opentallas-scratch2/claude/codex-kv-wisplit-0222/fdi_repo')
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
source='physical/die_plan/qwen_kvsys/bind/kv45/qkd_host_root_admission_obsx_bo1_c45.sv'
ref=subprocess.check_output(['git','-C',str(REPO),'show','HEAD:'+source],text=True)
old='ot_fdi_join2 #(.WA(522), .WB(521), .DEPTH(16)) u_fdi_join ('
assert ref.count(old)==1
new=ref.replace(old,'(* keep_hierarchy = "yes" *) ot_kv_fdi_join_rf #(.WA(522), .WB(521), .DEPTH(16)) u_fdi_join (')
assert new.replace('(* keep_hierarchy = "yes" *) ot_kv_fdi_join_rf #(.WA(522), .WB(521), .DEPTH(16)) u_fdi_join (',old)==ref
(out/'native_parent_fdi_rf.sv').write_text(new)
ports={'clk':['input',0,0],'rst_n':['input',0,0],'a_v':['input',0,0],'a_d':['input',521,0],'b_v':['input',0,0],'b_d':['input',520,0],'o_v':['output',0,0],'o_d':['output',1042,0]}
W=H=198.72;pins=[];classes={}
def bus(base,n,face,layers):
 for i in range(n):
  name=base if n==1 else f'{base}[{i}]';L=layers[i%len(layers)];j=i//len(layers);cnt=math.ceil((n-i%len(layers))/len(layers));v=4.32+(j+.5)/cnt*(W-8.64);pitch=.048 if L in('M4','M5') else .064;off=.024 if L in('M4','M5') else .032;v=round((v-off)/pitch)*pitch+off
  x,y=(.096,v) if face=='W' else (W-.096,v) if face=='E' else (v,H-.096) if face=='N' else (v,.096)
  pins.append({'name':name,'layer':L,'x':round(x,6),'y':round(y,6)});classes[name]='clk' if base=='clk' else 'out' if base in('o_v','o_d')else'in'
# Keep sideband and payload on the same face; reserve their own non-overlapping tracks.
bus('a_d',522,'W',['M4','M6']);bus('b_d',521,'N',['M5','M7']);bus('o_d',1043,'E',['M4','M6'])
for base,face,L,pos in [('a_v','W','M4',2.232),('b_v','N','M5',2.232),('o_v','E','M4',2.232),('rst_n','S','M5',99.384)]:
 x,y=(.096,pos) if face=='W' else(W-.096,pos)if face=='E'else(pos,H-.096)if face=='N'else(pos,.096);pins.append({'name':base,'layer':L,'x':x,'y':y});classes[base]='out'if base=='o_v'else'in'
pins.append({'name':'clk','layer':'M5','x':99.384,'y':99.36});classes['clk']='clk'
json.dump({'schema':'opentallas.die_plan.core_pins.v1','core':'ot_kv_fdi_join_rf','outline_um':[W,H],'pins':pins},open(out/'fdi_pins.json','w'),indent=1)
hc={'inst':'u_fdi','module':'ot_kv_fdi_join_rf','origin_um':[8.64,8.64],'outline_um':[W,H],'pins_file':'fdi_pins.json','cells':100000,'note':'Private isolated hardening form; no production die placement'}
plan={'schema':'opentallas.die_plan.v1','die':{'name':'private_fdi_trial','period_ps':833,'grid_um':8.64,'outline_um':[216.0,216.0]},'clock':{'common_latency_ps':250,'insertion_ps':250,'insertion_ff_ps':202.5,'insertion_tol_ps':40},'partition_types':{'fdi_trial':{'module':'fdi_trial_part','outline_um':[216.0,216.0],'hard_cores':[hc],'buses':[]}},'partitions':[{'name':'trial','type':'fdi_trial','origin_um':[0,0],'orient':'R0'}]}
json.dump(plan,open(out/'private_plan.json','w'),indent=1)
json.dump({'module':'ot_kv_fdi_join_rf','type':'fdi_trial','inst':'u_fdi','port_decl':ports,'pin_class':classes,'files':['rtl/physical/ot_fdi_join2.sv','rtl/physical/ot_kv_fdi_join_rf.sv'],'report':{'clock_nets':{'clk':'clk'},'added':[],'straps':[]}},open(out/'core.json','w'),indent=1)
(out/'kit_rtl/fdi_trial').mkdir(parents=True,exist_ok=True);json.dump({'hard_macros':{}},open(out/'kit_rtl/fdi_trial/kit_rtl.json','w'))
json.dump({'_default':{'util':.40,'sigmax':'M6','face_flops':True,'synth_memory_max_bits':16384}},open(out/'recipes.json','w'),indent=1)
model={'source_module':'ot_fdi_join2','parameters':{'WA':522,'WB':521,'DEPTH':16},'interface_ports':list(ports),'handshake':'valid-only input streams, no ready/credits; ordered pair output-valid','storage_mapping':'unchanged flop arrays, no SRAM macro and no changed read latency','FIFO_data_bits':16688,'native_output_FF_bits':1044,'native_pointer_count_FF_bits':26,'added_input_FF_bits':1045,'total_sequential_bits':18803,'PIN_CYCLES':{'a_v':1,'a_d':1,'b_v':1,'b_d':1},'host_receive_latency_delta_cycles':1,'queue_depth_change':0,'credit_or_ready_RTT_change':'not applicable: no such ports','outline_um':[W,H],'estimated_stdcell_area_um2':13300,'estimated_fill':13300/(W*H),'usable_row_fill_after_4p32um_margin':13300/((W-8.64)*(H-8.64)),'estimated_cells':100000,'estimate_status':'pre-synthesis sizing; actual cells/area still required','max_manhattan_um':W+H,'reach_limit_um':405,'pin_density_per_um':{'W':523/(H-8.64),'N':522/(W-8.64),'E':1044/(H-8.64)},'pin_layers':{'W':['M4','M6'],'N':['M5','M7'],'E':['M4','M6']},'clock_period_ps':833,'TT_setup_FF_hold':'shared tool policy; no overrides','unsigned_area_reason':'compact square:198.72um includes4.32um margin; estimated usable-row fill0.368 at target0.40','throughput':'native accepts one half per input per cycle, emits one paired word per cycle when both queued; added input stage preserves sustained rate'}
json.dump(model,open(out/'model.json','w'),indent=1)
json.dump({'private_only':True,'production_plan_changed':False,'new_hard_core_designs':1,'signed_core_credit_now':0,'parent':'unsigned kv3_hub_Wi host logic, later split HB/HT','existing_21_HR_core_modules_or_outlines_changed':False,'interface_impact':'new child boundary2091pins; both half streams+1cycle; output sequence+1cycle','regenerate':['native_parent RF source profile','strict bind and sub_core_leaf mapping','new core pin/clock/reset placement in actual parent','all affected parent kits','compiler/token ingress schedule'],'production_count_rule':'no credit until SIGNED current-tag view and approved plan event','reset_contract':'new module needs explicit private16-edge qualification entry before adoption'},open(out/'count_impact.json','w'),indent=1)
print(json.dumps({'ports':len(ports),'physical_pins':len(pins),'flops':18803,'outline':[W,H],'PIN_CYCLES':1}))
