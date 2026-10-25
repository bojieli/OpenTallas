"""Derive KV pre-START reset classes from actual boot ACK and config paths."""
import argparse,json,re,collections
from pathlib import Path
import schema


def derive(plan,bound,source):
    names=json.loads((bound/'bind_names.json').read_text())
    owner={v:k.split('.',1)[0] for k,v in names.items()}
    if len(owner)!=len(names):raise ValueError('ambiguous native instance owner')
    sinks=json.loads((bound/'bind_sinks.json').read_text())
    buses=json.loads((bound/'bind_latency.json').read_text())['buses']
    ctl=(source/'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_ctl_nc32.sv').read_text()
    aliases={int(n):(port,int(bit))for n,port,bit in re.findall(r'bobs__applied_hbm__(\d+)\s*=\s*(i_hroot_\w+)\[(\d+):\d+\]',ctl)}
    if set(aliases)!=set(range(160)):raise ValueError('expected all160 explicit boot ACK aliases')
    if '.sink_applied(w_bobs__applied_core[159:0])' not in ctl:raise ValueError('boot dispatcher ACK contract changed')
    tiles=(source/'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_nc32.sv').read_text()
    group=re.search(r'module\s+qkd_kvs_grp\b(.*?)endmodule',tiles,re.S).group(1)
    local=re.search(r'assign\s+o_ctl\s*=\s*\{i_up\[125:0\],\s*\{([^{}]+)\}\}',group).group(1)
    status=[x.strip() for x in local.split(',')][::-1]
    expected=[f'w_bcdc{k}__{field}' for k in range(4) for field in ('applied_hbm','fault_core','fault_hbm')]
    expected += ['w_bcdcf__applied_hbm','w_bcdcf__fault_core','w_bcdcf__fault_hbm','w_cf1__fault','w_drain__drained','w_drain__fault']
    if status!=expected:raise ValueError('group local boot ACK field positions changed')
    hroot=tiles.split('module qkd_kvs_hroot',1)[1]
    expr=re.search(r'assign\s+o_ctl\s*=\s*\{([^;]+)\};',hroot).group(1)
    chunks=re.findall(r'w_rly__g\[(\d+):(\d+)\]',expr)
    remnant=re.sub(r'w_rly__g\[\d+:\d+\]|[\s,]','',expr)
    if remnant:raise ValueError('unsupported HROOT ACK permutation')
    perm=[bit for hi,lo in reversed(chunks)for bit in range(int(lo),int(hi)+1)]
    if sorted(perm)!=list(range(144)):raise ValueError('HROOT ACK permutation not bijective')
    r2c=(source/'physical/die_plan/qwen_kvsys/bind/kv45/group_r2c_native.sv').read_text()
    if 'u0 <= i_up[125:0]' not in r2c or 'assign o_ctl = {up_q, own_q}' not in r2c:raise ValueError('group ACK shift contract changed')
    part_reasons=collections.defaultdict(set)
    ack=[]
    def follow(key):
        v=sinks[key]
        if v[0]!='pin':raise ValueError('nonphysical boot ACK source '+key+':'+str(v))
        return v[1]
    def pin_split(pin):
        m=re.fullmatch(r'(.+)\.(\w+)\[(\d+)\]',pin)
        if not m:raise ValueError('non-scalar ACK source '+pin)
        return m.group(1),m.group(2),int(m.group(3))
    for n,(port,bit) in sorted(aliases.items()):
        root,rootport,rootbit=pin_split(follow(f'kvs_ctl.{port}[{bit}]'))
        if rootport!='o_ctl':raise ValueError('unexpected root ACK port')
        current=follow(f'{root}.i_g[{perm[rootbit]}]');chain=[owner['kvs_ctl'],owner[root]]
        while True:
            cell,p,b=pin_split(current)
            if p!='o_ctl':raise ValueError('unexpected group ACK port')
            chain.append(owner[cell])
            if b<18:break
            current=follow(f'{cell}.i_up[{b-18}]')
            if len(chain)>12:raise ValueError('ACK shift cycle')
        if b not in (0,3,6,9,12):raise ValueError('ACK points at fault/drain bit')
        for part in chain:part_reasons[part].add('boot ACK return path')
        ack.append(dict(index=n,ctl_pin=f'{port}[{bit}]',native_endpoint=f'{cell}.o_ctl[{b}]',status_field=('bcdc'+str(b//3) if b<12 else 'bcdcf')+'.applied_hbm',part=owner[cell],chain=chain))
    unique={(x['part'],x['native_endpoint'])for x in ack}
    if len(unique)!=160:raise ValueError(f'ACKs alias only{len(unique)} physical boot sinks')
    P=schema.Plan(plan)
    # External SerDes carries boot/program replay before mission admission.
    # Select its exact declared IP and native bound identity, not partition names.
    ip_parts={part for part,p in P.parts.items() if any(c.get('module')=='ot_qfd_serdes_112g_x6_phy' for c in P.types[p['type']].get('contents',[]))}
    for part in ip_parts:
        native=[v for k,v in names.items() if k.startswith(part+'.')]
        if not native or any(not x.startswith('serdes_host.u_sub.') for x in native):
            raise ValueError('SerDes bootstrap identity changed '+part)
        part_reasons[part].add('external SerDes boot/program replay: '+','.join(native))
    selected=[]
    # These are concrete protocol fields, selected from actual bound leaves;
    # they are not guesses based on partition/type names.
    def boot_field(leaf):
        pin=re.sub(r'\[\d+\]$','',leaf)
        return (re.fullmatch(r'host\.(boot_go|boot_pr|hbm_rst_n|host_rst_n|die_rst_n|boot_image_(digest|epoch|fault|ready|target))',pin)
          or re.fullmatch(r'kvs_ctl\.(boot__link_cfg_(addr|data|rx_we|tx_we)|boot__setup_ready|dcfg__age_vport__\d+_\d+|o_hroot_(EN|ES|WN|WS))',pin)
          or re.fullmatch(r'kvs_hroot_(EN|ES|WN|WS)\.(o_c[0-7]|o_ch[0-7]|o_pc|o_ctl)',pin)
          or re.fullmatch(r'slg_(EN|ES|WN|WS)_\d+\.o_ctl',pin))
    families={re.sub(r'_d[0-9]+$','',bus['bus_out']) for bus in buses if any(boot_field(x)for x in bus.get('leaves',[]))}
    for lane in P.lanes.values():
        src=P.ports[lane['ports'][0]]['src'];dst=P.ports[lane['ports'][-1]]['dst']
        if src['part'] in ip_parts or dst['part'] in ip_parts:
            families.add(re.sub(r'_d[0-9]+$','',src['bus']))
    by_lane={bus['lane']:bus for bus in buses}
    for lid,lane in P.lanes.items():
        first=P.ports[lane['ports'][0]]['src'];last=P.ports[lane['ports'][-1]]['dst']
        if re.sub(r'_d[0-9]+$','',first['bus']) not in families:continue
        bus=by_lane.get(lid,dict(lane=lid,src=first['part'],dst=last['part'],bus_out=first['bus'],leaves=[]))
        lid=bus['lane']
        if lid not in P.lanes:raise ValueError('new plan lacks bound boot lane '+lid)
        lane=P.lanes[lid]
        ports=[P.ports[x]for x in lane['ports']]
        parts={side['part']for port in ports for side in(port['src'],port['dst'])if side['part']!='@die'}
        if bus['src'] not in parts or bus['dst'] not in parts:raise ValueError('boot lane endpoint changed '+lid)
        for part in parts:part_reasons[part].add('boot transport '+lid)
        selected.append(dict(lane=lid,src=bus['src'],dst=bus['dst'],native_fields=bus['leaves'],parts=sorted(parts)))
    types=collections.defaultdict(set)
    for part,reason in part_reasons.items():types[P.parts[part]['type']]|=reason
    patch={tn:'bootstrap'for tn in sorted(types)if not P.types[tn].get('hard')}
    expanded=[p for p,t in P.parts.items()if t['type']in patch]
    return dict(ack_count=len(ack),unique_ack_endpoints=len(unique),ack_endpoints=ack,bootstrap_types=patch,
      type_evidence={t:sorted(types[t])for t in patch},bootstrap_parts=sorted(expanded),explicit_parts={p:sorted(r)for p,r in part_reasons.items()},boot_lanes=selected,
      note='Uniform type closure of actual boot configuration and ACK transit paths. HOST admission separately gates on one local registered START. No raw die reset bypass or added data cycles.')

def apply_roles(plan,audit,start_port='mission_start_global'):
    import copy
    result=copy.deepcopy(plan)
    for tn,role in audit['bootstrap_types'].items():
        if tn not in result['partition_types']:
            raise ValueError('audited type missing from target plan '+tn)
        cfg=result['partition_types'][tn].setdefault('reset',{})
        if any(v=='mission' for v in cfg.get('core_start_roles',{}).values()):
            raise ValueError('mission core conflicts with bootstrap protocol '+tn)
        cfg['start_role']=role
    result.setdefault('reset',{}).update(start='broadcast',start_port=start_port)
    return result


def check_roles(plan,audit):
    missing=[tn for tn in audit['bootstrap_types'] if plan['partition_types'][tn].get('reset',{}).get('start_role','mission')!='bootstrap']
    if missing:raise ValueError('boot configuration/ACK path held until START: '+','.join(missing))
    if plan.get('reset',{}).get('start')!='broadcast' or not plan['reset'].get('start_port'):
        raise ValueError('one explicit HOST mission START port required')
    return True

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('plan',type=Path);ap.add_argument('bound',type=Path);ap.add_argument('source',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--apply-out',type=Path);a=ap.parse_args()
    raw=json.loads(a.plan.read_text());result=derive(raw,a.bound,a.source);
    if a.apply_out:
        updated=apply_roles(raw,result);check_roles(updated,result);a.apply_out.write_text(json.dumps(updated,separators=(',',':'))+'\n')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(dict(acks=result['ack_count'],unique=result['unique_ack_endpoints'],types=len(result['bootstrap_types']),parts=len(result['bootstrap_parts']),lanes=len(result['boot_lanes']))))
