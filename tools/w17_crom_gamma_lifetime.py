"""Serial source-command single-family gamma cache candidate, fail closed."""
import argparse,gzip,hashlib,json,subprocess

def can_replace(old_drained,output_quiet,owning_reverse_credit):
    return all(x is True for x in (old_drained,output_quiet,owning_reverse_credit))

def build():
    ref='f4bce8fa0';path='results/uarch/w11_crom_demand_20261001/demand_v2.json.gz'
    raw=subprocess.check_output(['git','show',ref+':'+path]);d=json.loads(gzip.decompress(raw))
    records=d['ranks'][0]['records'];rows=[];last={}
    for rec in records:
        gamma=[o for o in rec['operand_demands'] if o.get('tensor')=='norm.weight' or str(o.get('tensor','')).endswith(('attn_norm.weight','ffn_norm.weight'))]
        if not gamma:continue
        assert len(gamma)==1 and gamma[0]['unique_words']==5120
        layer=rec['layer'];previous=last.get(layer)
        rows.append(dict(layer=layer,PC=rec['global_instruction'],family=gamma[0]['tensor'],
            previous_gamma_PC=previous,cache_words=5120,cold_words=5120,
            intervals=['wait prior consumers/output/reversecredit drained',
                'invalidate old cache tag; no early ready','fill all5120 newsourcecoefficients',
                'publish image/rank/layer/family/PC/epoch tag only after lastaccepted fill',
                'consume5x1024 vectors from5entries/lane','wait all reads and owning credits drained before replacement'],
            actual_previous_consumer_done_cycle=None,actual_replacement_provider=False))
        last[layer]=rec['global_instruction']
    assert len(rows)==81 and sum(x['cold_words'] for x in rows)==414720
    return dict(schema='opentallas.CROM-single-gamma-family-lifetime.v1',
        source=dict(commit=ref,path=path,sha256=hashlib.sha256(raw).hexdigest()),
        candidate='one resident gamma family perhome under explicitly serial no-overlap command schedule',
        commands=rows,reference_rank_views=4,
        cache_bits_per_home=163840,cache_select_MUX2_bits_per_home=131072,
        preserved_twooperand_emit_buffers_bits=131072,
        retained_non_gamma_base_bits=147722,
        proposed_base_staging_bits=311562,
        gamma_words_refilled_per_rank=414720,no_alllayer_or_alltoken_reuse=True,
        no_refill_or_drain_timing_subtraction=True,
        replacement_predicate='oldactualconsumersdrained AND outputquiet AND returned owningreversecredit; booleanTrue only',
        actual_replacement_control_register_gate_inventory_complete=False,
        actual_consumer_lifetime_provider_bound=False,hardware_admission=False,
        previous_twofamily_screens_preserved=True,
        complete_area_power_or_slot_fit=None,checkpoint_reads=0,jobs_launched=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
