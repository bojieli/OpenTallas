"""Released DSpark Markov row sizing, before RTL. No physical or rate credit."""
import math

def model(k=256, vocab=129280, sk=11):
    assert k >= 16 and k % 16 == 0 and not (k//16 & (k//16-1))
    words=k//16
    levels=int(math.log2(words))
    latency=6+(9+levels+1)*sk+3
    return dict(schema='opentallas.dsrom.markov-row.v1',default_enabled=False,adopted=False,
        shape=dict(vocab=vocab,k=k,source='released mtp.2.markov_head.{head,embed}.weight safetensors headers'),
        arithmetic='BF16 exact products; each contiguous8 summed sequentially from+0; pairwise tree; separate add(lm_head,markov)',
        MACs_per_cycle=16,compute_intensity_macs_per_weight_byte=0.5,
        ports_bytes_per_cycle=dict(weights=32,embedding=32,head_logit=4,result=4),
        boundary_bits_per_cycle=dict(weights=256,embedding=256,control=2,head_logit=32,result=32),
        replicas=dict(row_engine=1,multipliers=16,chunk_adders=16,tree_adders=1+levels,join_adders=1),
        fanout=dict(clock_loads='measure synthesis',embedding_lanes=16,token_broadcast='129280-row bounds check; identity required'),
        routing=dict(input_tracks=546,output_tracks=33,capacity='requires actual slot and pin plan before route'),
        storage=dict(embed_bytes=vocab*k*2,head_bytes=vocab*k*2,head_pair_payload_bytes=8192*32,
                     embed_head_pairs=math.ceil(vocab*k*2/(8192*32))),
        area=dict(product_delay_bits=2*sum(range(8))*sk*32,
                  floorplan_slot='new dedicated engine; no existing closed view qualifies it'),
        latency=dict(first_beat_to_join_cycles_upper=words+latency,last_beat_to_join_cycles_upper=latency,
                     words_per_row=words,minimum_transaction_II_upper=words+latency+2,
                     five_sweeps_compute_ratio=k/5120,previous_reduced_ratio=32/4096,
                     claimed_54_6ns_budget_met=False),
        qualified=False,open=['ROM embed port','head row ROM allocation','full head element integration','exactness','TT/FF physical admission'])

if __name__=='__main__':
    import json
    print(json.dumps(model(),indent=2))
