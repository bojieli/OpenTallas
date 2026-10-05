"""Retained-image-only padded CROM candidate with explicit invalid L1 hole."""
import argparse,gzip,hashlib,json,subprocess

def sha(b):return hashlib.sha256(b).hexdigest()
def build():
    pins=[]
    def read(ref,path,compressed=False):
        b=subprocess.check_output(['git','show',ref+':'+path]);pins.append(dict(commit=subprocess.check_output(['git','rev-parse',ref]).decode().strip(),path=path,sha256=sha(b)))
        return gzip.decompress(b) if compressed else b
    prefix='results/uarch/w11_dsrom_crom_writer_20261001/'
    v=json.loads(read('70f73928f',prefix+'verification.json'))
    l14=read('60545ff45','results/uarch/w11_engram_product_source_20261001/L14.product.crom64-logical-slice.bin.gz',True)
    assert len(l14)==20480*8 and sha(l14)=='f2297940486c2604a7a4baf8887ed319c264f77cb10ccc3f164c16e01182f377'
    program=json.loads(read('4080bb5fd','results/rtl/w17_connected_token_preparation_20261001/full40_crom_bound_templates_v2.json'))
    ranks=[]
    for rank in range(4):
        image=read('70f73928f',prefix+f'rank{rank}.crom.bin.gz',True)
        assert len(image)==508800*8 and sha(image)==v['rank_images'][rank]['image_sha256']
        banks=[hashlib.sha256() for _ in range(45)]
        valid=[hashlib.sha256() for _ in range(45)]
        # Placeholder bytes NEVER constitute valid L1 parameters. Separate bitmap obligatory.
        padded=image+bytes(20480*8)+l14+bytes(3200*8)
        for a in range(552960):
            bank=(a//3)%45
            banks[bank].update(padded[a*8:a*8+8])
            valid[bank].update(bytes([not 508800<=a<529280]))
        bindings=[]
        for stage in program['ranks'][rank]['stages']:
            if stage['layer'] in (1,14):
                for u in stage['unbound']:
                    if u['operand']=='b' and u['elements']==20480:
                        bindings.append(dict(layer=stage['layer'],instruction=u['instruction'],operand='b',
                            proposed_base=508800 if stage['layer']==1 else 529280,
                            actual_encoded_base=u['actual_base'],source_valid=stage['layer']==14))
        assert len(bindings)==2
        ranks.append(dict(rank=rank,checkpoint_image_sha256=sha(image),bindings=bindings,
            incomplete_placeholder_padded_sha256=sha(padded),
            banks=[dict(bank=i,rows=4096,logical64_slots_per_row=3,bytes=98304,
                placeholder_payload_sha256=banks[i].hexdigest(),byte_per_word_validity_sha256=valid[i].hexdigest()) for i in range(45)],
            complete_image_sha256=None,complete=False))
    return dict(schema='opentallas.CROM-frozen-closure.v1',source_pins=pins,ranks=ranks,
        layout=dict(address_bits=20,old19bit_aperture_fail=True,logical_words=549760,padded_words=552960,
            invalid_source_hole=[508800,529280],L14_span=[529280,549760],padding_span=[549760,552960],
            bank='(a//3)%45',row='(a//3)//45',slot='a%3',physical_home_and_rank_replication=None),
        finite_service=dict(macro_read_ports=45,selected_FP32_outputs_per_fast_cycle=16,
            all_words_delivery_floor_fast_cycles=34360,gamma_words=414720,gamma_floor_fast_cycles=25920,
            gamma_home_words=5120,gamma_home_selected_output_floor_cycles=320,
            burst_capture_max_coefficients=135,burst_drain_cycles=9,
            gamma_cache_coefficients_per_lane=5,lanes=1024,
            instantaneous_1024_lane_gamma_delivery=False,
            actual_routes_capture_mux_CDC_deadlines_and_power_bound=False,
            bound_existing_calendar='47b715428 local11cycle-envelope candidate only; not actual home placement'),
        clock_scope=dict(c01fc4b72='conditional synchronous causal circuit, not24928 asynchronous mailboxes',
            no_provisional_power_minimum=True,
            obligations=['branch selection and fanout','reset and source identity','all-hop drain',
                'actual interdie PHY CDC','actual1.2/.9GHz coefficient CDC','clock-tree contextual SS/FF']),
        owner_work=dict(Fermat=['L1 retained source provenance without new reads','complete padded immutable compiler image and consumer base encoding'],
            Ramanujan=['physical local CROM homes plus selected-port deadline/calendar composition'],
            Avicenna=['synchronous branch/fanout/reset/drain inventory and actual CDC bindings'],
            Confucius=['fresh typed selected phase/data/clock budget after full inventory'],
            Godel=['actual immutable image publication, consumer addresses and finite capture/credit RTL binding']),
        failures=['L1 source absent: complete image impossible with authorized retained inputs',
            'current generated operand bases NULL, proposed bases not encoded programme',
            'physical CROM home/replicas and service deadlines not qualified',
            'synchronous control circuit incomplete and full selected-phase power unclosed'],
        complete_frozen_image=False,hardware_admission=False,full_token_cycles=None,checkpoint_reads=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
