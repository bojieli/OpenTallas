"""Private dead-forwarded-clock wiring event; never edits the plan of record."""
import copy,json,re,sys
from pathlib import Path
OLD={'fhN':16,'piN':289,'piN_d1':289,'piN_d2':289,'piN_d3':289,'rhN':16}
DEAD={'fhN':set(range(4)),'piN':set(range(277,285)),'piN_d1':set(range(285,289)),'piN_d2':set(range(4)),'piN_d3':set(range(4,12)),'rhN':set(range(12,16))}
NEW={k:w-len(DEAD[k]) for k,w in OLD.items()}
RULE={'pin':r'phy_(?:EN|ES|WN|WS)(?:\.u_sub)?\.u_s[0-7]\.(?:fh|rh)[0-3]','domain':'core'}
def transform(plan,asbuilt):
    before=copy.deepcopy(plan);p=copy.deepcopy(plan);ab=copy.deepcopy(asbuilt)
    types=p['partition_types'];parts={x['name']:x['type'] for x in p['partitions']}
    changed=set();bus_count=0
    for tn,t in types.items():
        phy=tn in ('kv3_phy','kv3_phy_v1');pc=tn.startswith('kv3_pc')
        if not (phy or pc):continue
        prefix='o_phy_Q__sN_' if phy else 'i_phy_Q__sN_'
        seen=set()
        for bus in t['buses']:
            if not bus['name'].startswith(prefix):continue
            key=bus['name'][len(prefix):]
            if key not in OLD:continue
            assert bus['width']==OLD[key],(tn,key,bus['width'])
            bus['width']=NEW[key];seen.add(key);bus_count+=1
        assert seen==set(OLD),(tn,seen)
        changed.add(tn)
        # Physical homes of surviving face flops follow their compacted bit.
        homes=t.get('relay_sites',{});remap={}
        pattern=re.compile(r'u_(bin|bout)_(?:i|o)_phy_Q__sN_(fhN|piN|piN_d1|piN_d2|piN_d3|rhN)/q\[(\d+)\]')
        for name,xy in homes.items():
            m=pattern.fullmatch(name)
            if not m:remap[name]=xy;continue
            key,bit=m[2],int(m[3])
            if bit in DEAD[key]:continue
            index=sum(i not in DEAD[key] for i in range(bit))
            remap[name[:name.rfind('[')]+f'[{index}]']=xy
        if homes:t['relay_sites']=remap
    assert len(changed)==8,(len(changed),changed)
    crossings=0;removed=0
    for port in p['ports']:
        sp=port['src'];dp=port['dst']
        if parts[sp['part']] not in ('kv3_phy','kv3_phy_v1'):continue
        prefix='o_phy_Q__sN_'
        if not sp['bus'].startswith(prefix):continue
        key=sp['bus'][len(prefix):]
        if key not in OLD:continue
        assert parts[dp['part']].startswith('kv3_pc')
        assert dp['bus']=='i_phy_Q__sN_'+key
        assert port['width']==OLD[key]
        port['width']=NEW[key];crossings+=1;removed+=len(DEAD[key])
    assert crossings==192 and removed==1024,(crossings,removed)
    ab.setdefault('clocks',[]).append(RULE)
    # Existing native consumers already use the declared core clock. The rule
    # classifies only the redundant forwarded copies, not payload pi outputs.
    assert p['latency']==before['latency']
    for tn in types:
        if tn not in changed:assert p['partition_types'][tn]==before['partition_types'][tn]
    for key in p:
        if key not in ('partition_types','ports'):assert p[key]==before[key],key
    report={'changed_types':sorted(changed),'changed_type_buses':bus_count,'changed_crossings':crossings,'removed_wire_bits':removed,'removed_face_flops':2*removed,'data_cycle_delta':0,'reset_cycle_delta':0,'native_clock_rule':RULE,'old_bus_widths':OLD,'new_bus_widths':NEW,'dead_bits':{k:sorted(v)for k,v in DEAD.items()},'verdict':'PRIVATE_DRAFT_NEEDS_STRICT_BIND_AND_LIVE_OPERAND_MITER'}
    return p,ab,report
def prune_clock_r8(table):
    rule=re.compile(RULE['pin'])
    removed=[m for m in table['members']if rule.fullmatch(m['source'])]
    assert len(removed)==256,len(removed)
    bits=sum(hi-lo+1 for m in removed for lo,hi in m['sink_bits'])
    assert bits==1024,bits
    assert all(m['pad']==0 for m in removed),'dead clock unexpectedly has a data pad'
    assert {m['sink_port']for m in removed}=={'pc__front_hbm_data','pc__return_hbm_data'}
    fixed=copy.deepcopy(table)
    fixed['members']=[m for m in fixed['members']if not rule.fullmatch(m['source'])]
    assert len(fixed['members'])+len(removed)==len(table['members'])
    fixed['source_summary']=fixed.pop('summary',{})
    fixed['summary']={'members':len(fixed['members']),'padded_members':sum(bool(m['pad'])for m in fixed['members']),'padded_bits':sum(sum(hi-lo+1 for lo,hi in m['sink_bits'])for m in fixed['members']if m['pad']),'pad_flops':sum(m['pad']*sum(hi-lo+1 for lo,hi in m['sink_bits'])for m in fixed['members'])}
    fixed['dead_clock_removal']={'rows':len(removed),'bits':bits,'pad_flops_removed':0,'rule':RULE,'reason':'declared forwarded clocks are not data crossings; every surviving R8 member and pad unchanged'}
    return fixed,removed
if __name__=='__main__':
    a,b,o=sys.argv[1:4];out=Path(o);out.mkdir(parents=True,exist_ok=True)
    p,ab,r=transform(json.load(open(a)),json.load(open(b)))
    source=Path(ab['land_r8'])
    if not source.is_absolute():source=Path(ab['base'])/source
    fixed,removed=prune_clock_r8(json.load(open(source)))
    if len(sys.argv)>4:
        import hashlib
        bg=json.load(open(sys.argv[4]))
        fixed['source_bus_groups_digest']=fixed.get('bus_groups_digest')
        fixed['bus_groups_digest']=hashlib.sha256(json.dumps(bg,sort_keys=True).encode()).hexdigest()[:16]
    r8out=out/'r8_no_dead_forwarded_clocks.json';r8out.write_text(json.dumps(fixed,indent=1))
    ab['land_r8']=str(r8out)
    r['r8_removed_clock_rows']=len(removed);r['r8_removed_clock_bits']=1024
    (out/'removed_clock_r8_members.json').write_text(json.dumps(removed,indent=1))
    (out/'plan_c.json').write_text(json.dumps(p,indent=1))
    (out/'asbuilt.json').write_text(json.dumps(ab,indent=1))
    (out/'event_report.json').write_text(json.dumps(r,indent=1))
    print(json.dumps(r))
