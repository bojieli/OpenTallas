"""Map the actual 256 HCOL + 8 tails onto existing plan instances.

Usage: scorer_exact_map.py INVENTORY BASE_MAP OUTPUT_MAP OUTPUT_PACKET
Residual prefixes are proposals, kept separate until physical soft placement is adopted.
"""
import collections,json,re,sys
from pathlib import Path

inventory,base,out,packet=map(Path,sys.argv[1:])
d=json.loads(inventory.read_text()); m=json.loads(base.read_text())
actual={x['path']:x for x in d['actual_leaves']}
rows=[]; rules=[]; chunks=collections.defaultdict(list); tails={}
for h in d['planned']:
    match=re.fullmatch(r'u_hb_idx__s_(Q2|Q)_(?:r(\d)c(\d)_k(\d)h(\d)|tail(\d))',h['inst'])
    assert match,h
    q,r,c,k,half,tail=match.groups()
    hub=h['partition'][:2]
    role=({'NW':'SW','NE':'SE'}[hub] if q=='Q2' else hub)
    pre=f'hb_idx__s_{role}.scorer'
    if tail is not None:
        path=f'{pre}.ge[{tail}].u_t'; master='ot_hbm_idx_tail_native'
        assert actual[path]['module']==master
        assert actual[path]['params']=={'DELIVERED_RESET':'1'},actual[path]
        tails.setdefault(role,[]).append(h['partition'])
    else:
        path=f'{pre}.ge[{r}].gc[{c}].leaf.core.g_col[{k}].g_half[{half}].u_hc'
        a=actual[path];assert a['module']=='ot_hidx_score_hcol'
        assert a['params']=={'DELIVERED_RESET':'1','HALF':half,'MUT':'0'},a
        master=f'ot_hbm_idx_score_hcol_h{half}'
        rule=dict(inst=re.escape(path),module=master,reason='Exact HALF specialization; source DELIVERED_RESET=1 preserved, no added cycle')
        if half=='0':
            assert a['identity_source']['cs_in']==['0']*32 and a['identity_source']['cf_in']==['0']
            rule['port_bit_constants']={p:{str(i):'0' for i in range(n)} for p,n in [('cs_in',32),('cf_in',1)]}
        rules.append(rule)
        chunks[(role,int(r),int(c))].append(h['partition'])
    m['parts'][path]=[h['partition'],h['inst']]
    rows.append(dict(source_path=path,partition=h['partition'],plan_inst=h['inst'],module=master,
                     params=dict(MUT=0,DELIVERED_RESET=1) if tail is None else dict(DELIVERED_RESET=1),
                     previous_module=h['module'],pin_change='remove cs_in[31:0],cf_in only' if half=='0' else 'rename extracted tail ports to actual i_*/o_*; clk_tail to clk' if tail is not None else 'none'))
assert len(rows)==264 and len(rules)==256
residual=[]
for (role,r,c),parts in sorted(chunks.items()):
    hist=collections.Counter(parts); anchor=hist.most_common(1)[0][0]
    residual.append(dict(prefix=f'hb_idx__s_{role}.scorer.ge[{r}].gc[{c}]',candidate_partition=anchor,child_partition_counts=dict(hist),status='SOFT_PLACEMENT_REQUIRED'))
for role,parts in sorted(tails.items()):
    assert len(set(parts))==1
    residual.append(dict(prefix=f'hb_idx__s_{role}',candidate_partition=parts[0],status='SOFT_PLACEMENT_REQUIRED',note='fallback for quarter/row glue; keybuf and all exact child paths override this prefix'))
p=dict(schema='opentallas.hbm.scorer_exact_map.v1',exact_children=rows,substitute_inst=rules,
       residual_proposals=residual,added_cycles=0,h0_removed_seed_bits=128*33,
       hid4='Actual timed nets, not static straps. Preserve source launch registers and all 8192 bits.',
       tail_pin_rename={'clk_tail':'clk','ge_E_u_t_PORT':'PORT'},
       note='No whole-quarter hard core; no additional source arithmetic. Residual proposals are not applied to map until physical lane adopts their locations/cuts.')
out.write_text(json.dumps(m,indent=1)+'\n');packet.write_text(json.dumps(p,indent=2)+'\n')
print('exact264, HCOL256, H0seed4224bits, residual proposals',len(residual))
