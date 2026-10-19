#!/usr/bin/env python3
"""Read-only GEN2e unread-output audit. Produces review candidates, never an admission manifest.

Reconstructs every connection bit from generated die RTL and cross-checks the
strict binder's independent diagnostic ranges. Unsupported syntax or a mismatch
fails closed. No RTL indexing, synthesis, gate-tree writes or waiver adoption.
"""
import argparse, collections, hashlib, json, re
from pathlib import Path


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ranges(bits):
    out=[]
    for b in sorted(bits):
        if out and b == out[-1][1]+1: out[-1][1]=b
        else: out.append([b,b])
    return out


def parse_die(path, contract):
    text=Path(path).read_text()
    widths={n:int(h)+1 for h,n in re.findall(r'^  wire \[(\d+):0\] (\w+);',text,re.M)}
    instances={};cur=None
    for no,line in enumerate(text.splitlines(),1):
        m=re.match(r'^  (\w+)(?: #\((.*)\))? (\w+) \($',line)
        if m:
            cur=m[3];instances[cur]=dict(master=m[1],line=no,connections={})
        elif cur:
            m=re.match(r'\s*\.(\w+)\((.*)\),?$',line)
            if m: instances[cur]['connections'][m[1]]=m[2]
            elif line=='  );': cur=None
    reads=collections.defaultdict(set);outputs={};consumers=collections.defaultdict(list)
    for n,a in instances.items():
        for p,expr in a['connections'].items():
            direction=contract['instances'][n]['ports'][p]['direction']
            if direction=='output': outputs[expr]=(n,p)
            else:
                for m in re.finditer(r'\b([A-Za-z_]\w*)(?:\[(\d+)(?::(\d+))?\])?',expr):
                    net,hi,lo=m.groups()
                    if net not in widths: continue
                    bits=list(range(widths[net])) if hi is None else ([int(hi)] if lo is None else list(range(int(lo),int(hi)+1)))
                    reads[net].update(bits)
                    consumers[net].append(dict(instance=n,port=p,ranges=ranges(bits)))
    unread={net:sorted(set(range(widths[net]))-reads[net]) for net in outputs if net in widths}
    unread={n:b for n,b in unread.items() if b}
    return instances,widths,outputs,reads,consumers,unread


def split_expr(s):
    out=[];depth=0;start=0
    for i,c in enumerate(s):
        depth += c=='{';depth -= c=='}'
        if c==',' and depth==0: out.append(s[start:i]);start=i+1
    out.append(s[start:]);return out


def expr_bits(s,widths):
    s=s.strip()
    m=re.fullmatch(r"(\d+)'([bdh])([0-9a-fA-F_]+)",s)
    if m:
        size,base,data=m.groups();value=int(data.replace('_',''),{'b':2,'d':10,'h':16}[base])
        return [('constant',(value>>b)&1) for b in range(int(size))]
    m=re.fullmatch(r'\{(\d+)\{(.*)\}\}',s)
    if m:return expr_bits(m[2],widths)*int(m[1])
    if s.startswith('{') and s.endswith('}'):
        return [b for part in reversed(split_expr(s[1:-1])) for b in expr_bits(part,widths)]
    m=re.fullmatch(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?',s)
    if not m or m[1] not in widths:raise ValueError('unsupported relay input '+s)
    net,hi,lo=m.groups()
    ids=range(widths[net]) if hi is None else ([int(hi)] if lo is None else range(int(lo),int(hi)+1))
    return [(net,b) for b in ids]


def padding_origin(net,bit,instances,widths,outputs,seen=()):
    if (net,bit) in seen:raise ValueError('relay cycle')
    n,p=outputs[net];a=instances[n]
    if not a['master'].startswith('hbfd_rly_') or p!='o':return None
    seq=expr_bits(a['connections']['i'],widths)
    if len(seq)!=widths[net]:raise ValueError('relay width differs')
    other,k=seq[bit]
    hop=dict(instance=n,master=a['master'],output_bit=bit,input_expression=a['connections']['i'])
    if other=='constant':return dict(constant=k,hops=[hop])
    if other not in outputs:return None
    prev=padding_origin(other,k,instances,widths,outputs,seen+((net,bit),))
    if prev is None:return None
    return dict(constant=prev['constant'],hops=[hop]+prev['hops'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--die-v',required=True);ap.add_argument('--contract',required=True)
    ap.add_argument('--bind-report',required=True);ap.add_argument('--out',required=True)
    args=ap.parse_args();c=json.loads(Path(args.contract).read_text());b=json.loads(Path(args.bind_report).read_text())
    inst,widths,outputs,reads,consumers,unread=parse_die(args.die_v,c)
    if digest(args.die_v)!=b['die_sha256']:raise ValueError('die hash differs from strict binder input')
    expected=b['unread_bit_ranges']
    actual={n:ranges(bits) for n,bits in unread.items()}
    if actual!=expected:raise ValueError('source graph differs from strict binder diagnostics')
    if sum(map(len,unread.values()))!=b['summary']['unread_net_bits']:raise ValueError('bit total differs')
    rows=[]
    for net,bits in sorted(unread.items()):
        n,p=outputs[net];a=inst[n];m=a['master'];info=c['instances'][n]
        row=dict(instance=n,master=m,port=p,net=net,width=widths[net],unread_ranges=ranges(bits),bit_count=len(bits),
            die_line=a['line'],source=info['source'],classification='unresolved_functional_or_status',
            reason='No semantic waiver proved. Preserve strict failure; inspect producer and required consumer.',
            evidence=[],allowlist_candidate=False)
        def candidate(cls,reason,evidence):
            row.update(classification=cls,reason=reason,evidence=evidence,allowlist_candidate=True)
        if m=='ot_hbm_svc_sm_group_id' and p in ('lt0','lt1','lb0','lb1','fm','expected_request'):
            sm='sm_'+n[4:];smc=inst[sm]['connections'];svgc=a['connections']
            assert svgc['sm_packet'] in smc['packet'] and svgc['sm_command'] in smc['command']
            assert consumers.get(svgc['fault'])
            candidate('duplicate_checker_feed','Service feed duplicates the SM normal feed; packet+command reach actual SM. Service feed fault remains observed. Output does not drive arithmetic.',
                ['ot_hbm_svc_sm_feed_programmed_id.sv consumer ot_smh_static_feed; fault OR includes feed_fault',
                 'ot_hbm_sm_attn_front_static.sv u_normal -> ot_smh_static_front.sv u_feed -> FC_t/FC_xr arithmetic',
                 dict(actual_sm=sm,packet=smc['packet'],command=smc['command'],service_fault_consumers=consumers[svgc['fault']])])
        elif m=='ot_hbm_accel_smh_attn' and p=='request':
            candidate('checked_request_observation','Normal request is command[82:40] observation; attention descriptor request is checked against expected_q inside SM. Actual K requests originate in service issuer, not this export.',
                ['ot_smh_static_feed.sv command[82:40] observational comment and expected_request assignment',
                 'ot_hbm_sm_attn_front_static.sv request mux and attention_q request!=expected_q schedule_fault check'])
        elif m=='ot_hbm_xp_aq_tree13_fmt' and p=='y':
            assert consumers.get(a['connections']['q']) and consumers.get(a['connections']['e'])
            candidate('unused_alternate_representation','y is dequantised BF16 reconstructed from same S10 quantiser state; production x-load consumes encoded q/e. This is not a missing quantiser result path.',
                ['ot_hbm_xp_aq_tree13.sv S11 separately assigns q,e and reconstructed BF16 y',dict(q_consumers=consumers[a['connections']['q']],e_consumers=consumers[a['connections']['e']])])
        elif m=='ot_hbm_idx_selector_static' and p in ('out_line','out_v','threshold_observe','selected_observe'):
            assert consumers.get(a['connections']['selected_line']) and consumers.get(a['connections']['selected_v'])
            candidate('selector_optional_readback','out_line/out_v expose separate EMIT raw readback; compact selected_line/selected_v drive actual link. Threshold/count are observation exports, used internally in selector.',
                ['ot_hbm_idx_selector_static.sv compact/selected_line versus emit/out_line branches',dict(selected_line_consumers=consumers[a['connections']['selected_line']],selected_v_consumers=consumers[a['connections']['selected_v']])])
        elif m.startswith('hbfd_rly_') and p=='o':
            proofs=[padding_origin(net,k,inst,widths,outputs) for k in bits]
            if all(z is not None and z['constant']==0 for z in proofs):
                candidate('propagated_zero_padding','Every unread bit traces through bit-preserving relay stages to an explicit sized zero pad. No live payload bit is waived.',
                    ['ot_hbm_rly.sv r<=i and assign o=r, no RTL mutant define',dict(max_hops=max(len(z['hops']) for z in proofs),first_bit_proof=proofs[0],last_bit_proof=proofs[-1])])
        elif m=='ot_static_cmd_target' and p in ('cmd_v','cmd','cycle') and info.get('params',{}).get('MODE')==0:
            candidate('inactive_mode_or_counter_export','MODE0 exports run_v/base/count to SVG. MODE1 command sequencer cannot start (rd_go requires MODE1); cycle is the free-running diagnostic export and SVG runs from its own compiler calendar.',
                ['ot_static_cmd_target.sv launch MODE0 run_v versus MODE1 seq_on; rd_go MODE==1; cycle<=cyc;cyc<=cyc+1',dict(run_consumers=consumers.get(a['connections']['run_v'],[]))])
        elif m=='hfd_hgi_vm_calendar_f20' and p=='ordinal':
            assert consumers.get(a['connections']['active']) and consumers.get(a['connections']['fault'])
            candidate('counter_or_ordinal_export','Calendar ordinal is registered ord1 observation. Actual calendar command fields drive consumers, while active and fault reach host target status.',
                ['ot_vms_calendar_static.sv ordinal<=ord1;calendar_v<=valid1;active<=busy',dict(active_consumers=consumers[a['connections']['active']],fault_consumers=consumers[a['connections']['fault']])])
        elif m=='ot_hgi_sfu_programme_store_r10' and p in ('programme_ordinal','io_ordinal'):
            assert consumers.get(a['connections']['fault'])
            candidate('internally_checked_ordinal_export','SFU p_omm/io_omm compare stripe ordinals internally; disagreement feeds sticky p_fault/io_fault and exported fault. These outputs only repeat representative ordinal.',
                ['ot_hgi_sfu_programme_store_r10.sv p_omm/io_omm -> p_fault/io_fault -> fault; programme_ordinal<=sp_ord[0];io_ordinal<=si_ord[0]',dict(fault_consumers=consumers[a['connections']['fault']])])
        elif m=='ot_hbm_static_cfg_collar':
            params=info.get('params',{})
            if p in ('rec','go') and params.get('NREC')==0:
                candidate('inactive_record_interface','NREC=0 makes recs_done permanently true, so record payload never emits and go remains zero. rec data need not initialise because no record is scheduled. start_v, programme writes, ready/active/fault remain connected.',
                    ['ot_hbm_static_cfg_collar.sv recs_done=(NREC==0)||...; payload/go assignment guarded !recs_done',dict(params=params,start_consumers=consumers.get(a['connections']['start_v'],[]))])
            elif p=='prm' and n=='col_su' and set(bits)==set(range(16,256)):
                candidate('reserved_operand_abi','SU operand row uses length[15:0]; remaining240bits are not part of current SU programme input ABI.',
                    [dict(length_consumers=consumers[net]),'ot_hbm_su_programme.sv length16; contract col_su note specifies operand row0[15:0]'])
            elif p=='prm' and n.startswith('col_sfu_') and set(bits)==set(range(78,256)):
                candidate('reserved_operand_abi','SFU operand row packs two39bit base/limit/loops records [77:0]; upper178bits unused by specified SFU ABI.',
                    [dict(start_field_consumers=consumers[net]),'contract SFU collar note arithmetic programme start[38:0],IO start[77:39]'])
            elif p=='prm' and n=='col_idx':
                assert ranges(bits)==[[44,50],[424,765],[1108,1449],[1460,1535]]
                candidate('reserved_operand_abi_review','Two physical stacks use bitmap slots0&2: SW/SE even/odd[82:423],NW/NE even/odd[766:1107]. Slots1&3 unused684bits; [44:50] and[1460:1535] are unused ABI holes. Current rank uses[81:74],k uses[1459:1450]. Host compiler layout compatibility still needs root review.',
                    ['ot_hbm_idx_score_quarter_static.sv keep_bitmap171, half strap and kb_r[beat_index]',dict(actual_consumed_ranges=ranges(reads[net]))])
            elif p=='rec' and n=='col_idx' and set(bits)==set(range(156,221)):
                candidate('reserved_record_abi','TOPK uses record[155:0] and ARGMAX[89:0]; upper65bits are outside both current descriptor ABIs.',[dict(record_field_consumers=consumers[net])])
            elif p=='pw_addr' and n=='col_idx':
                row.update(classification='unresolved_truncated_programme_address',reason='Collar AW12 exports address[11:0] but IDX programme consumes only[7:0]. Host install must constrain page/high address to zero; do not waive without an alias/range rejection proof.')
        elif m=='ot_hbm_hc_bankq_static' and n.endswith('7') and p in ('o_v','o_ss','o_nv','o_wa','o_xa'):
            assert consumers.get(a['connections']['sum_out']) and consumers.get(a['connections']['f_out'])
            candidate('terminal_chain_control','Bank7 forward control terminates; sum_out/f_out wrap to bank0.s_i, while bank0 receives fresh independent control. Payload and fault ring are connected; no command field is used after terminal bank.',
                [dict(sum_consumers=consumers[a['connections']['sum_out']],f_consumers=consumers[a['connections']['f_out']]),'ot_hbm_hc_bankq_static.sv separate control and sum/f outputs'])
        elif m=='ot_hbm_idx_score_quarter_static' and p=='score':
            assert bits==list(range(1,10))
            row.update(classification='unresolved_score_flags_and_last',reason='score[1]=last and[9:2]=8 arithmetic fl flags are dropped; XQR receives valid,kv,value,index. Producer fault aggregates efault/engine agreement/wf, not the arithmetic fl vector. Must prove exception policy or propagate flags; not a telemetry candidate.',evidence=['ot_hbm_idx_score_quarter_static.sv score[305:1]<={idx,val,kv,fl,last[0]}; fault aggregation excludes fl'])
        elif m=='ot_vms_status4_static' and p=='vmstat':
            row.update(classification='missing_vm_fault_path',reason='vmstat[18:16] contains bank protocolflt/uncorrectableECC and hub faults. Current host ingress has no vmstat input; fr quadrant leaves consume ring_fault only. Fatal flags must be wired. Low16 saturating CE count can be reviewed separately as telemetry.',evidence=['ot_vms_status_static.sv flags OR hub_status[2:0],ring_fault,bank_status[17]/[16]','ot_vms_status4_static.sv flags OR retained in vmstat[18:16]','ot_hbm_host_static_ingress.sv status inputs block_ready/program_active/program_fault only'])
        rows.append(row)
    counts=collections.defaultdict(lambda:dict(ports=0,bits=0))
    for row in rows:
        z=counts[row['classification']];z['ports']+=1;z['bits']+=row['bit_count']
    proof=dict(schema='opentallas.hbm_unread_audit_1019.v1',manifest_adopted=False,
        rule='Exact source-backed candidates require root review. Unresolved sets remain strict failures; no global waiver.',
        inputs={k:dict(path=getattr(args,k),sha256=digest(getattr(args,k))) for k in ('die_v','contract','bind_report')},
        crosscheck=dict(instances=len(inst),unread_ports=len(rows),unread_bits=sum(z['bit_count'] for z in rows),strict_binder_equal=True),
        categories=dict(counts),entries=rows)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    (out/'audit.json').write_text(json.dumps(proof,indent=1)+'\n')
    for name,predicate in [('safe_candidates',lambda x:x['allowlist_candidate']),('unresolved',lambda x:not x['allowlist_candidate'])]:
        selected=[z for z in rows if predicate(z)]
        (out/(name+'.json')).write_text(json.dumps(dict(schema=proof['schema'],manifest_adopted=False,entries=selected,bits=sum(z['bit_count'] for z in selected)),indent=1)+'\n')
    print(json.dumps(dict(crosscheck=proof['crosscheck'],categories=proof['categories']),indent=1))

if __name__=='__main__': main()
