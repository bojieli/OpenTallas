#!/usr/bin/env python3
"""Stage the actual RAW/COPY endpoint, ROLE calendar, physical service and VM banks.

The source candidate is read from pinned repository objects. This functional
mechanism fixture does not change production source, memory allocation or dates.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PROVIDER='24de429cd'
FIXTURE='79d539a81'
ROLE='8c5f35a6f'
PREFIX='rtl/hbm_accel/loader/service_native/split/'
def read(ref,path):return subprocess.check_output(['git','show',f'{ref}:{path}'],cwd=ROOT)
def stage(out,transport_age=0):
 out.mkdir(parents=True,exist_ok=False);sources=[];pins={}
 def export(ref,path):
  data=read(ref,path);p=out/'source'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);pins[path]=dict(commit=ref,sha256=hashlib.sha256(data).hexdigest());return p
 manifest=json.loads(read(FIXTURE,'results/tok_hbm_provider_1030/timing833_source_dependencies.json'))
 for path in manifest['shared_repo_files']:sources.append(export(PROVIDER,path))
 names=list(manifest['provider_files'])+['ot_hbm_static_load_native_provider_quad.sv','ot_hbm_static_load_dated_cmd_hold.sv','ot_hbm_static_load_raw_copy_fill_route.sv','ot_hbm_static_load_window_calendar.sv']
 for name in names:sources.append(export(PROVIDER,PREFIX+name))
 role=json.loads(read(FIXTURE,'results/tok_hbm_provider_1030/selected_role_sources.json'))
 for path in role['files']:sources.append(export(ROLE,path))
 # Historical exact descriptor cohort already exercised through the native banks.
 for name in ('fixture_desc.mem','fixture_steps.mem','fixture_expected.mem'):
  data=read(FIXTURE,'results/tok_hbm_provider_1030/'+name);(out/name).write_bytes(data)
 tool=export(PROVIDER,'tools/hbm_timing_833_profile.py')
 subprocess.run([sys.executable,str(tool),'--first-pc','0','--npc','16','--json-out',str(out/'timing_profile.json'),'--boot-row-out',str(out/'timing_boot.mem')],check=True)
 bench=read(FIXTURE,'results/tok_hbm_provider_1030/tb_timing833_provider.sv').decode()
 bench=bench.replace('tb_timing833_provider','tb_raw_copy_provider')
 start=bench.index(' ot_hbm_static_load_cmd_provider_quad #')
 end=bench.index('\n ot_hgi_dma_back_static_vp4_banks_rs',start)
 bench=bench[:start]+''' wire[15:0]raw_fills;wire[15:0]raw_ready;wire[7:0]raw_fault,raw_busy,raw_full0,raw_full1,raw_bad;
 wire[2247:0]raw_dq;integer raw_seen[0:7];integer raw_total=0,mut_raw=0,mut_early=0;
 ot_hbm_static_load_native_provider_quad #(.SOURCE_QUAD(2))dut(.clk(clk),.rst_n(rst_n),.cmd_v(load_v),.cmd(cmd),.cycle(cycle),.command_fault_i(collar_fault|dispatch_fault),
 .source_fault_i((|raw_fault)|ref_fault|(|pc_fault)|(|vmks_fault)),.calendar_v_i(cal_v),.calendar_payload_i(cal_payload),
 .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),
 .vm_dq_done_i(vm_dq_done_i),.vm_fault_i(vm_fault_i),.raw_fill_v_o(raw_fills),.dated_step_o(),.admit_o(),
 .vm_dq(vm_dq),.block_ready(block_ready),.leaf_fault(leaf_fault),.busy_o(load_busy),.fault_o(load_fault),.load_done_o(load_done_o));
 for(genvar rb=0;rb<8;rb=rb+1)begin:RAW
 ot_hbm_svc_vmdel_lane_load_static #(.NPC(2),.SHPRE(1),.RPIPE(1))lane(.clk(clk),.rst_n(rst_n),.bank_id(3'(rb)),
 .begin_v_i(cal_v&&cal_payload[0]),.begin_bank_i(cal_payload[1]),.begin_epoch_i(cal_payload[17:2]),
 .start_i(cal_v&&cal_payload[18]),.start_bank_i(cal_payload[19]),.start_epoch_i(cal_payload[35:20]),.start_base_sector_i(cal_payload[51:36]),
 .fill_v_i(mut_raw!=0?2'd0:raw_fills[rb*2+:2]),.fill_bank_i(fill_bank[rb*2+:2]),.fill_slot_i(fill_slot[rb*12+:12]),.fill_epoch_i(fill_epoch[rb*32+:32]),.fill_data_i(fill_data[rb*512+:512]),
 .full0_all(raw_full0),.full1_all(raw_full1),.pcbad_all(raw_bad),.full0(raw_full0[rb]),.full1(raw_full1[rb]),.pcbad(raw_bad[rb]),
 .block_ready(raw_ready[rb*2+:2]),.busy(raw_busy[rb]),.fault(raw_fault[rb]),.load_v_i(1'b0),.load_cmd_i(62'd0),.load_dest_bank(),.load_dest_q(),.load_dq(),.load_out_v(),.dq(raw_dq[rb*281+:281]));
 end
 always @(posedge clk)if(rst_n)begin:RAW_CHECK
 integer rb,gg,ss,ww;reg[255:0]gold;
 for(rb=0;rb<8;rb=rb+1)if(raw_dq[rb*281+280])begin
 gg=raw_seen[rb]%2;ss=raw_seen[rb]/2;gold=0;
 for(ww=0;ww<8;ww=ww+1)gold[ww*32+:32]=payload(phase,rb,gg,ss,ww);
 if(phase==1||ss>=64||raw_dq[rb*281+8+:256]!==gold||raw_dq[rb*281+:8]!==8'hff)$fatal(1,"RAW_DATA phase=%0d leaf=%0d group=%0d slot=%0d actual=%h expected=%h",phase,rb,gg,ss,raw_dq[rb*281+8+:256],gold);
 raw_seen[rb]=raw_seen[rb]+1;raw_total=raw_total+1;
 end
 if(phase==1&&(|raw_fills))$fatal(1,"COPY_ONLY_LEAKED_RAW_FILL");
 end
''' +bench[end:]
 bench=bench.replace('dut.dated_step','dut.consumer.dated_step').replace('dut.admit','dut.consumer.admit').replace('dut.cmd','dut.consumer.cmd').replace('dut.move','dut.consumer.move').replace('dut.drain_at','dut.consumer.drain_at')
 # RAW begin count is two joint epochs; COPY-only epoch deliberately omits it.
 a=bench.index(' for(phase=0;phase<3;phase=phase+1)begin')
 z=bench.index(' if(mut_epoch!=0||mut_deadline!=0)',a)
 bench=bench[:a]+(Path(__file__).with_name('mission.sv').read_text())+bench[z:]
 bench=bench.replace(' for(k=0;k<32;k=k+1)begin rq0_bank[k]=0;', ' for(integer ri=0;ri<8;ri=ri+1)raw_seen[ri]=0;\n if($value$plusargs("MUT_RAW=%d",mut_raw))begin end\n if($value$plusargs("MUT_EARLY=%d",mut_early))begin end\n for(k=0;k<32;k=k+1)begin rq0_bank[k]=0;')
 bench=bench.replace('PASS TIMING833_ROLE_VMFC_SHARED_NATIVE_PHY_VM_CP_PROVIDER','PASS RAW_COPY_ROLE_SHARED_NATIVE_PHY_VM_CP_PROVIDER')
 bench=bench.replace(' $display("LOCAL_NS_COUNTS', ' if(raw_total!=3072)$fatal(1,"RAW_SECTOR_CONSERVATION total=%0d",raw_total);\n $display("RAW_CONSERVATION sectors=%0d joint_epochs=2 copy_only_epochs=1 raw_only_epochs=1",raw_total);\n $display("LOCAL_NS_COUNTS')
 if transport_age:
  if transport_age!=82:raise ValueError('this measured transport probe reserves exactly82fixtureedges')
  transport=""" reg[81:0]transport_v=0;reg[307:0]transport_cmd[0:81];reg[31:0]transport_cycle[0:81];integer mut_cycle_age=0;
 initial if($value$plusargs("MUT_CYCLE_AGE=%d",mut_cycle_age))begin end
 always @(posedge clk)begin
 transport_v<=rst_n?{transport_v[80:0],load_v}:82'd0;transport_cmd[0]<=cmd;transport_cycle[0]<=cycle;
 for(integer ti=1;ti<82;ti=ti+1)begin transport_cmd[ti]<=transport_cmd[ti-1];transport_cycle[ti]<=transport_cycle[ti-1];end
 end
 wire[31:0]forwarded_cycle=transport_cycle[81]-(mut_cycle_age!=0?32'd82:32'd0);
"""
  spot=bench.index(' ot_hbm_static_load_native_provider_quad #')
  bench=bench[:spot]+transport+bench[spot:]
  bench=bench.replace('ot_hbm_static_load_native_provider_quad #(.SOURCE_QUAD(2))dut(.clk(clk),.rst_n(rst_n),.cmd_v(load_v),.cmd(cmd),.cycle(cycle)',
    'ot_hbm_static_load_native_provider_quad #(.SOURCE_QUAD(2),.CP_CYCLE_AGE(82))dut(.clk(clk),.rst_n(rst_n),.cmd_v(transport_v[81]),.cmd(transport_cmd[81]),.cycle(forwarded_cycle)')
  # The SOURCE-side direction dispatcher rejects metadata while its current
  # endpoint is busy. Preserve that check: later callers must pay82morelead
  # edges. The first future context is sent16edges earlier to beat ROLE fill.
  bench=bench.replace("entry={command,32'(at_date)};\n write_word(12'h800","entry={command,32'(at_date-(di==0?16:0))};\n write_word(12'h800",1)
  bench=bench.replace('issue_date=di==0?(mut_early!=0?800:4096):at_date+8;','issue_date=di==0?(mut_early!=0?800:4096):at_date+90;')
  bench=bench.replace('if(rst_n&&dut.consumer.dated_step)begin','if(rst_n&&dut.consumer.dated_step)begin\n if(dut.consumer.cycle!==cycle)$fatal(1,"CP_WALL_CYCLE_AGE expected=%0d actual=%0d",cycle,dut.consumer.cycle);')
  bench=bench.replace(' $display("CP_TRANSPORT_CALLER_PRICE metadata_edges=82 per_later_command_edges=82 per14LOADepoch_added=1066 total3epoch_added=3198");\n if(raw_total!=3072)', ' if(first_step!=4660||first_packet!=4668||last_step!=27377||last_packet!=27385)$fatal(1,"TRANSPORT_CALLER_STEP_PRICE_MISMATCH");\n $display("CP_TRANSPORT_CALLER_PRICE metadata_edges=82 per_later_command_edges=82 per14LOADepoch_added=1066 total3epoch_added=3198");\n if(raw_total!=3072)')
 p=out/'tb_raw_copy_provider.sv';p.write_text(bench);sources.append(p)
 (out/'sources.f').write_text('\n'.join(map(str,sources))+'\n')
 (out/'source_pins.json').write_text(json.dumps(dict(scope='actual endpoint composition; no production adoption',sources=pins),indent=1)+'\n')
 print('STAGED',len(sources),'native source files')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cp-transport-age',type=int,choices=(0,82),default=0);a=p.parse_args();stage(a.out.resolve(),a.cp_transport_age)
