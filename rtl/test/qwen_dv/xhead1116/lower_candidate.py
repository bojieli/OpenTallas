exec(open(__file__.replace('lower_candidate.py','gen_packets.py')).read().split('meta={}')[0])
r=json.loads((P/'calibrated.json').read_text())['consumer']
a={'schema':'opentallas.qwen.dv-xhead-ages.v1','status':'CANDIDATE_PENDING_SELECTED_LEAF_REPLAY','slice_rtl':'s8','source_scope':'native_zero_parent_transport','x_tap':0,'d_head':21,'read_tail':-6,'go_lag':-3,'xpf_lead':4,'consumer':{k:{'go_lag':v['go_lag']-1,'xpf_lead':v['xpf_lead']+1} for k,v in r.items()},'boundary':'coupon hr_q is after nativeFDN1; compiler slicehr input precedes FDN1; producer xt pin receiver origin'}
(P/'xhead_ages_candidate.json').write_text(json.dumps(a,indent=2)+'\n')
lw=X.lower_layer(comp,a)
(P/'lowered_candidate.json').write_text(json.dumps(lw,indent=2)+'\n')
print('ERRORS',lw['errors']);print('consumers',[(x['matvec'],x['xpf_w5'],x['go_w5'],x['go_delay'],x['xpf_window']) for x in lw['consumers']]);print('notes',lw['notes']);print('hr_at',lw['hr_arrival'])
