"""Attach a reviewed native FUSED target and its complete status participation."""
import hashlib
import json
import re
from pathlib import Path
from b2_top import seg_width


def parameter(text, name):
    match = re.search(r'\.' + re.escape(name) + r'\(([^()]*)\)', text)
    if not match:
        raise ValueError('missing explicit parameter ' + name)
    return match.group(1)


def replace_parameter(obj, name, value):
    pattern = r'(\.' + re.escape(name) + r'\()[^()]*(\))'
    text, count = re.subn(pattern, lambda match: match.group(1) + str(value) + match.group(2), obj['params'])
    if count != 1:
        raise ValueError('parameter is not unique: ' + name)
    obj['params'] = text


def literal(text):
    if text.isdecimal(): return int(text)
    match = re.fullmatch(r"(\d+)'([bdh])([0-9a-fA-F]+)", text)
    if not match: raise ValueError('unsupported explicit parameter literal: ' + text)
    return int(match.group(3), {'b':2,'d':10,'h':16}[match.group(2)])


def attach(instances, target, audit_path, required, output):
    audit_path = Path(audit_path)
    audit = json.loads(audit_path.read_text())
    if audit.get('candidate') != target or audit.get('verdict') != 'NO_EXISTING_ALLOCATION_OR_DECODE_ALIAS_FOUND' or audit.get('unresolved'):
        raise ValueError('target lacks a complete exact namespace review')
    if not 16 <= target <= 255:
        raise ValueError('native host bootstrap target must be16..255; lower targets are disabled by the host ABI')
    root_name, programme_name, leaf_name = 'u_mu_fused_root', 'u_mu_fused_programme', 'hleaf_NW'
    root, leaf, status, ingress = [instances[name] for name in (root_name,leaf_name,'host_status','host_cp_ingress')]
    if leaf['master'] != 'ot_hbm_host_cfg_leaf2' or status['master'] != 'ot_hbm_status_join_fa' or ingress['master'] != 'ot_hbm_host_static_ingress_obs':
        raise ValueError('actual host interface masters differ from reviewed source')
    nt, nf = literal(parameter(leaf['params'],'NT')), literal(parameter(leaf['params'],'NF'))
    status_nt, status_nf = literal(parameter(status['params'],'NT')), literal(parameter(status['params'],'NF'))
    targets = literal(parameter(status['params'],'TGTS'))
    target_ids = [(targets >> (8 * index)) & 255 for index in range(status_nt)]
    if target in target_ids: raise ValueError('target already participates in status')
    node = dict(clk=leaf['ports']['clk'], rst_n=required(programme_name,'rst_n',1,'Current die-delivered programme reset endpoint/offset is not bound'))
    native_ports = dict(cfg_v=1,cfg_target=8,cfg_addr=12,cfg_data=256,desc_v=1,desc_base=12,desc_limit=13,desc_loops=16,launch_v=1)
    for port, width in native_ports.items():
        source = leaf['ports'].get('a_' + port)
        if not source or source['direction'] != 'output' or source['width'] != width:
            raise ValueError('native host leaf interface differs: a_' + port)
        node[port] = dict(direction='input',segments=[('n',f'{leaf_name}__a_{port}',0,width-1)])
    for port, width in dict(ready=1,active=1,done=1,fault=1,job_v=1,job=217,wsc=8,pk5=6,pb5=1).items():
        node[port] = output(programme_name,port,width)
    for port in ('done','fault','busy'):
        node['root_' + port] = dict(direction='input',segments=[('n',f'{root_name}__{port}',0,0)])
    for port, width in dict(job_v=1,job=217,wsc=8,pk5=6,pb5=1).items():
        root['ports'][port] = dict(direction='input',segments=[('n',f'{programme_name}__{port}',0,width-1)])
    instances[programme_name] = dict(master='ot_hnx_fused_host_program',params=f".TARGET(8'd{target}), .DELIVERED_RESET(1)", ports=node,origin='native_host_bootstrap_contract')
    # Append a real MSB slot to the leaf, preserving all pre-existing status bits.
    for port in ('ready','active','fault'):
        key = 't_' + port
        old_width = nf if port == 'fault' else nt
        if sum(seg_width(segment) for segment in leaf['ports'][key]['segments']) != old_width:
            raise ValueError('existing leaf participation width differs: ' + key)
        leaf['ports'][key]['segments'].append(('n',f'{programme_name}__{port}',0,0))
        spec = leaf['ports']['s_' + port]
        spec['width'] = old_width + 1
        spec['segments'] = [('n',f'{leaf_name}__s_{port}',0,old_width)]
    replace_parameter(leaf,'NT',nt+1)
    replace_parameter(leaf,'NF',nf+1)
    inserted_target_bit = None
    for port in ('ready','active','fault'):
        segments = status['ports']['t_' + port]['segments']
        old_width = nf if port == 'fault' else nt
        offset, found = 0, 0
        for index, segment in enumerate(segments):
            if segment[0] == 'n' and segment[1] == f'{leaf_name}__s_{port}':
                if (segment[2],segment[3]) != (0,old_width-1):
                    raise ValueError('status references a partial/misaligned native leaf')
                segments[index] = ('n',segment[1],0,old_width)
                found += 1
                if port == 'ready': inserted_target_bit = offset + old_width
            offset += seg_width(segment)
        if found != 1: raise ValueError('status leaf participation is not unique')
    if inserted_target_bit is None: raise ValueError('no ready target slot')
    target_ids.insert(inserted_target_bit,target)
    targets = sum(value << (8*index) for index,value in enumerate(target_ids))
    replace_parameter(status,'TGTS',f"{8*(status_nt+1)}'h{targets:x}")
    replace_parameter(status,'NT',status_nt+1)
    replace_parameter(status,'NF',status_nf+1)
    mask = literal(parameter(ingress['params'],'TARGET_MASK'))
    replace_parameter(ingress,'TARGET_MASK',f"256'h{mask | (1 << target):064x}")
    return dict(target=target,namespace_audit_sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        native_leaf=leaf_name,leaf_nt_before=nt,leaf_nt_after=nt+1,leaf_nf_before=nf,leaf_nf_after=nf+1,
        status_nt_before=status_nt,status_nt_after=status_nt+1,status_nf_before=status_nf,status_nf_after=status_nf+1,
        inserted_status_target_bit=inserted_target_bit,status_targets_lsb_first=target_ids,
        source_contract='ot_hnx_fused_host_program from bootstrap component gate; source pin/RTL closure must be supplied separately',
        production_programme='MISSING_CURRENT_CALENDAR_HEADER_COMPILATION',
        reset_authority='MISSING_CURRENT_DIE_DELIVERED_PROGRAMME_RESET',
        scope='Native byte ABI and status participation only; no production job, calendar, reset wavefront or physical admission')
