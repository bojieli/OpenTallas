#!/usr/bin/env python3
"""Compose genuine SOURCE0 BODY runs with bounded native CP table pages.

Fixed dates include explicit per-command readback gaps. HOST writes and target106
are fixture reservations; this does not adopt a production global calendar.
"""
import argparse,collections,hashlib,json
from pathlib import Path
from stack0_body_probe import prepare,git
EXTRA=['rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_cp_collar.sv','rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv','rtl/hbm_accel/loader/service_native/split/ot_hbm_static_load_cmd_provider_quad.sv','rtl/hbm_accel/loader/service_native/split/ot_hbm_static_load_vm_commit_guard.sv']
def make(repo,body,out,mode,order="grouped",limit=None):
 prepare(repo,body,out,mode,order,limit)
 full_runs=json.loads(body.read_text())['runs']
 def key(r):return ((r['resident_command'],) if order=='source' else ())+(r['row'],r['col'],r['half'])
 full_groups=[]
 if order=='source':
  for r in full_runs:
   if not full_groups or full_groups[-1][0]!=key(r):full_groups.append([key(r),0])
   full_groups[-1][1]+=1
 else:full_groups=list(collections.Counter(key(r) for r in full_runs).items())
 max_pages=sum((n+127)//128 for _,n in full_groups)
 runs=json.loads((out/'source_runs.json').read_text());steps=[int(x,16) for x in(out/'steps.mem').read_text().splitlines()][:len(runs)]
 groups=[]
 for i,r in enumerate(runs):
  window=key(r)
  if not groups or groups[-1][0]!=window:groups.append((window,[]))
  groups[-1][1].append(i)
 pages=[];epoch=6
 for window,indices in groups:
  epoch+=1
  for start in range(0,len(indices),128):
   ids=indices[start:start+128];at=32;words=[];records=[]
   for i in ids:
    issue=at+8;drain=issue+steps[i]+24;move=int(runs[i]['effective227'],16)
    cmd=(epoch<<292)|(move<<64)|(drain<<32)|issue;entry=(cmd<<32)|at
    words.extend([entry&((1<<256)-1),entry>>256]);records.append({'phase':i,'at':at,'issue':issue,'drain':drain,'steps':steps[i],'move':runs[i]['effective227']})
    at=drain+steps[i]+128
   page={'first':ids[0],'last':ids[-1],'limit':len(ids),'epoch':epoch,'window':window,'records':records};pages.append(page)
   (out/f'cp_page{len(pages)-1}.mem').write_text(''.join(f'{w:064x}\n'for w in words)+('0'*64+'\n')*(256-len(words)))
 def mem(n,values):(out/n).write_text(''.join(f'{x:08x}\n'for x in values)+('00000000\n')*(max_pages-len(values)))
 mem('cp_page_first.mem',[p['first']for p in pages]);mem('cp_page_last.mem',[p['last']for p in pages]);mem('cp_page_limit.mem',[p['limit']for p in pages])
 src=out/'sources';files=(out/'files.f').read_text().splitlines();pins=json.loads((out/'sources.json').read_text())
 for path in EXTRA:
  raw=git(repo,'24de429cd',path);dest=src/Path(path).name;dest.write_bytes(raw);files.append('sources/'+dest.name);pins[path]={'revision':'24de429cd','sha256':hashlib.sha256(raw).hexdigest()}
 tb=(src/'tb_stack0_body_provider.sv').read_text().replace('module tb_stack0_body_provider #','module tb_stack0_body_cp #')
 tb=tb.replace('reg load_desc=0,step=0,release_v=0;', 'reg release_v=0;')
 tb=tb.replace('wire[1:0]active,provider_fault;', 'wire[1:0]active,provider_fault,load_done; wire[31:0]vm_fault; for(genvar f=0;f<32;f=f+1)assign vm_fault[f]=status[f][17]|status[f][16];')
 begin=tb.index(' ot_hbm_static_load_provider_quad #');end=tb.index('\n end\n wire[280:0]vm_dq',begin)
 tb=tb[:begin]+''' ot_hbm_static_load_cmd_provider_quad #(.SOURCE_STACK(0),.SOURCE_LOW_QUAD(0),.SOURCE_QUAD(h))dut(.clk(clk),.rst_n(rst_n),.cmd_v(cp_cmd_v&&half==h),.cmd(cp_cmd),.cycle(cp_cycle),.command_fault_i(cp_fault),
 .begin_v(cal_v&&cal_payload[0]&&half==h),.begin_bank(cal_payload[1]),.begin_epoch(cal_payload[17:2]),.begin_row(cal_payload[84:70]),.begin_col(cal_payload[88:85]),
 .fill_v(h==0?lfv:hfv),.fill_bank(h==0?lfb:hfb),.fill_slot(h==0?lfs:hfs),.fill_epoch(h==0?lfe:hfe),.fill_data(h==0?lfd:hfd),
 .release_v_i(release_v&&half==h),.release_buffer_i(1'b0),.release_epoch_i(epoch),.vm_dq_done_i(native_done),.vm_fault_i(vm_fault),
 .busy_o(active[h]),.vm_dq(dq[h]),.block_ready(ready[h]),.leaf_fault(leaf_fault[h]),.fault_o(provider_fault[h]),.load_done_o(load_done[h]),.dated_step_o(),.admit_o());'''+tb[end:]
 insert='''
 // One actual CP collar, native 128-command/two-SRAM table, fixture target106.
 reg cp_desc_v=0,cp_launch_v=0; reg[12:0]cp_limit=0;
 wire cp_cmd_v,cp_fault,cp_configured,cp_active;wire[307:0]cp_cmd;wire[31:0]cp_cycle;
 ot_hgi_dma_back_cp_collar cp(.clk(clk),.rst_n(rst_n),.tgt(8'd106),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(cp_desc_v),.desc_base(12'd0),.desc_limit(cp_limit),.desc_loops(16'd1),.launch_v(cp_launch_v),.tgt_active(|active),.tgt_fault(|provider_fault),
 .cmd_v(cp_cmd_v),.cmd(cp_cmd),.cycle(cp_cycle),.configured(cp_configured),.fault(cp_fault),.active(cp_active));
 integer page_no=0,done_count=0,cmd_count=0,mut_drain=0,page_count=@@COUNT@@;reg[255:0]cp_words[0:255];reg[31:0]page_first[0:@@PAGES@@-1],page_last[0:@@PAGES@@-1],page_limit[0:@@PAGES@@-1];
 always @(posedge clk)if(rst_n)begin #2;if(cp_fault)$fatal(1,"S0_CP_FAULT phase%0d page%0d",phase,page_no);if(cp_cmd_v)cmd_count=cmd_count+1;if(|load_done)done_count=done_count+1;end
'''.replace('@@PAGES@@',str(max_pages)).replace('@@COUNT@@',str(len(pages)))
 tb=tb.replace(' wire[280:0]vm_dq=dq[half];',insert+' wire[280:0]vm_dq=dq[half];')
 tb=tb.replace('void\'($value$plusargs("MUT_EPOCH=%d",mut_epoch));','void\'($value$plusargs("MUT_EPOCH=%d",mut_epoch));void\'($value$plusargs("MUT_DRAIN=%d",mut_drain));void\'($value$plusargs("PAGES=%d",page_count));\n $readmemh("cp_page_first.mem",page_first);$readmemh("cp_page_last.mem",page_last);$readmemh("cp_page_limit.mem",page_limit);')
 old=' load_desc=1;tick();load_desc=0;step=1;repeat(steps[phase])tick();step=0;repeat(24)tick();'
 new=''' if(phase==page_first[page_no])begin
 cfg_target=106;cp_limit=13'(page_limit[page_no]);$readmemh($sformatf("cp_page%0d.mem",page_no),cp_words);
 // Deliberately shorten the first drain without altering packet payloads.
 if(mut_drain!=0&&page_no==0)cp_words[0][95:64]=cp_words[0][63:32]+1;
 for(integer wi=0;wi<2*page_limit[page_no];wi=wi+1)write_word(12'h800+12'(wi),cp_words[wi]);
 repeat(16)tick();cp_desc_v=1;tick();cp_desc_v=0;repeat(16)tick();if(!cp_configured)$fatal(1,"S0_CP_NOT_CONFIGURED");
 cp_launch_v=1;tick();cp_launch_v=0;
 end
 waiting=0;while(done_count<=phase)begin tick();waiting=waiting+1;if(waiting>20000)$fatal(1,"S0_CP_DONE_TIMEOUT phase%0d done%0d",phase,done_count);end
 repeat(2)tick();'''
 assert old in tb;tb=tb.replace(old,new)
 tb=tb.replace(' if(phase==run_count-1||window_info[phase+1]!=window_info[phase])begin release_v', ' if(phase==page_last[page_no])begin waiting=0;while(cp_active||(|active))begin tick();waiting=waiting+1;if(waiting>20000)$fatal(1,"S0_CP_PAGE_DRAIN");end page_no=page_no+1;end\n if(phase==run_count-1||window_info[phase+1]!=window_info[phase])begin release_v')
 tb=tb.replace('if(mut_epoch!=0)$fatal', 'if(mut_epoch!=0||mut_drain!=0)$fatal')
 tb=tb.replace('if(got!=total_packets||words!=total_words||acks!=total_packets||read_got!=total_packets)', 'if(got!=total_packets||words!=total_words||acks!=total_packets||read_got!=total_packets||done_count!=run_count||cmd_count!=run_count||page_no!=page_count)'.replace('@@PAGES@@',str(len(pages))))
 tb=tb.replace('S0_BODY_PROVIDER PASS descriptors=', 'S0_BODY_NATIVE_CP PASS descriptors=')
 if order=='source':
  tb=tb.replace('mut_drain=0,page_count=', 'mut_drain=0,mut_release=0,page_count=')
  tb=tb.replace('void\'($value$plusargs("MUT_DRAIN=%d",mut_drain));', 'void\'($value$plusargs("MUT_DRAIN=%d",mut_drain));void\'($value$plusargs("MUT_RELEASE=%d",mut_release));')
  tb=tb.replace('release_v=1;tick();release_v=0;', 'release_v=!(mut_release!=0&&phase<run_count-1&&window_info[phase+1][63:20]!=window_info[phase][63:20]&&window_info[phase+1][19:0]==window_info[phase][19:0]);tick();release_v=0;')
  tb=tb.replace('if(mut_epoch!=0||mut_drain!=0)', 'if(mut_epoch!=0||mut_drain!=0||mut_release!=0)')
 (src/'tb_stack0_body_cp.sv').write_text(tb);files.remove('sources/tb_stack0_body_provider.sv');files.append('sources/tb_stack0_body_cp.sv');(out/'files.f').write_text('\n'.join(files)+'\n');(out/'sources.json').write_text(json.dumps(pins,indent=1)+'\n')
 (out/'cp_pages.json').write_text(json.dumps({'pages':pages,'source_stack':0,'table_depth':128,'production_calendar_adopted':False,'host_wire_cost_included':False,'fixture_target':106,'original_source_order':order=='source','BODY_barriers_encoded':order=='source','scope':'Actual CP table→command guard→SOURCE0 provider→native VM transport; fixed fixture dates/host gaps only; intervening resident operations not executed'},indent=1)+'\n')
 run=(out/'run.sh').read_text().replace('+RUNS=',f'+PAGES={len(pages)} +RUNS=').replace('tb_stack0_body_provider','tb_stack0_body_cp').replace('S0_BODY_PROVIDER PASS','S0_BODY_NATIVE_CP PASS').replace('+MUT_EPOCH=1','+MUT_DRAIN=1').replace('mutant_epoch.log','mutant_drain.log').replace("grep 'S0_PROBE_FAULT'", "grep -E 'S0_PROBE_FAULT|S0_CP_FAULT'")
 if order=='source':
  count=json.loads((out/'spec.json').read_text())
  run+=f'''if [ "${{S0_MUTANTS:-1}}" = 1 ];then
 if "$BIN" +PAGES={len(pages)} +RUNS={len(runs)} +PACKETS={count['packets']} +WORDS={count['words']} +HBM_IMG_DIR="$PWD/images" +MUT_RELEASE=1 > mutant_release.log 2>&1;then echo 'MUTANT RELEASE ESCAPED';exit 2;fi
 grep -E 'S0_PROBE_FAULT|S0_CP_FAULT' mutant_release.log
fi
'''
 (out/'run.sh').write_text(run)
 print(json.dumps({'mode':mode,'commands':len(runs),'pages':len(pages),'max_page':max(p['limit']for p in pages),'fixed_dates':True,'production_calendar_adopted':False}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--body-plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mode',choices=['pilot','canary','volume'],default='pilot');p.add_argument('--order',choices=['grouped','source'],default='grouped');p.add_argument('--limit',type=int);a=p.parse_args();make(a.repo,a.body_plan,a.out,a.mode,a.order,a.limit)
