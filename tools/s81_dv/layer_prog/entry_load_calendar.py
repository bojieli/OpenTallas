"""Place real page-local HLOAD/GAIN after exact selected VP/VN store commits.

Only relative issuer slots are assigned. KIT, END, host reload/start, root
phase and SEAL stay outside this helper's qualified local schedule.
"""
import copy
from layer_prog.entry_write_calendar import compile_pages,encode_unsealed
from layer_prog.target5_arrivals import lower_page,compose
import dv_layer_compile as D


def compile_jobs(entry, control, transport, inventory, target5_receipt, local_control, source_root, manifest, *, first_issue, issue_stride):
    validated=compile_pages(entry,first_issue=first_issue,issue_stride=issue_stride)
    if transport.get('vn_local_intake',{}).get('verdict')!='PASS_SELECTED_FUNCTIONAL_VN_STORE_INTAKE':
        raise ValueError('page loads require actual selected VN store readiness')
    leaves={}
    for index,w in enumerate(entry['writes']):leaves.setdefault((w['slice'],w['leaf']),[]).append((index,w))
    if len(leaves)!=80 or any(len(w)!=49 for w in leaves.values()):raise ValueError('all80 actual complete49row leaf images required')
    routes={(r['slice'],r['leaf']):r for r in transport['leaves']}
    groups=list(leaves.items());jobs=[]
    for start in range(0,len(groups),2):
        selected=groups[start:start+2];indexed=[iw for _,rows in selected for iw in rows]
        indexes=[i for i,_ in indexed]
        if indexes!=list(range(indexes[0],indexes[-1]+1)):raise ValueError('leaf grouping would reorder actual source writes')
        subset=dict(entry,writes=[w for _,w in indexed],row_count=len(indexed))
        page=compile_pages(subset,first_issue=first_issue,issue_stride=issue_stride)[0]
        page.update(source_row_count=entry['row_count'],source_write_indices=[indexes[0],indexes[-1]+1],source_write_table_sha256=validated[0]['source_write_table_sha256'])
        for item in page['commands']+page['templates']:item['source_write_index']+=indexes[0]
        dated=compose(lower_page(page,control,local_control),transport,inventory,target5_receipt,source_root,manifest)
        last={key:max(c['leaf_store_commit_edge']for c in dated['commands']if(c['slice'],c['leaf'])==key)for key,_ in selected}
        page['write_commit_dates']=dated['commands'];next_issue=max(c['issue']for c in page['commands'])+2
        hready={};load_dates=[]
        for kind in('HLOAD','GAIN'):
            for key,_ in selected:
                sl,leaf=key;route=routes[key];path=control['paths'][sl];sid=local_control.die.slices()[sl]['sid']
                port='vo_n'if sid&1 else'vo_s'
                arrival=local_control.local('u_seqhost','calendar_command_to_'+port)['edges']+path['xr_command_pin_edge']+route['command_transport_edges']
                prior=last[key]if kind=='HLOAD'else hready[key]
                issue=max(next_issue,prior+1-arrival)
                op=D.VP[kind];a0=0 if kind=='HLOAD'else 64
                payload=D.ctl_payload(1<<sid,0,1<<leaf,D.vp_cmd(op,a0=a0))
                ti=len(page['templates']);engine=D.ENG['VN'if sid&1 else'VS'];done=issue+5
                if done>=1<<24:raise ValueError('entry load date exceeds native slot field')
                ready=issue+arrival+route['local_hload_readiness_edges'if kind=='HLOAD'else'local_gain_readiness_edges']
                page['templates'].append(dict(i=ti,name=f'entry.{kind}.{sid}.{leaf}',payload186=f'{payload:047x}'))
                page['commands'].append(dict(kind=kind,slice=sl,sid=sid,leaf=leaf,issue=issue,template=ti))
                page['rows'].append(dict(eng=engine,issue=issue,done=done,arg=ti,tix=ti,row76=f'{D.pack_row(done,issue,engine,ti):019x}'))
                load_dates.append(dict(kind=kind,slice=sl,leaf=leaf,issue=issue,vp_command_input_edge=issue+arrival,
                    issuer_to_vp_command_input_edges=arrival,required_prior_store_commit_edge=prior,last_vn_store_commit_edge=ready,
                    local_store_readiness_edges=ready-issue-arrival,source_relative=True))
                if kind=='HLOAD':hready[key]=ready
                next_issue=issue+1
        page['load_dates']=load_dates;page['source_relative_retire_not_before']=max(r['last_vn_store_commit_edge']for r in load_dates)+1
        page.update(schema='opentallas.s81.entry_write_load_command_page.v1',command_count=len(page['commands']),host_word_count=len(encode_unsealed(page)),native_job_sealed=False,host_boot_complete=False)
        check_page(page);jobs.append(page)
    return jobs


def check_page(page):
    """Check encoded dates and measured store/read fences independently of placement."""
    if len(page['rows'])!=102 or len(page['templates'])!=102 or len(page['commands'])!=102:
        raise ValueError('two49row images plus four actual reader commands required')
    if len(page['rows'])+2>128:raise ValueError('native128row page needs actual KIT/END reservation')
    commands={c['template']:c for c in page['commands']};rows={r['tix']:r for r in page['rows']};seen=set();live={};last_done={}
    for row in page['rows']:
        c=commands[row['tix']];key=(row['eng'],row['issue'])
        if key in seen or c['issue']!=row['issue']or row['done']!=row['issue']+5:raise ValueError('native issuer row/ACK differs')
        seen.add(key)
        if row['row76']!=f"{D.pack_row(row['done'],row['issue'],row['eng'],row['arg']):019x}":raise ValueError('native encoded PW row differs')
        if row['done']<=last_done.get(row['eng'],-1):raise ValueError('per-engine completion slots not increasing')
        last_done[row['eng']]=row['done'];live[row['eng']]=[d for d in live.get(row['eng'],[])if d>=row['issue']]+[row['done']]
        if len(live[row['eng']])>8:raise ValueError('native issuer exceeds eight live commands')
    actual_writes={}
    for c in page['write_commit_dates']:
        key=(c['slice'],c['leaf']);actual_writes[key]=max(actual_writes.get(key,-1),c['leaf_store_commit_edge'])
    hready={}
    for r in page['load_dates']:
        key=(r['slice'],r['leaf']);prior=actual_writes[key]if r['kind']=='HLOAD'else hready[key]
        c=next(c for c in page['commands']if c['kind']==r['kind']and(c['slice'],c['leaf'])==key)
        payload=int(page['templates'][c['template']]['payload186'],16)
        expected=D.ctl_payload(1<<c['sid'],0,1<<c['leaf'],D.vp_cmd(D.VP[r['kind']],a0=0 if r['kind']=='HLOAD'else 64))
        if payload!=expected:raise ValueError('reader payload differs from actual leaf/operation/row')
        if r['vp_command_input_edge']!=r['issue']+r['issuer_to_vp_command_input_edges']:raise ValueError('reader input date differs from exact route offset')
        if r['issue']!=c['issue']or r['vp_command_input_edge']<=prior or r['required_prior_store_commit_edge']!=prior:
            raise ValueError('reader command can observe stale prior store')
        if r['last_vn_store_commit_edge']!=r['vp_command_input_edge']+r['local_store_readiness_edges']:
            raise ValueError('reader store completion age differs')
        if r['kind']=='HLOAD':hready[key]=r['last_vn_store_commit_edge']
    if page['source_relative_retire_not_before']<=max(r['last_vn_store_commit_edge']for r in page['load_dates']):raise ValueError('page retirement precedes actual VN stores')
    return True
