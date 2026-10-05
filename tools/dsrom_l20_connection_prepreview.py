#!/usr/bin/env python3
"""Source-only L20 connection, service-band sizing and visibility bench prepreview."""
import argparse,hashlib,json,math,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REAL='4e38326d6f361bc85e660f48c59c355e2bb95274'
PRIOR='1fb01b08d2bf08f9458928595d94f492ac8aab4a'
PINS={}
def raw(rev,path):
 b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
 PINS[rev+':'+path]={'commit':rev,'path':path,'sha256':hashlib.sha256(b).hexdigest()}
 return b

def record(rev,path):return json.loads(raw(rev,path))
def emit(p,b):
 if p.exists() and p.read_bytes()!=b:raise SystemExit('Immutable output differs: '+str(p))
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def encoded(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()

def visibility_bench(env):
 # Actual legal W path through both immutable muxes, arbiter, backend. The
 # observed completion is not renamed or replaced by a synthetic visible ACK.
 lines=['`timescale 1ns/1ps','// PREPARED ONLY; no compilation or simulation authorized.',
 'module tb_l20_actual_backend_visibility;',
 'localparam NPC=32, AW=30, HAW=30, TAGW=16, LENW=4, BEATW=4, DW=256;',
 'reg clk=0,rst_n=0; always #0.5 clk=~clk;',
 "reg [3:0] w_v=0; wire [3:0] w_rdy,w_wr_done; localparam [255:0] DATA={32{8'hA5}};",
 'integer pc; longint observed_ps,column_ps,earliest_visible_ps;']
 def inst(path,name,params,mapping):
  pairs=[]
  for d,w,n in env['ports'](path):
   if n in mapping:v=mapping[n]
   elif d=='input':v="'0"
   else:
    v=name+'_'+n;lines.append('wire '+w+' '+v+';')
   pairs.append('.'+n+'('+v+')')
  lines.append(Path(path).stem+' #('+params+') '+name+'('+','.join(pairs)+');')
 for d,w,n in env['ports'](env['INNER']):
  if n.startswith(('m_','s_')):lines.append('wire '+w+' '+n+';')
 mapping={n:n for d,w,n in env['ports'](env['OUTER']) if n.startswith(('m_','s_'))}
 mapping.update(clk='clk',rst_n='rst_n',w_v='w_v',w_rdy='w_rdy',w_wr_done='w_wr_done',w_we="4'b1000",w_addr="{30'd311,90'd0}",w_len="16'h1111",w_tag="64'd0",w_wdata="{DATA,768'd0}",w_wstrb="{32'hffffffff,96'd0}",w_srdy="4'hf",c_srdy="4'hf",p_srdy="4'hf")
 inst(env['OUTER'],'mux','.HAW(30),.TAGW(16)',mapping)
 # Only stack3 carries a request. Inactive stacks have no outstanding jobs.
 lines.append("assign m_rdy[2:0]=0;assign m_wr_done[2:0]=0;assign s_v[2:0]=0;assign s_tag[47:0]=0;assign s_beat[11:0]=0;assign s_data[767:0]=0;")
 mapping={'clk':'clk','rst_n':'rst_n','b_rsp_rdy':"'1"}
 for n,w in [('v',1),('rdy',1),('addr',30),('len',4),('tag',16),('we',1),('wdata',256),('wstrb',32),('wr_done',1)]:mapping['k_'+n]=f'm_{n}[{3*w}+:{w}]'
 for kn,sn,w in [('rsp_v','v',1),('rsp_rdy','rdy',1),('rsp_tag','tag',16),('rsp_beat','beat',4),('rsp_data','data',256)]:mapping['k_'+kn]=f's_{sn}[{3*w}+:{w}]'
 for d,w,n in env['ports'](env['KARB']):
  if n.startswith(('h_','r_')):lines.append('wire '+w+' '+n+';');mapping[n]=n
 inst(env['KARB'],'arb','.NPC(32),.AW(30),.TAGW(16),.LENW(4),.BEATW(4),.DW(256),.PIPE_OUT(0),.PIPE_RSP(0)',mapping)
 mapping={'clk':'clk','rst_n':'rst_n','wr_done':'h_wr_done'}
 for n in ['v','rdy','addr','len','tag','we','wdata','wstrb']:mapping['req_'+n]='h_'+n
 for n in ['v','rdy','tag','beat','data']:mapping['rsp_'+n]='r_'+n
 inst(env['HBM'],'backend','.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),.DW(256),.MEM_WORDS(2048),.MEM_MODE(0),.QD(64),.RQD(32),.REFPB(3),.CLK_PS(1000)',mapping)
 lines += ['initial begin for(integer z=0;z<2048;z=z+1) backend.mem[z]=0;',
 ' pc=((311>>2)^(311>>7)^(311>>12))&31;',
 ' repeat(4) @(negedge clk);rst_n=1; @(negedge clk);w_v=8;',
 ' do @(posedge clk); while(!w_rdy[3]); @(negedge clk);w_v=0;',
 ' end',
 'always @(negedge clk) if(rst_n && w_wr_done[3]) begin',
 ' column_ps=backend.h_tcol[pc];observed_ps=(backend.cyc-1)*1000;earliest_visible_ps=column_ps+backend.CWL_PS+backend.BURST_PS;',
 ' if(backend.mem[311]!==DATA || backend.st_wr[pc]!=1 || observed_ps<column_ps || observed_ps>=earliest_visible_ps) $fatal(1,"actual backend early completion witness mismatch");',
 ' $display("NEGATIVE_WITNESS actual W backing update and WRdone at %0dps, column %0dps, earliest burst visibility %0dps; NOT_VISIBLE_ACK",observed_ps,column_ps,earliest_visible_ps);$finish;',
 'end',
 'initial begin repeat(3000) @(posedge clk);$fatal(1,"bounded actual backend witness timeout");end',
 'endmodule']
 return '\n'.join(lines)+'\n'


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--prepare',type=Path,required=True);a=ap.parse_args()
 source=raw(PRIOR,'tools/dsrom_l20_raw_producer_binding.py')
 env={'__name__':'pinned_preparation_only','__file__':str(ROOT/'tools/dsrom_l20_raw_producer_binding.py')}
 exec(compile(source,'pinned_preparation_only','exec'),env)
 prev=record(PRIOR,'results/uarch/dsrom_l20_raw_producer_binding_20261002/model.json')
 orig=record('e474925e4b8e5f07f41001e6efc40909fdc0a48e','results/uarch/dsrom_l20_mandatory_service_fixture_20261002/model.json')
 old=record('117ae7d5d25fda1084402c456340f2861eb32d1f','results/uarch/dsrom_attention_controller_l20_composition_20261001/model.json')
 fp=record(REAL,'results/floorplan/v41_pack_refit_w18_e8p5.json')
 manifest=raw(REAL,'tools/w17_current_fastpp_l20_sources.txt')
 files=[s.strip() for s in manifest.decode().splitlines() if s.strip()];assert len(files)==125
 census=[]
 for path in files:raw(REAL,path);census.append(PINS[REAL+':'+path])
 program=raw(REAL,'results/rtl/hdc_v41x_fullshape_l20_program.hex');assert len(program.decode().splitlines())==144
 quant=env['QUANT'];qe='rtl/hdc/v41/ot_hdc_v41_qe.sv';core='rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv';tile='rtl/chip/ckvsel/ot_chip_v41x_tile.sv';die='rtl/chip/ckvsel/ot_chip_v41x_die.sv';service=env['SERVICE']
 copies=env['COPIES']+[qe,core,tile,die,'rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv']
 blobs={p:raw(REAL,p) for p in copies}
 tb=visibility_bench(env)
 payload=orig['finite_state']['payload_bits']
 fields=['selected_collector_payload','IDs_table','owned_rank_ID_list','CKV_DMA_slots_payload','CKV_fetch_output_register','selected_merger_beat_buffers','selected_merger_input_registers','direct_quantizer_packed_own_row_buffer']
 payload_bits=sum(payload[n] for n in fields)
 mux=old['combinational_budget'];mux_fields=['collector_four_read_mux_bit_equivalents','collector_five_write_candidates_bit_equivalents','fetch_four_stack_64slot_request_mux_bit_equivalents','selectedID_five_read_mux_bit_equivalents','selected_WINDOW_beat_mux_bits']
 mux_bits=sum(mux[n] for n in mux_fields)
 placed=payload_bits*.2916/.5/1e6+mux_bits*.2/.5/1e6+prev['dedicated_slot_audit']['mandatory_service_placed_candidate_mm2']
 band_screens=[]
 for region in fp['soft_regions']:
  if region[1]!='HBM_SERVICE':continue
  fit=next(x for x in fp['area']['soft_region_fit'] if x['region']==region[0])
  gross=region[4]*region[5]/1e6
  horizontal=sum(math.floor(region[5]/pitch*.5+1e-9) for pitch in [.036,.048])
  band_screens.append(dict(region=region,gross_mm2=gross,retained_available_mm2=fit['available_mm2'],retained_required_mm2=fit['required_mm2'],
   service_listed_candidate_mm2=placed,service_area_deficit_mm2=placed-fit['available_mm2'],
   required_length_at_source216um_band_height_um=placed*1e6/region[5],source_band_length_um=region[4],
   M2_M4_tracks_over216um=horizontal,collector_read_boundary_tracks_minimum=9229,collector_overflow_tracks=9229-horizontal,collector_five_input_wires=11680,collector_five_input_overflow_tracks=11680-horizontal,
   result='FAIL_MONOLITHIC_LISTED_FF_AND_MUX_SERVICE_IN_THIS_BAND',
   qualification='Analytical conservative FF/mux-equivalent screen. Macro/banked redesign may change cost but needs its own abstract, exact5write/4read schedule and ports; no area/timing transfer.'))
 # Exact proposed ports, absent on retained sources. GID/block derive from the
 # same registered QE address; no decoder/reencoder can fill missing ports.
 ports=[('ckv4_v',1),('ckv4_codes',128),('ckv4_scales',16),('ckv4_gid',21),('ckv4_block',4),('ckv4_user',10),('ckv4_layer',6),('ckv4_epoch',16),('ckv4_fault',1)]
 assert sum(w for n,w in ports)==203
 edges=[]
 for src,dst,stage,note in [(quant,qe,'S6 output -> QE register','code128/scale16/fault1 plus alias existing fq_vo; same preedge as widen(fq_y)'),(qe,core,'QE output register -> combinational core','gid=registered w_addr>>9, block=w_addr[8:5]; require low5bits0, exact obase+wb_i*32'),(core,tile,'combinational forwarding','only CKV_SEL and qe_mode3; mode1 kvb sideband untouched'),(tile,die,'combinational forwarding','dedicated CKV_SELECTED variant; default opt-in off'),(die,service,'service captures next edge','reserve one2304bit row before PC38 issue; exact16beat mask; all9 visible sectors required before publication')]:
  edges.append(dict(source=src,consumer=dst,stage=stage,ports=[dict(name=n,width=w) for n,w in ports],note=note,
    exists_in_retained_source=False,preview_only=True))
 state_ports={p:{'ports':env['ports'](p),'sha256':PINS[REAL+':'+p]['sha256']} for p in [quant,qe,service,env['INNER'],env['OUTER'],env['KARB'],env['HBM']]}
 blockers=[
 dict(id='PACKED_PRODUCER_PORTS',files=[quant,qe,core,tile,die,service],missing='The exact203bit mode3 sideband is absent on allfive edges; no direct packed producer can currently connect.',gate='Source prepreview approves S3scale/S5code serialization, S6 alignment and sameQEwrite address; future isolated direct-port exactness gate.'),
 dict(id='FINITE_SCALE_DOMAIN',files=[quant],missing='Retained finite QDQ4E inputs can round past E4M3 max448; nonfinite fault does not enforce amax<=2784.',gate='Source-backed PC38 range bound or explicit contract resolution; no silent clamp/reencoder.'),
 dict(id='ACCEPTED_INTENT_IDENTITY',files=[core,die,service],missing='Current source has no generation16/user10/layer6 CKV producer session ports. These are prospective fields, not blindly inherited characterization dependencies.',gate='Dedicated single-user/layer session latch before PC38; immutable through quantizer outputs and accepted intents; epoch reuse only after backend/peer/attention physical drain. Coordinate fence ownership with Peirce.'),
 dict(id='WRITABLE_C_AND_VISIBLE_ACK',files=[env['INNER'],env['OUTER'],service,env['HBM']],missing='OuterCwrite is rejected; innerCwrite strips WE/data/strb and ACK; writer drops wr_act after9grants; actual backend commits and wr_done at tcol rather than tcol+7274ps.',gate='Exact opt-in writable C ownership and delayed held visibleACK, nine unique sectors; bench baseline defects plus corrected regression reviewed before adoption.'),
 dict(id='JOINT_READY_RETIREMENT',files=[die,service],missing='WINDOW128 READY is not joined to512selected/ownpublication; collector npresent clear can be overwritten, selection lacks complete old-epoch drain guard.',gate='Matching epoch/GID all640 readiness, priority reset/npresent, QKthenPV result completion+DRAIN+MEidle+VMquiet+accepted-intent/peer retirement; QE_done/prodEMPTY is insufficient.'),
 dict(id='FINITE_PEER_PROVIDER',files=[die,service],missing='Three RX lanes lack ready/epoch and retainedhost peerqueues are unbounded.',gate='512reserved seats and3TXskids; all3copy reservations before acceptance, bounded providers and actual reversecredit until destination accept.'),
 dict(id='DEDICATED_SERVICE_SLOT',files=['results/floorplan/v41_pack_refit_w18_e8p5.json'],missing='No CKV slot/collector abstract in retained inventory; every216um serviceband fails full listed monolithic service area and9229track read boundary.',gate='Review dedicated hub placement/ownership or separately priced banked distribution; source-equivalent4096row die, OBS, origins, reservations and current32-PC connectivity required.'),
 dict(id='PHYSICAL_ROUTE_AND_TOKEN_BOUND',files=[core,tile,die],missing='No measured203bit producer,9229collector,16966mergedKV,2351peer and reversecredit endpoints/route latency at1.2GHz with0.9GHz SU CDC.',gate='Exact per-layer/co-resident track budget and realroute endpoints/CDC/clock latencies. Compose service guarantee and actual acceptance schedule into token graph; no perfect service or9537load multiplication.')]
 model=dict(schema='opentallas.dsrom.L20-source-connection-prepreview.v1',prior=PRIOR,source=REAL,
  verdict='PREPARATION_COMPLETE_CONNECTED_SOURCE_AND_PHYSICAL_BUILD_NOT_READY',engine_RTL_build_ready=False,launch_allowed=False,
  source_manifest=census,program={'instructions':144,'pin':PINS[REAL+':results/rtl/hdc_v41x_fullshape_l20_program.hex']},
  original_FAILURE=prev['original_failure'],four_targets=prev['four_targets'],
  direct_mode3_connection_edges=edges,
  identity_and_acceptance={'session_bits':32,'gid_bits':21,'block_bits':4,'identity_is_prospective':'user/layer/epoch have no current CKV output source; must be latched opt-in session identity, never fabricated per output or reused on QE_done',
   'acceptance':'Whole2304bit destination reservation before PC38; no ready inside eight-stage quantizer.16consecutive outputs; capture only accepted matching block/GID, one per maskbit; faults stay in fence ledger.',
   'timing_edges':{'first_input':0,'first_S6_output':7,'first_QE_registered_sideband':8,'first_service_capture':9,'last_input':15,'last_service_capture':24},
   'common_cut':'Prospective controller3stages/+2cycles remains priced separately; zero new producer latency only if matching the retained QE register and combinational forwarding exactly.',
   'fanout':'1quantizer->1QE->1core/tile/die service perrank.32nibbles each have1capture sink; 2scale bytes ultimately each fan to16native deq elements.3outgoing peer copies need finite independent skids; no9537serial factor.'},
  full_service_area={'payload_fields':{n:payload[n] for n in fields},'payload_bits':payload_bits,'payload_FF_cell_um2':payload_bits*.2916,
    'mux_fields':{n:mux[n] for n in mux_fields},'mux_bit_equivalents':mux_bits,'mux_cell_um2':mux_bits*.2,
    'mandatory_added_state_bits':9161,'mandatory_service_placed_mm2':prev['dedicated_slot_audit']['mandatory_service_placed_candidate_mm2'],
    'full_listed_service_placed_mm2_per_rank':placed,'TP4_service_placed_mm2':4*placed,'replicas':4,'logic_utilization_assumption':.5,
    'scope':'Listed actual service memories priced asFFs and naive muxes plus mandatory state/backend/mux repairs. Not mapped/hardened area. Arithmetic/indexer/attention and physical clocks/reset/PG excluded from service subtotal; priorfull41.536585mm2 retains those listed attentioncosts separately. No BFpair spare.'},
  exact_retained_service_bands=band_screens,
  retained_hub={'source_region':next(r for r in fp['soft_regions'] if r[0]=='HUB_ATTENTION'),'actual_CKV_slot':False,'full_goal_source_screen':prev['dedicated_slot_audit'],'cannot_allocate':'Placing a prospective bbox inside this shared envelope does not reserve space from attention/index/co-residents.'},
  port_service_budget={'producer_Bpc':18,'producer_bits_per_cycle':203,'row_write_Bpc':32,'row_write_sectors':9,'collector_peak_Bpc':1152,'collector_five_write_candidate_bits_per_cycle':11680,'collector_five_write_payload_Bpc':1440,'collector_sustained_candidate_Bpc':576,'merged_KV_Bpc':2120,'peer_payload_bits':2351,'three_copy_payload_bits':7053,'HBM_return_guarantee_candidate_Bpc_per_stack':32,'HBM_stacks':4,'MACs_in_service':0,'communication_intensity':'288rowbytes producer +288ownwrite bytes; selected512*288 collectorbytes, replaytwice; compute is in actualattention32768MAC/cycle, not this service.'},
  token_composition={'producer_capture_cycles_inclusive':25,'source_QK_post_READY_cycles':2894,'source_PV_post_READY_cycles':3374,'common_cut_QK_PV_added_cycles':4,
   'conditional_finite_service':old['finite_service_candidate'],'producer_clock':'Streaming1.2GHz target, currentbench1ns diagnostics; SU0.9GHz and physicalCDC not zero-assumed.',
   'conditional_only':'Prior serialcandidate3166517 cycles is not a whole-token bound. Fullpath sourcecorrectness is currently absent. Service routes/providers/oldaccepted intent drains and SU/index schedule must be bound before certification.'},
  prepared_bench={'baseline_Cwriter_fixture':'tests/fixtures/dsrom_l20_actual_write_20261002/tb_l20_actual_write.sv','supplemental_actual_backend_visibility':'tb_l20_actual_backend_visibility.sv','sha256':hashlib.sha256(tb.encode()).hexdigest(),
   'intent':'Prepare actual legalW path through unchangedbothmuxes/Karb/backend to observe actualWRdone/backingupdate beforecolumn+7274ps. This isolates backend visibleACK flaw that blockedCpath cannot reach.',
   'provider':'Actual FR-FCFS/REFPB3 RTL, MEM_MODE0, one synthetic32B sector311; no substitute completion or backend.',
   'bounds':{'stacks':1,'NPC':32,'QD':64,'RQD':32,'MEM_WORDS':2048,'backing_bytes':65536,'CLK_PS':1000,'watchdog_cycles':3000,'future_wall_timeout_seconds':120,'future_memory_cap_GiB':1},
   'source_tick_observation':'Read at negedge after NBA; backend now=(cyc-1)*CLK_PS corresponds to the column/commit edge; h_tcol from actual schedule, never synthetic.',
   'execution':'SOURCE_PREPARED_ONLY_NO_COMPILE_OR_SIMULATION','correctness_admission':False,
   'expected_baseline':'Negative witness actual backingupdate+WRdone atcolumn event, earlier than burst visibility; not a correctedPASS.',
   'next_fix_regression':'Use reviewedopt-in Cwriter chain with sameactualbackend corrected visibleprovider; stallheldACK,9unique sectors, publicationonlyafterlastvisible, resetnointentloss, jointREADY and retirement gates.'},
  source_port_prepreview=state_ports,remaining_exact_blockers=blockers,operations={'engine_RTL_edits':0,'RTL_compiles':0,'simulations':0,'PnR':0,'checkpoint_payload_reads':0,'live_job_operations':0},pins=PINS)
 # Bound file/module closure without elaborating RTL.
 definitions=set();references=set()
 import re
 for data in blobs.values():
  clean=re.sub(r'//[^\n]*|/\*.*?\*/','',data.decode(),flags=re.S)
  definitions.update(re.findall(r'\bmodule\s+(ot_\w+)',clean))
  references.update(re.findall(r'^\s*(ot_\w+)\s*(?:#\s*\(|\w+\s*\()',clean,re.M))
 # QE/core/tile/die previews have fullengine dependencies; they are NOT compile
 # inputs for either bench. Verify closure only the14 immutable benchfiles.
 bench_defs=set();bench_refs=set()
 for path in env['COPIES']:
  clean=re.sub(r'//[^\n]*|/\*.*?\*/','',blobs[path].decode(),flags=re.S)
  bench_defs.update(re.findall(r'\bmodule\s+(ot_\w+)',clean));bench_refs.update(re.findall(r'^\s*(ot_\w+)\s*(?:#\s*\(|\w+\s*\()',clean,re.M))
 assert bench_refs<=bench_defs,bench_refs-bench_defs
 model['prepared_bench']['static_module_dependency_closure']={'verdict':'PASS_SOURCE_NAMES_ONLY_NOT_ELABORATION','definitions':sorted(bench_defs),'references':sorted(bench_refs),'full_QE_in_compile_list':False}
 model['prepared_bench']['compile_command_not_executed']=['iverilog','-g2012','-s','tb_l20_actual_backend_visibility','-o','/tmp/l20_actual_backend_visibility','tb_l20_actual_backend_visibility.sv']+['source/'+p for p in env['COPIES']]
 model['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 emit(a.output,encoded(model))
 for p,b in blobs.items():emit(a.prepare/'source'/p,b)
 emit(a.prepare/'original_l20_sources.txt',manifest);emit(a.prepare/'original_l20_program.hex',program)
 emit(a.prepare/'tb_l20_actual_backend_visibility.sv',tb.encode())
 emit(a.prepare/'source_manifest.json',encoded({'copies':[PINS[REAL+':'+p] for p in copies],'model_sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),'bench_sha256':model['prepared_bench']['sha256'],'full125_source_census':True,'RTL_executed':False}))
 print(json.dumps({'status':model['verdict'],'full125pins':len(census),'copied_source_files':len(copies),'full_service_listed_mm2_per_rank':placed,'monolithic_serviceband_fit':False,'engine_RTL_build_ready':False}))
if __name__=='__main__':main()
