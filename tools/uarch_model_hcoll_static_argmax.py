"""Pre-build static ARGMAX merger model; preserves actual HGI total ordering."""
def model(group=96):
    if group not in (1,2,4,8,96): raise ValueError('illegal HGI group')
    return {'group':group,'input_flits':group,'lanes':4,'flit_bits':545,
            'input_bits_per_cycle':2180,'output_bits_per_cycle':545,
            'payload_rule':'larger FP32, zeros equal, NaN last, ties lower U32 id',
            'fixed_flush_to_registered_output_edges':6,
            'ingress_edges':(group+3)//4,
            'native_fold_pipeline':'capture4, pair2, pair1, accumulator; exact existing amerge',
            'added_control_register_bound':1200,'existing_fold_register_bound':1100,
            'root_sink_upper_bound':2300,'elastic_storage':0,
            'comparators':'three pipelined pair compares plus one accumulator compare',
            'memory_bytes_per_cycle':0,'replicas_per_die':1,
            'area_slot':'unmeasured; separate M5 SW leaf; no assigned outline',
            'qualification':'component design model only; routed pin/clock and op price pending'}
if __name__=='__main__':
    import json
    print(json.dumps(model(),indent=2))
