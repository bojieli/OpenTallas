"""Finite storage/service costs for selected typed witness MODEL; no storage RTL."""
import argparse,hashlib,json,re
from pathlib import Path
class Error(ValueError):pass

class InstallGuard:
    def __init__(self,packet):
        self.expected={r['first_PW']+i:int(w,16) for r in packet['records'] for i,w in enumerate(r['words'])}
        self.next=400;self.active=False;self.ready=False;self.auth=False;self.drained=False;self.digest=packet['calendar_copy_candidate_digest']
    def word(self,addr,data):
        if self.active or self.ready or addr!=self.next or data!=self.expected.get(addr):raise Error('active/duplicate/order/header/padding/payload')
        self.next+=1
    def drain(self,committed_rows,pending_writes):
        if self.next!=439 or committed_rows!=28 or pending_writes:raise Error('partial or undrained native image')
        self.drained=True
    def authenticate(self,digest,all_copies):
        if not self.drained or digest!=self.digest or not all_copies:raise Error('copy digest/profile or drain incomplete')
        self.auth=True;self.ready=True
    def prefetch(self):
        if not self.ready or not self.auth or not self.drained:raise Error('read before installed/authenticated')
    def execute(self):
        self.prefetch();self.active=True

def reject(name,fn):
    try:fn()
    except Error:return dict(name=name,rejected=True,scope='executable MODEL policy; no RTL guard claim')
    raise AssertionError('guard mutant accepted '+name)

def guard_checks(packet):
    def loaded():
        g=InstallGuard(packet)
        for addr,data in sorted(g.expected.items()):g.word(addr,data)
        return g
    g=loaded();g.drain(28,0);g.authenticate(g.digest,True);g.prefetch();g.execute()
    result=[]
    result.append(reject('write_during_execution',lambda:g.word(400,g.expected[400])))
    result.append(reject('prefetch_during_install',lambda:InstallGuard(packet).prefetch()))
    result.append(reject('execute_before_install',lambda:InstallGuard(packet).execute()))
    result.append(reject('missing_final_native_drain',lambda:loaded().drain(27,1)))
    result.append(reject('missing_partial_record',lambda:InstallGuard(packet).drain(28,0)))
    def duplicate():
        q=InstallGuard(packet);q.word(400,q.expected[400]);q.word(400,q.expected[400])
    result.append(reject('duplicate_PW',duplicate))
    result.append(reject('out_of_order_PW',lambda:InstallGuard(packet).word(401,0)))
    def bad_header():
        q=InstallGuard(packet);q.word(400,q.expected[400]);q.word(401,q.expected[401]);q.word(402,q.expected[402]^(1<<63))
    result.append(reject('header_or_padding_mutation',bad_header))
    def bad_auth(copies,digest):
        q=loaded();q.drain(28,0);q.authenticate(digest,copies)
    result.append(reject('wrong_profile_digest',lambda:bad_auth(True,'0'*16)))
    result.append(reject('missing_physical_copy_auth',lambda:bad_auth(False,g.digest)))
    result.append(reject('authenticate_before_drain',lambda:loaded().authenticate(g.digest,True)))
    return result

def build(model,packet,macro,cell,out):
    groups=model['source_groups'];records=packet['records'];stream=0;fetch=[]
    for i,r in enumerate(records):
        w=[int(x,16) for x in r['words']];value=w[0]|(w[1]<<64)|((w[2]&63)<<128)
        stream|=value<<(134*i)
        start=134*i;first=start//64;last=(start+133)//64
        fetch.append(dict(group=i,family=groups[i]['family'],pidx=groups[i]['local_pidx'],
          first_row=first,last_row=last,bit_offset=start%64,read_slots=last-first+1))
    rows=[(stream>>(64*i))&((1<<64)-1) for i in range(32)]
    assert all(r==0 for r in rows[28:]) and rows[27]>>14==0
    (out/'packed_sram.hex').write_text(''.join(f'{x:016x}\n' for x in rows))
    # On each edge: commit previous registered boundary write, then service
    # old FIFO head, then accept this edge's PW record. No input ready/wait.
    queue=[];carry=0;nbits=0;pending=None;writes=[];maxq=0;beats=0
    for edge in range(45):
        if pending is not None:writes.append(dict(edge=edge,row=len(writes),value=pending));pending=None
        if queue:pending=queue.pop(0)
        if edge<39:
            beats+=1
            if edge%3==2:
                r=records[edge//3];w=[int(x,16) for x in r['words']]
                value=w[0]|(w[1]<<64)|((w[2]&63)<<128)
                value=(value<<nbits)|carry;total=134+nbits
                for j in range(total//64):queue.append((value>>(64*j))&((1<<64)-1))
                nbits=total%64;carry=value>>(64*(total//64))
                if edge==38:queue.append(carry);carry=0;nbits=0
        maxq=max(maxq,len(queue))
        if len(queue)>3:raise Error('write FIFO overflow')
    assert [w['value'] for w in writes]==rows[:28]
    # Four simultaneous diagnostic source contexts. Their real command outputs
    # would collide; this stresses storage only, not full-MU admissibility.
    service=[];occupied=set();intervals=[]
    for i,(g,f) in enumerate(zip(groups,fetch)):
      for u in range(4):
        request=g['first_w5']-20+4*u;n=f['read_slots']
        for e in range(request,request+n):
            if e in occupied:raise Error('native read service collision')
            occupied.add(e)
        usable=request+n+2
        if usable>=g['first_w5']:raise Error('prefetch misses first witness sample')
        service.append(dict(user=u,group=i,request_sample=request,read_slots=n,
          first_macro_read_sample=request+1,last_macro_read_sample=request+n,
          last_capture_publication=request+n+1,earliest_consumer_sample=usable,
          first_witness_source_edge=g['first_w5'],slack_edges=g['first_w5']-usable))
        intervals.append((u,request,g['last_w5']+1))
    maximum=max(sum(u==v and a<=e<=b for v,a,b in intervals) for u in range(4) for e in range(5600))
    if maximum>2:raise Error('two active-template slots per context insufficient')
    faults=[]
    for name in ['install_during_execution','read_during_install','same_address_install_prefetch',
                 'execution_before_final_native_write','execution_before_complete_copy_digest',
                 'missing_partial_PW','duplicate_PW','out_of_order_PW','header_or_padding_mutation',
                 'prefetch_late','stale_prefetch_generation','overwrite_live_template']:
        # These are required policy guard cases, not implemented RTL passes.
        faults.append(dict(name=name,required_fault=True,RTL_tested=False))
    loader=dict(partial_assembly=128,carry=63,carry_count=6,write_FIFO3x64=192,
      FIFO_count=2,FIFO_read_write_pointers=4,next_PW=6,record_index=4,part=2,
      loaded_mask=13,registered_write_boundary=70,row_emit_pointer=5,
      rows_committed=6,loading_seal_fault_drain=4)
    active=dict(template_cache8x134=1072,seen8x12=96,group_ids8x4=32,
      cache_valid=8,context_cycle13x4=52,stage6x4=24,generation16x4=64,
      held_ME_XPF_users=4,held_valid=2,fault=1)
    prefetch=dict(read_assembly4x64=256,two_pending_target_tags=58,
      registered_read_request_addr_CE=6,word_indices=4,busy=1)
    ff_loader=dict(partial_assembly=128,part=2,record_index=4,next_PW=6,
      loaded_mask=13,loading_seal_fault=3,drain=1)
    ff_prefetch=dict(pending_target_tag=29,selector=4,valid=1)
    native_ff=sum(loader.values())+sum(active.values())+sum(prefetch.values())
    full_ff=1742+sum(ff_loader.values())+sum(active.values())+sum(ff_prefetch.values())
    dff_area=float(re.search(r'area\s*:\s*([\d.]+)',cell).group(1))
    clockcap=float(re.search(r'pin \(CLK\).*?capacitance\s*:\s*([\d.]+)',cell,re.S).group(1))
    return dict(schema='opentallas.qwen.witness-storage-service-options.v1',production_bound=False,storage_RTL_implemented=False,
      packed=dict(useful_bits=1742,native_rows_used=28,physical_rows=32,row_bits=64,
        explicit_zero_rows=[28,29,30,31],last_row_useful_low_bits=14,
        template_fetch=fetch,read_slots_per13groups=sum(f['read_slots'] for f in fetch),
        read_slots_4contexts=4*sum(f['read_slots'] for f in fetch)),
      installation=dict(PW_beats=beats,first_PW_sample=0,last_PW_sample=38,
        first_native_write_sample=writes[0]['edge'],last_native_write_sample=writes[-1]['edge'],
        seal_publication=writes[-1]['edge']+1,first_usable_seal_sample=writes[-1]['edge']+2,
        max_write_FIFO_words=maxq,native_writes=28,writes=[{k:v for k,v in w.items() if k!='value'} for w in writes],
        complete_physical_copy_authentication_still_required=True),
      storage_prefetch_stress=dict(contexts=4,simultaneous_origin=True,service=service,
        native_read_ports=1,max_active_or_prefetch_reserved_templates_per_context=maximum,
        minimum_first_witness_slack=min(s['slack_edges'] for s in service),
        intended_slots_per_context=2,cal_output_execution_admissibility=False,
        physical_clock_axis_bound=False,
        axis='separate runtime unit phase after installed/authenticated; installation-relative sample0 is not shared',
        absolute_execution_start=None),
      required_faults=faults,MODEL_guard_mutants=guard_checks(packet),
      native_SRAM=dict(master='ot_sram_1r1w_32x64_m1',source_commit='b65718325',
        geometry_um=[macro['area']['macro_width_um'],macro['area']['macro_height_um']],area_um2=macro['area']['macro_area_um2'],
        true_single_clock_1R1W=True,same_address='read_before_write',
        read_sample_to_output_publication=0,output_to_external_capture=1,
        request_control_sample_to_macro_read=1,max_record_request_to_usable_sample=6,
        loader_FF_components=loader,active_FF_components=active,prefetch_FF_components=prefetch,
        total_FF_bits=native_ff,native_clock_pins=1,FF_clock_pins=native_ff,
        conservative_resettable_control_bits=58+283+69,
        raw_DFF_plus_macro_area_lower_bound_um2=native_ff*dff_area+macro['area']['macro_area_um2'],
        raw_clockcap_DFF_only_ff=native_ff*clockcap,
        max_indexed_data_block_bits=1072,alignment_mux2_equivalents=134*12,
        feedback_enable_mux_bits=128+63+192+64+1072+256),
      finite_FF=dict(template_block_bits=1742,loader_FF_components=ff_loader,
        active_FF_components=active,prefetch_FF_components=ff_prefetch,
        total_FF_bits=full_ff,FF_clock_pins=full_ff,conservative_resettable_control_bits=29+283+34,
        raw_DFF_area_lower_bound_um2=full_ff*dff_area,raw_clockcap_DFF_only_ff=full_ff*clockcap,
        template_read_ports=1,template_read_width=134,request_to_usable_sample=2,
        template_read_mux2_equivalents=134*12,feedback_enable_mux_bits=1742+1072+128,
        template_async_reset=False,active_data_async_reset=False,max_indexed_block_bits=1742),
      clock_reset_scope='unreset data guarded by sealed/loaded/cachevalid; conservative control reset counts; no clock gates assumed',
      physical_cost_limits=['raw DFF area is a lower bound, excludes reset-cell uplift, enable/select/decode logic, buffers, CTS, route, placement and mux timing',
        'mux equivalents are explicit logic obligations, not mapped cell area or timing',
        'native macro has additional9.3458fF clock capacitance in TT view; pin cap alone is not clock-route signoff'],
      candidate_selection=None,physical_admission=False)
def main():
    ap=argparse.ArgumentParser()
    for k in ('model','packet','macro','cell','out'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    data=build(json.loads(a.model.read_bytes()),json.loads(a.packet.read_bytes()),json.loads(a.macro.read_bytes()),a.cell.read_text(),a.out)
    data['sources']={k:dict(path=str(getattr(a,k)),sha256=hashlib.sha256(getattr(a,k).read_bytes()).hexdigest()) for k in ('model','packet','macro','cell')}
    (a.out/'model.json').write_text(json.dumps(data,indent=2)+'\n')
    print('WITNESS_STORAGE_SERVICE_MODEL_PASS',data['packed']['read_slots_per13groups'],'readslots/context,',data['installation']['max_write_FIFO_words'],'FIFO words,',data['native_SRAM']['total_FF_bits'],'SRAM-option FF,',data['finite_FF']['total_FF_bits'],'FF-option FF; production false')
if __name__=='__main__':main()
