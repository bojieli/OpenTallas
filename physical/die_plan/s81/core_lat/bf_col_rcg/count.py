import json,sys,collections
M=json.load(open(sys.argv[1]))['modules']; d=M['ot_v41_bf_col']
def mbits(m):  # flop bits inside a kept submodule (single clock 'clk')
    return sum(int(c['parameters'].get('WIDTH','1'),2) for c in M[m]['cells'].values() if c['type'].startswith('$') and 'dff' in c['type'].lower())
drv={}
for n,c in d['cells'].items():
    for p,bits in c['connections'].items():
        if p in ('Q','Y','GCLK','q','rd_out') or c.get('port_directions',{}).get(p)=='output':
            for b in bits: drv[b]=n
for p,v in d['ports'].items():
    if v['direction']=='input':
        for b in v['bits']: drv[b]='PORT:'+p
cnt=collections.Counter(); mac=collections.Counter(); icg={}
for n,c in d['cells'].items():
    t=c['type']
    if t in M and 'ot_v41_kreg' in t:
        cnt[drv.get(c['connections']['clk'][0],'?')]+=mbits(t)
    elif t.startswith('$') and 'dff' in t.lower():
        cnt[drv.get(c['connections']['CLK'][0],'?')]+=int(c['parameters'].get('WIDTH','1'),2)
    elif False:
        cnt[drv.get(c['connections']['clk'][0],'?')]+=mbits(t)
    elif t.startswith('ot_rom'):
        mac[drv.get(c['connections']['clk'][0],'?')]+=1
    elif t=='ICGx1_ASAP7_75t_R':
        icg[n]={'clk_from':drv.get(c['connections']['CLK'][0],'?'),'ena_from':drv.get(c['connections']['ENA'][0],'?')}
out={'flops_by_clock_driver':dict(cnt.most_common()),'macros_by_clock_driver':dict(mac),'icg':icg,'total_flop_bits':sum(cnt.values())}
json.dump(out,open(sys.argv[2],'w'),indent=1); print(json.dumps({k:out[k] for k in ('flops_by_clock_driver','macros_by_clock_driver','total_flop_bits')},indent=0)[:3000])
print(set((v['clk_from']) for v in icg.values()))
