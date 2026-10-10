"""ATT unit physical partition inventory, before a sector-stager build."""
import json


def model(H=16, D=512, TD=64, NL=2, BLK=512, density=0.55):
    assert D % TD == 0 and TD % H == 0
    nt = NL * D // TD
    dpt = D // nt
    pb = max(8, TD // H)
    engine = dict(q=D*16, kv=NL*(D//32)*265, p=TD*16,
                  score=NL*H*32, pv=nt*H*32)
    # Each bank's actual single write and combinational read contract must be
    # represented by its SRAM view; nothing is replaced with an ideal wire.
    memory = {
        'Q': dict(banks=8, depth=D//8, word_bits=16,
                  write_ports_per_bank=1, read='all depth words simultaneously'),
        'P': dict(banks=H*pb, depth=BLK//pb, word_bits=16,
                  write_ports_per_bank=1, read_ports_per_bank=1),
        'codes': dict(banks=32, depth=D//32, word_bits=8,
                      write_ports_per_bank=1, read='all depth words simultaneously'),
        'cur': dict(banks=nt*H, depth=dpt, word_bits=32,
                    write_ports_per_bank=1, read_ports_per_bank=1),
        'merge': dict(banks=1, depth=4*H*D, word_bits=32,
                      write_ports_per_bank=1, read_ports_per_bank=1),
        'scores': dict(banks=1, depth=32, word_bits=NL*H*32+16+NL,
                       write_ports_per_bank=1, read_ports_per_bank=1),
        'add_dest': dict(banks=1, depth=64, word_bits=14,
                         write_ports_per_bank=1, read_ports_per_bank=1),
    }
    for v in memory.values():
        v['storage_bits'] = v['banks']*v['depth']*v['word_bits']
        v['physical_view_qualified'] = False
    # One sector is converted at a time, exactly 32 FP8 /16 BF16 /8 FP32
    # values. Static output lanes avoid a dynamic multi-write memory.
    inputs = 256+8+2+1+2
    outputs = 256+32+32+8+1
    pins = inputs+outputs
    side = 320
    perimeter = 4*(side-2*10.8)
    return dict(source='rtl/hbm_accel/generic/peers/ot_hgi_att_unit.sv',
        shape=dict(H=H,D=D,TD=TD,NL=NL,BLK=BLK,engine_tiles=nt),
        clock=dict(domain='streaming',frequency_GHz=1.2,period_ps=833.333,
                   setup_uncertainty_ps=60,hold_uncertainty_ps=25,
                   headline_requires='SS setup and FF hold; TT pathfinding only'),
        engine_boundary_bits=engine,engine_payload_bits=sum(engine.values()),
        memory=memory,storage_bits=sum(v['storage_bits'] for v in memory.values()),
        sector_codec=dict(replicas=1,macs_per_cycle=0,
            input_bytes_per_cycle=32,output_bytes_per_cycle=32,
            useful_output_values=dict(FP8=32,BF16=16,FP32=8),
            inputs_bits=inputs,outputs_bits=outputs,total_pins=pins,
            routing_tracks=pins,pin_density_per_um=density,
            slot_side_um=side,usable_perimeter_um=perimeter,
            perimeter_capacity_pins=int(perimeter*density),
            pin_capacity_fits=pins<=perimeter*density,
            register_bits_upper_bound=inputs+outputs,
            area_um2=None,area_status='await mapped synthesis; no guessed fit claim',
            mux_demux='static lane select by format/tag; 32 code bank write masks',
            added_pipeline_cycles=1,
            token_latency_bound='one added response stage; conservative one edge per fetched sector, including finite NOUT credit interaction; measure exact RTL',
            per_record_added_cycles_bound_expression='sum over fetched QK/PV rows of ceil(head_dim * element_bytes / 32); actual response/credit timing required',
            rate_credit=0,default_on=False),
        monolithic_controller_cut=dict(payload_bits=sum(engine.values()),
            pin_capacity=int(perimeter*density),fits=False,
            disposition='reject this perimeter; distribute Q/P/code/cur stagers beside actual engine tiles'),
        physical_adopted=False,
        readiness='sector codec ready for component RTL sizing; whole ATT split blocked on real memory port views and distributed geometry')


if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
