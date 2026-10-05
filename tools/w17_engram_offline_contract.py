"""Source-bound parameter-only CROM manufacture authority, no tensor reads."""
import argparse
import ast
import hashlib
import json
import subprocess

PIN='d2c28c279'
PATH='tools/hdc_program_v41.py'
def audit(source):
    t=ast.parse(source)
    products=[]
    for n in ast.walk(t):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='G' and n.func.attr=='mul':
            args=n.args
            if len(args)==2 and all(isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='lw' for x in args):
                families=[x.args[1].value for x in args if len(x.args)==2 and isinstance(x.args[1],ast.Constant)]
                if families==['engram.q_weight','engram.k_weight']:
                    products.append(n.lineno)
    if len(products)!=1: raise ValueError('parameter-only exact producer contract changed')
    consumers=[]
    for n in ast.walk(t):
        if not isinstance(n,ast.Call): continue
        kw={x.arg:x.value for x in n.keywords}
        if 'b_base' in kw and 'ewgt' in ast.unparse(kw['b_base']):
            if ast.unparse(kw.get('b_src'))!='I.SRC_CLO' or ast.unparse(kw.get('m1'))!='I.M1_AB' or ast.unparse(kw.get('m2'))!='I.M2_C':
                raise ValueError('CROM consumer/order changed')
            consumers.append(n.lineno)
    if len(consumers)!=1: raise ValueError('missing immutable CROM consumer')
    return products,consumers

def build():
    raw=subprocess.check_output(['git','show',f'{PIN}:{PATH}'])
    products,consumers=audit(raw.decode())
    receipt_path='results/uarch/w11_engram_product_source_20261001/verification.json'
    receipt_raw=subprocess.check_output(['git','show',f'60545ff45:{receipt_path}'])
    receipt=json.loads(receipt_raw)
    return dict(schema='opentallas.engram-offline-parameter-contract.v1',
        source=dict(commit=subprocess.check_output(['git','rev-parse',PIN]).decode().strip(),path=PATH,sha256=hashlib.sha256(raw).hexdigest(),producer_lines=products,consumer_lines=consumers),
        retained_receipt=dict(commit=subprocess.check_output(['git','rev-parse','60545ff45']).decode().strip(),path=receipt_path,sha256=hashlib.sha256(receipt_raw).hexdigest(),L14_product=receipt['actual_L14_product']),
        authoritative_path='offline exact parameter product -> immutable CROM image -> SRC_CLO consumer',
        arithmetic='BF16 widen exactly; FP32 integer-RNE multiply; no product BF16 round; preserve runtime h*p then key and tree order',
        activation_oracle_used=False, checkpoint_reads=0,
        runtime_initializer_required=False, mutable_overlay_required=False,
        initializer_458_scope='optional opt-in architecture alternative, not frozen-ROM baseline mandatory hardware or latency',
        physical_composition=dict(checkpoint_words_per_rank=508800,
            generated_words_per_layer=20480,generated_layers=[1,14],
            total_logical64_words_per_rank=549760,default_capacity=524288,default_deficit=25472,
            candidate_macro_banks=45,macro_rows=4096,logical64_slots_per_macro_row=3,
            candidate_capacity=552960,candidate_spare_before_padding=3200,
            layout='candidate address a: bank=(a//3)%45,row=(a//3)//45,slot=a%3',
            physical_images_complete=False, runtime_coefficient_delivery_still_required=True,
            placement_read_capture_select_CDC_power_qualified=False,
            reference_rank_views_do_not_imply_automatic_physical_copies=True),
        lifetime='manufacture once per immutable parameter/image revision; source/product/image hashes bind publication; no per-token SU initialization cost',
        hard_gates=['L1 actual retained q/k pair SHA/provenance absent',
            'complete padded immutable image and actual consumer bases absent',
            'selected physical bank/home replication and finite coefficient service not qualified'],
        hardware_admission=False,full_token_cycles=None)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,indent=2,sort_keys=True);f.write('\n')
