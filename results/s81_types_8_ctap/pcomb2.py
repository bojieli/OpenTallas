import json,hashlib,sys
W='/srv/opentallas-scratch3/claude/kw34/wave_cg_frz_xrt/physical/die_plan/s81/'
base=json.load(open(W+'plan_h2_2249.json'))
src={'ctap':'/srv/opentallas-scratch2/claude/s81-types-8/ctap/wave_out_v4.json',
     'colh':'/srv/opentallas-scratch3/claude/s81-types-8-colh/wave_cg_frz_xrt_wge/physical/die_plan/s81/plan_h2_2249.json',
     'ts1':W+'plan_h2_2249_ts1.json'}
out=json.loads(json.dumps(base)); prov={}
bp=base['partition_types']
for n,f in src.items():
    o=json.load(open(f))
    for k in o: 
        if k!='partition_types': assert o[k]==base[k],(n,k)
    for t,v in o['partition_types'].items():
        if v==bp[t]: continue
        if n=='ts1':
            # ts1 only adds clock.tap_pair_affinity (empty); add key, keep everything else
            d={kk:vv for kk,vv in v.items() if kk!='clock'}; assert d=={kk:vv for kk,vv in bp[t].items() if kk!='clock'},t
            c={kk:vv for kk,vv in v['clock'].items() if kk!='tap_pair_affinity'}; assert c==bp[t]['clock'],t
            out['partition_types'][t]['clock']['tap_pair_affinity']=v['clock']['tap_pair_affinity']
        else:
            assert t not in prov,(t,prov.get(t),n)
            out['partition_types'][t]=json.loads(json.dumps(v)); prov[t]=n
    print(n,"applied")
# t36: leafb tap superseded by ctap re-site (ctap includes leafb)
out['note']=base['note']+' | S81-TYPES-8 combined 11-08: wave ba6292b0c502 + ctap v4 153ffcc4ce90 (CTAP + LEAFB + budget moves, 75 leaf types) + colh 4e2f79c8bed7 (13 col_h) + ts1 7e9695ef5896 (tap_pair_affinity key).'
p='plan_h2_2249_comb2.json'
json.dump(out,open(p,'w'),indent=1)
print(hashlib.sha256(open(p,'rb').read()).hexdigest()[:12], {n:sum(1 for v in prov.values() if v==n) for n in src})
json.dump(prov,open('comb_prov.json','w'),indent=1)
