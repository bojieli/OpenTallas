#!/usr/bin/env python3
"""Additive repair of QE WQR input binding and source-derived SU edge; never compile."""
from pathlib import Path
import json,re,hashlib,subprocess,importlib.util
ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
CORE='rtl/test/w17_window_core_cancel_prepared_r8/fastpp_core_cancel.sv'
OUT=ROOT/'rtl/test/w17_window_core_cancel_join_r7'
REC=ROOT/'results/uarch/w17_window_core_cancel_join_preparation_r7_20261002'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blob(p):return subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT)
def generate():
 core=(ROOT/CORE).read_text();a=core.index('module ot_hdc_core_v41x_cancel_fastpp #(');b=core.index('\n);',a)+3;header=core[a:b]
 overrides={'OPT_CORE_PRODUCER_CANCEL':'1','FULL_SHAPE':'1','KV_HBM':'1','X_SU':'1','SUN':'256','SUM':'64','X_ROM':'0','NSLOT':'1','MP':'1'}
 params=[]
 for name,expr in re.findall(r'^\s*parameter integer (\w+)\s*=\s*([^\n]+)',header,re.M):
  expr=expr.split('//',1)[0].rstrip().rstrip(',');params.append('localparam integer '+name+' = '+overrides.get(name,expr)+';')
 from w17_window_core_cancel_source_ports_repair import parse_ports
 ports=parse_ports(header)
 assert len(ports)==252
 decl=[];connections=[]
 for direction,width,name in ports:
  decl.append(('logic ' if direction=='input' else 'wire ')+(width or '')+' core_'+name+('=0;' if direction=='input' else ';'))
  connections.append('.'+name+'(core_'+name+')')
 spec=importlib.util.spec_from_file_location('isa',ROOT/'tools/hdc_isa_v41.py');isa=importlib.util.module_from_spec(spec);spec.loader.exec_module(isa)
 q=isa.encode(full_shape=True,unit=3,qe_mode=1,qe_xbase=54720,qe_nb=16,qe_obase=55232)
 s=isa.encode(full_shape=True,unit=2,wait=4,su_nout=1,su_nin=512,a_base=55232,a_si=1,dst=3,o_base=0,o_d=16)
 e=isa.encode(full_shape=True,unit=0,wait=31)
 original=(ROOT/'rtl/test/w17_window_recovery_gate/tb.sv').read_text()
 # Reuse exact pinned connected transport, observer, competitor conservation.
 transport=original[:original.index('task automatic tick();')]
 transport=transport.replace('.rec_commit(commit)', '.rec_commit(core_rec_commit_qualified)')
 replacements={'assign src_blk_v = block_offer;':'assign src_blk_v = core_win_blk_v && !guard_bad;',
 'assign src_blk_row = \'0;':'assign src_blk_row = core_win_blk_row;',
 'assign src_blk_idx = \'0;':'assign src_blk_idx = core_win_blk_idx;',
 'assign src_blk_codes = \'0;':'assign src_blk_codes = core_win_blk_codes;',
 "assign src_blk_scale = 8'd127;":'assign src_blk_scale = core_win_blk_scale;',
 'assign src_packed_re = fault_pulse;':"assign src_packed_re = 0;"}
 for old,new in replacements.items():
  assert transport.count(old)==1;transport=transport.replace(old,new)
 # Connected owner fault enters through explicit recovery request; no fabricated malformed read.
 # Source rec_request already consumes recover in the reviewed transport.
 addition='\n'+'\n'.join(params+decl)+'\n'
 addition+='ot_hdc_core_v41x_cancel_fastpp #('+','.join('.'+n+'('+n+')' for n in overrides)+') core (\n'+',\n'.join(connections)+');\n'
 addition+='''
wire guard_bad;
ot_chip_v41x_window_block_guard #(.AW(30),.POS_W(21)) guard (
 .step_pos(core_pos), .blk_abs_row(core_win_blk_row), .blk_kvt_row(core_win_blk_kvt_row),
 .blk_idx(core_win_blk_idx), .kvt_base(core_win_blk_kvt_base), .first_elem(core_win_blk_first_elem),
 .hbm_slot(), .expected_first(), .bad(guard_bad));
// Only synthetic finite fixture inputs. No manually injected captures/blocks.
always_comb begin
 core_coll_busy=0;core_coll_fault=0;core_rope_pf_fault=0;
 core_rope_pf_rdy=0;core_rope_pf_done=0;core_rom_ffault=0;
 core_clk=clk;core_rst_n=rst_n;core_win_blk_ready=src_blk_ready && !guard_bad;
 core_rec_request=recover;core_rec_token=token;
 core_rec_fault_inject=fault_pulse || src_fault || (core_win_blk_v && guard_bad);
 core_rec_provider_ready=restart_ready;
 core_rec_rearm_request=commit;
 // External causal certificates default false, independently supplied controls below.
end
integer qe_accepts=0, su_accepts=0, terminals=0, vm_stores=0, captures=0, blocks=0;
integer prefix=0, fault_cycle=-1, stopped_pc=-1, suppress_samples=0;
integer init_word, vlane;
integer local_edge=-1, start_edge=-1;
reg [31:0] vm_shadow[0:511]; // synchronous masked fixture sink; never freeze accepted writes
reg [511:0] vm_written=0;
integer sink_words=0, sink_frames_frozen=0;
wire [AW:0] sink_last_wide={1'b0,core_ww_q_addr}+(AW+1)'(31);
string cut;
logic checking=0, injected=0;
always @(posedge clk) if(rst_n) begin
 local_edge++;
 if(core_start) start_edge=local_edge;
 if(core_prog_re) begin
  case(core_prog_addr)
   20: core_prog_q<=2048'hQWORD;
   21: core_prog_q<=2048'hSWORD;
   default: core_prog_q<=2048'hEWORD;
  endcase
 end
 if(core_wqr_re) begin
  if(core_wqr_addr < 54720 || core_wqr_addr+31 >= 55232)
   $fatal(1,"real QE input full-address aperture");
  core_wqr_q <= {32{32'h3f800000}};
  if(cut=="POISON" && core_wqr_addr==54720+8*32) core_wqr_q[31:0]<=32'h7fc00000;
 end
 if(core.g_cancel.u_impl.qe_go_e && core.g_cancel.u_impl.qe_ready_e) begin
  if(local_edge-start_edge!=7) $fatal(1,"declared actual QE admission calendar mismatch");
  qe_accepts++;
 end
 if(core.g_cancel.u_impl.rec_su_go && core.g_cancel.u_impl.su_ready) begin
  if(local_edge-start_edge!=43) $fatal(1,"declared actual SU admission calendar mismatch");
  su_accepts++;
 end
 if(core.g_cancel.u_impl.rec_terminal) begin
  if(local_edge-start_edge!=24+terminals) $fatal(1,"declared actual QE terminal calendar mismatch");
  terminals++;
 end
 if(core.g_cancel.u_impl.rec_cap_v && core.g_cancel.u_impl.win_cap_ready) captures++;
 if(core_ww_q_we) begin
  if(sink_last_wide[AW] || core_ww_q_addr < AW'(55232) || sink_last_wide >= (AW+1)'(55744) ||
     !core.g_cancel.u_impl.rec_terminal || core_ww_q_mask != 32'hffffffff ||
     core_ww_q_addr != 55232+32*vm_stores ||
     (!core.g_cancel.u_impl.win_capture_fault && core_ww_q_data != {32{32'h3f800000}}))
   $fatal(1,"accepted QE suffix VM store lost or changed");
  for(vlane=0;vlane<32;vlane++) if(core_ww_q_mask[vlane]) begin
   if(vm_written[core_ww_q_addr-55232+vlane]) $fatal(1,"duplicate VM suffix word ownership");
   if(1) begin // VM_SINK_COMMIT: accepted raw stores continue during freeze
    vm_shadow[core_ww_q_addr-55232+vlane] <= core_ww_q_data[32*vlane +: 32];
    vm_written[core_ww_q_addr-55232+vlane] <= 1'b1;
    sink_words++;
   end
  end
  if(core_rec_frozen_out) sink_frames_frozen++;
  vm_stores++;
 end
 if(core_win_blk_v && core_win_blk_ready) begin
  if(guard_bad) $fatal(1,"actual producer block identity");
  blocks++;
 end
 if(checking && (core.g_cancel.u_impl.qe_go_e || core.g_cancel.u_impl.rec_su_go ||
                 core.g_cancel.u_impl.rec_cap_v || core_win_blk_v))
  $fatal(1,"admission freeze violated");
 if(checking && core.g_cancel.u_impl.pc != stopped_pc)
  $fatal(1,"fault edge advanced PC");
 if(core.g_cancel.u_impl.win_scalar_suppress && !core.g_cancel.u_impl.su_idle) begin
  suppress_samples++;
  if(|core_xs_kv_we || |core_kv_we) $fatal(1,"accepted scalar suppression lost");
 end
 if(core_rec_commit_qualified && (!core_rec_visibility_certified ||
    !core_rec_delivery_certified || !core_rec_provenance_valid || !core_rec_local_ack ||
    !restart_ready || !core.g_cancel.u_impl.su_idle))
  $fatal(1,"local ACK mistaken for selected owner or causal retirement");
 if(cycles>4096 && cut!="WC" && cut!="WS" && cut!="SU_SUFFIX")
  $fatal(1,"actual source suffix bounded timeout");
end
task automatic tick(); @(posedge clk); #0.001; endtask
task automatic inject();
 recover=1;fault_pulse=1;stopped_pc=core.g_cancel.u_impl.pc;fault_cycle=cycles;
 tick();checking=1;injected=1;@(negedge clk);fault_pulse=0;
endtask
initial begin
 if(!$value$plusargs("CUT=%s",cut)) cut="PREFIX";
 if(!$value$plusargs("PREFIX=%d",prefix)) prefix=8;
 if(prefix<0 || prefix>16) $fatal(1,"unreviewed prefix");
 scenario="actual_core";control="none";
 for(init_word=0;init_word<512;init_word++) vm_shadow[init_word]=32'hdeadbeef;
 repeat(3) tick();@(negedge clk);rst_n=1;
 for(init_word=262144;init_word<264320;init_word++) back.g_recovery.u_impl.mem[init_word]=0;
 tick();@(negedge clk);core_entry=20;core_pos=0;core_start=1;
 tick();@(negedge clk);core_start=0;
 if(cut=="ISSUE") begin
  wait(core.g_cancel.u_impl.st==6 && core.g_cancel.u_impl.d_unit==3);
  @(negedge clk);inject();
 end else if(cut=="GO") begin
  wait(core.g_cancel.u_impl.qe_go);@(negedge clk);inject();
 end else if(cut=="PREFIX") begin
  wait(qe_accepts==1);
  if(prefix>0) wait(terminals==prefix);
  @(negedge clk);inject();
 end else if(cut=="POISON") begin
  wait(core.g_cancel.u_impl.win_capture_fault);@(negedge clk);inject();
 end else if(cut=="SU_SUFFIX") begin
  wait(su_accepts==1);@(negedge clk);inject();
 end else if(cut=="WC" || cut=="WS") begin
  if(cut=="WC") wait(src.g_recovery.u_impl.state==2);
  else wait(src.g_recovery.u_impl.state==4);
  @(negedge clk);inject();
 end else $fatal(1,"unreviewed actual-core cut");
 wait(core_rec_local_ack);tick();
 if(core.g_cancel.u_impl.rec_active || !core.g_cancel.u_impl.rec_suffix_closed ||
    !core.g_cancel.u_impl.qe_idle_e || !core.g_cancel.u_impl.win_idle)
  $fatal(1,"local ACK before actual suffix and logical EMPTY");
 if(cut=="ISSUE" || cut=="GO") begin
  if(qe_accepts!=0 || terminals!=0 || vm_stores!=0) $fatal(1,"registered go cut accepted QE");
 end else begin
  if(qe_accepts!=1 || terminals!=16 || vm_stores!=16)
   $fatal(1,"accepted QE suffix not completely drained");
  if(cut=="POISON" && captures!=8) $fatal(1,"poison suffix capture freeze violated");
  if(cut=="PREFIX" && captures!=prefix) $fatal(1,"capture prefix count changed");
 end
 if(qe_accepts==1 && (vm_written!={512{1'b1}} || sink_words!=512))
  $fatal(1,"actual accepted VM stores missing");
 if(cut=="PREFIX" && sink_frames_frozen!=16-prefix)
  $fatal(1,"accepted VM suffix commits stopped after freeze");
 for(init_word=0;init_word<512;init_word++)
  if(qe_accepts==1 && !(cut=="POISON" && init_word>=256 && init_word<288) && vm_shadow[init_word]!=32'h3f800000)
   $fatal(1,"actual masked VM suffix memory image mismatch");
 if(core_rec_provenance_fault) $fatal(1,"intended fault cut falsely classed provenance violation");
 // Test local ACK cannot certify ownership or projected-vs-causal visibility.
 @(negedge clk);commit=1;
 repeat(4) begin tick();if(core_rec_commit_qualified) $fatal(1,"causal certificates absent but rearm admitted");end
 @(negedge clk);commit=0;
 wait(restart_ready && core.g_cancel.u_impl.su_idle);tick();
 if(expected_writes!=accepted_writes || accepted_reads!=returned_reads)
  $fatal(1,"accepted owner intent lost before restart");
 if(cut=="SU_SUFFIX" && (su_accepts!=1 || suppress_samples==0))
  $fatal(1,"actual accepted SU suppression witness absent");
 if(other_grants==0) $fatal(1,"competitor ownership witness absent");
 // Certificates are intentionally never asserted: actual causal provider absent.
 $display("ACTUAL_CORE_CANCEL_PASS cut=%s prefix=%0d qe=%0d terminal=%0d vm=%0d capture=%0d blocks=%0d acceptedWR=%0d faultcycle=%0d localACKcycle=%0d suppressed=%0d sinkWords=%0d frozenFrames=%0d",cut,prefix,qe_accepts,terminals,vm_stores,captures,blocks,accepted_writes,fault_cycle,cycles,suppress_samples,sink_words,sink_frames_frozen);
 $finish;
end
endmodule
'''.replace('QWORD',f'{q:0512x}').replace('SWORD',f'{s:0512x}').replace('EWORD',f'{e:0512x}')
 # Declarations precede connections to avoid implicit-net mistakes.
 text=transport.replace('assign src_clk = clk;',addition[:addition.index('integer qe_accepts')].split('always_comb begin')[0]+'\nassign src_clk = clk;',1)
 # Keep combinational mapping, monitors and actual-stimulus body after transport.
 text += addition[addition.index('// Only synthetic finite fixture inputs.'):]
 # drop second declarations/instance occurrence? Prefix is before stimulus comment, so no duplication.
 # Runtime-only extraction: retain original selected code, omit inactive engines.
 ea=core.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
 enabled=core[ea:];prefix=enabled[:enabled.index('    // -- units ')]
 su_start=enabled.index('    // the stream unit.')
 su_end=enabled.index('    // X_ROM: a LINQ op',su_start)
 su=enabled[su_start:su_end]
 qe_start=enabled.index('    ot_hdc_v41_qe #')
 qe_end=enabled.index('    // the XU:',qe_start)
 qe=enabled[qe_start:qe_end]
 fault=enabled[enabled.rindex('    assign unit_busy'):]
 wiring='''
    // Fixture cone: absent engine classes are prohibited, never qualified providers.
    assign me_ready=1;assign me_idle=1;assign me_fault=0;
    assign xu_ready=1;assign xu_idle=1;assign xu_fault=0;
    assign he_ready=1;assign he_idle=1;assign he_fault=0;
    assign am_idx_v=0;assign am_val_v=0;assign am_any_v=0;assign me_progress=0;
    assign xu_sel_first=0;
    localparam [1:0] MC_W=0,MC_A=1,MC_I=2;
    wire [1:0] me_cls=!me_wsrc?MC_W:((me_wbase>=cfg_ik_base)?MC_I:MC_A);
    wire qe_rom=(X_ROM!=0)&&qe_mode==0;
    wire qe_go_e=rec_qe_go&&!qe_rom;
    wire qe_ready_e,qe_idle_e;
    assign qe_ready=qe_ready_e;assign qe_idle=qe_idle_e;
    wire rom_fault_w=0;
    initial if(X_ROM!=0 || X_SU!=1 || SUN!=256 || SUM!=64 || MP!=1 || BL!=16 || IL!=8)
        $fatal(1,"actual selected cone geometry");
    always @(posedge clk) if(rst_n && (me_go||xu_go||he_go||coll_go||rope_pf_v||rope_pf_release))
        $fatal(1,"excluded engine admitted in selected cone");
'''
 cone=core[:ea]+prefix+wiring+su+qe+fault
 OUT.mkdir(exist_ok=False);REC.mkdir(exist_ok=True)
 (OUT/'actual_fastpp_core_selected_cone.sv').write_text(cone)
 (OUT/'tb.sv').write_text(text)
 manifest_path='results/rtl/w17_connected_token_preparation_20261001/L0_cli_recovery_launch.json'
 manifest=json.loads((ROOT/manifest_path).read_text());originals=manifest['source_sha256']
 selected={}
 for path,expected in originals.items():
  if not path.endswith(('.sv','.svh','.v')) or 'ot_hdc_core_v41x.sv' in path:continue
  content=blob(path)
  if hashlib.sha256(content).hexdigest()!=expected:raise ValueError('retained source hash mismatch '+path)
  selected[path]=expected
 record={'status':'PREPARED_UNCOMPILED_REVIEW_REQUIRED','pin':PIN,'manifest':manifest_path,'manifest_sha256':sha(ROOT/manifest_path),
  'core_path':CORE,'core_sha256':sha(ROOT/CORE),'runtime_cone_path':str((OUT/'actual_fastpp_core_selected_cone.sv').relative_to(ROOT)),'runtime_cone_sha256':sha(OUT/'actual_fastpp_core_selected_cone.sv'),'extracted_regions_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in {'prefix':prefix,'actual_SU':su,'actual_QE_producer':qe,'fault':fault}.items()},'bench_sha256':sha(OUT/'tb.sv'),'generator_sha256':sha(Path(__file__)),
  'original_source_sha256':selected,'program_fields':{'20':isa.decode(q,full_shape=True),'21':isa.decode(s,full_shape=True)},
  'cases':[{'CUT':x} for x in ('ISSUE','GO','POISON','SU_SUFFIX','WC','WS')]+[{'CUT':'PREFIX','PREFIX':n} for n in range(17)],
  'compilation_scope':'Source-extracted actual fastpp sequencer/DYN/decode/descriptor logic, actual SU generate and QE/producer code unchanged after declared opt-in cancellation delta. Inactive ME/XU/HE/ROM omitted and all admission to them fatal. No whole-core claim. Actual QE BL16 IL8 NBMAX192 CHUNK8 MP1; actual SU SUN256 SUM64, all other core text unchanged. No die, no images/checkpoint payloads.',
  'VM_scope':'Existing synthetic synchronous masked VM fixture: full AW30 aperture54720..55231 read /55232..55743 write, no modulo alias; all accepted raw stores retained. Actual buffered/shared VM retirement provider remains unqualified.',
  'observer_scope':'Local suffix closure and accepted WCWS intent through selected STACK2 WINDOW/mux/KARB/idx; independent causal certificates false. Exact transport competitor ledger retained.',
  'accounting':{'provider':259,'producer_receipt':2,'core_control':8,'concrete':269,'envelope':278,'older_280_plan':'superseded, preserved; never added'},
  'predicted_relative_calendar':{'start':0,'S_ISSUE':6,'physical_QE_accept':7,'terminal_VM_samples':list(range(24,40)),'raw_idle_observed':42,'local_ACK_observed':43,'earliest_physical_SU_accept':43,'basis':'Source sequencer edges plus prior independently pinned actual QE fixed calendar; no runtime fitted value'},
  'resource_model':{'CPUs':[30,31],'aggregate_memory_bytes':4294967296,'swap_bytes':0,'aggregate_output_bytes':268435456,'single_file_bytes':268435456,'whole_seconds':180,'compile_shared_seconds':130,'runtime_shared_seconds':26,'reserve_seconds':24,'actual_joined_SU_QE_cone_compile_output_peak':'UNKNOWN before capped GO; standalone QE known 165788101B does not bound joined SU256+QE cone','no_shrink_or_helper_substitution':True},
  'future_mutants':{'physical_QE_gate':{'old':'wire rec_qe_go = qe_go && !rec_stop && !rec_rearm;','new':'wire rec_qe_go = qe_go;','case':'GO','failure':'registered go cut accepted QE'},'PC_advance':{'old':'else if (rec_stop || rec_bad_su_ready) st <= S_COLL_HALT;','new':'else if (rec_stop || rec_bad_su_ready) begin if (st == S_GO) pc <= pc + 1\'b1; st <= S_COLL_HALT; end','case':'GO','failure':'fault edge advanced PC'},'VM_frozen_store_drop':{'target':'bench','old':'if(1) begin // VM_SINK_COMMIT: accepted raw stores continue during freeze','new':'if(!core_rec_frozen_out) begin // MUTANT drops accepted frozen stores','case':'PREFIX','args':['+PREFIX=0'],'failure':'actual accepted VM stores missing'},'scalar_suppression':{'old':'assign xs_kv_we = raw_kv_we & {SUN{!win_scalar_suppress}};','new':'assign xs_kv_we = raw_kv_we;','case':'SU_SUFFIX','failure':'accepted scalar suppression lost'}},
  'physical_causal_visibility':False,'producer_qualification':False,'runtime_PASS':False,'fulltoken':False,'adoption':False}
 (REC/'model.json').write_text(json.dumps(record,indent=2)+'\n')
 return record
if __name__=='__main__':print(json.dumps({'prepared':generate()['status'],'compiler_invocations':0}))
