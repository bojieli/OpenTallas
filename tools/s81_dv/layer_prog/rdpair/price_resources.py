"""Apply measured minimum-cut port costs to the complete proposed route map.

No propagation/clock/host/native or unsupported transport admission is inferred.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


def price(model):
    shared_lo=Counter();source_commands=Counter();v_reference=Counter()
    tier_commands=Counter({f'rank{r}/tier{t}':50 for r in range(4) for t in range(2)})
    for packet in model['local']+model['peers']:
        for leg in packet['legs']:
            rank=leg.get('rank',leg.get('source_rank'))
            key=f'rank{rank}/sid{leg["source"]}'
            shared_lo[key]+=leg['pairs']
            source_commands[key]+=2
            tier_commands[f'rank{rank}/tier{leg["source"]%2}']+=2
            if leg['kind']=='typed_v_pair_candidate':
                if leg['pairs'] not in (2,4):raise ValueError('unmeasured V packet shape')
                v_reference[key]+=leg['pairs']+1
    if sum(shared_lo.values())!=16960:raise ValueError('changed complete route read inventory')
    return dict(schema='opentallas.s81.rd_pair.resource_binding.v1',admitted=False,
                shared_XR_lo_pair_slots=dict(sorted(shared_lo.items())),
                shared_XR_lo_bandwidth_only_floor=max(shared_lo.values()),
                uncoalesced_source_CTL_occurrences=dict(sorted(source_commands.items())),
                uncoalesced_tier_CTL_occurrences_including_80combine_320POST=dict(sorted(tier_commands.items())),
                uncoalesced_V_reference_period_edges=dict(sorted(v_reference.items())),
                uncoalesced_V_reference_busiest_edges=max(v_reference.values()),
                measurements=dict(np4_period=5,np4_pairs=256,np4_write_span=319,np4_startup_inclusive_span=340,
                                  np2_period=3,np2_pairs=128,np2_write_span=191,np2_startup_inclusive_span=212),
                original_V_payload_only_floor=520,full_token_delta=None,actual_peer_POST_arrival=None,
                qualifications=['shared lo floor counts all five leaves sharing XR nlo0 selector',
                    'tier commands and V periods price this uncoalesced reference, not universal lower bounds',
                    'broadcast command coalescing may change control counts but needs actual collision/lifetime proof',
                    'measured periods omit DL4, actual V landing/native and host/PHY',
                    '883 unlanded horizontal traversals, SAFE control/reset and all real leases remain open'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--model',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();raw=a.model.read_bytes()
    if raw[:2]==b'\x1f\x8b':raw=gzip.decompress(raw)
    r=price(json.loads(raw));r['complete_model_sha256']=hashlib.sha256(raw).hexdigest()
    a.out.write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps({k:r[k] for k in ('shared_XR_lo_bandwidth_only_floor','uncoalesced_V_reference_busiest_edges','admitted')}))
if __name__=='__main__':main()
