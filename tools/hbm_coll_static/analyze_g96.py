#!/usr/bin/env python3
"""Quantify schedule causes without guessing actual FEC/board flight."""
import argparse,collections,json,pathlib
p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
v=json.loads((a.directory/'calendar.json').read_text());pubs=v['publications'];adds=v['arithmetic'];hops=v['transport_hops'];last=max(v['broadcasts'],key=lambda x:x['last_delivery'])
slack=[e['read']-e['write']-4 for e in hops];assert min(slack)>=0
root_pubs=[p for p in pubs if p['bf16']]
report={'cycles':v['cycles'],'immutable_price':1325.9,'ratio':v['cycles']/1325.9,'arithmetic_last_safe_read':max(x['issue']+9 for x in adds),'first_BF16_pub_issue':min(p['issue'] for p in root_pubs),'last_BF16_pub_issue':max(p['issue'] for p in root_pubs),'critical_multicast':last,'critical_multicast_pub_to_final_delivery':last['last_delivery']-last['pub_issue'],'native_link_read_after_write':{'minimum_required':4,'additional_slack_min':min(slack),'additional_slack_max':max(slack),'additional_slack_sum_over_hops':sum(slack),'nonzero_hops':sum(s>0 for s in slack)},'physical_flight':'Each endpoint follows actual TX5/RX1 and613/487 reservations, but current three-word flight is a component bench assumption; actual full FEC/clock/board latency unbound. Do not attribute modeled flight to qualified physical ports.','interpretation':'Additional link slack includes rational frame alignment, occupied reservations and native write/read sequence ordering. It is scheduler/resource overhead, not extra physical FEC flight. Critical multicast includes actual qslot and registered quarter bridge stages when present.'}
(a.directory/'cause_analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
