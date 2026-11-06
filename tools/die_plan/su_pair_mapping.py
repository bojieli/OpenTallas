"""Derive native pair to lane1 port mapping from actual Yosys endpoint identities.

Preparation mechanism only: the fixed physical child's phase is deliberately not
claimed equivalent to native MLAT4/ALAT4. Source-specific phase proof is required.
"""
import copy
from collections import defaultdict

CLOCKS = ('bank0_clk', 'bank0_clk_macro', 'lane0_clk_stage', 'lane0_clk_insert')

def pair_connections(template, actual, bank_name, lane_name):
    names = {'u_bank0': bank_name, 'u_lane0': lane_name}
    if set(template['cells']) != set(names):
        raise ValueError('Lane1 template must contain exactly the native bank and lane')
    endpoints = defaultdict(list)
    for name, cell in template['cells'].items():
        other = actual['cells'][names[name]]
        if cell['type'] != other['type'] or cell['parameters'] != other['parameters']:
            raise ValueError(f'Native template parameters/type differ: {name}/{names[name]}')
        for port, bits in cell['connections'].items():
            for bit_index, bit in enumerate(bits):
                if isinstance(bit, int):
                    endpoints[bit].append((names[name], port, bit_index))
    def actual_bit(ep):
        cell, port, bit = ep
        bits = actual['cells'][cell]['connections'][port]
        if bit >= len(bits):
            raise ValueError(f'Unconnected required endpoint {ep}')
        return bits[bit]
    # All internal template links must also exist in the native source. This
    # includes the local VI feedback and the physical row-address permutation.
    for bit, eps in endpoints.items():
        if len(eps) > 1:
            values = [actual_bit(ep) for ep in eps]
            if len(set(values)) != 1:
                raise ValueError(f'Native pair does not share template net {bit}: {eps}')
    ports = {}
    for name, port in template['ports'].items():
        result = []
        for bit in port['bits']:
            if not isinstance(bit, int):
                result.append(bit)
                continue
            eps = endpoints.get(bit, [])
            if not eps:
                raise ValueError(f'No native endpoint for template port {name}')
            values = [actual_bit(ep) for ep in eps]
            if len(set(values)) != 1:
                raise ValueError(f'Conflicting native input aliases for {name}')
            result.append(values[0])
        ports[name] = result
    clocks = [b for p in CLOCKS for b in ports.pop(p)]
    if len(set(clocks)) != 1:
        raise ValueError('Signed one-clock view cannot join different native clocks')
    ports['clk'] = [clocks[0]]
    return ports

def candidate_group(native_design, template_design, signed_design, native_top):
    template = template_design['modules']['ot_hbm_su_pg_lane1_core']
    signed = signed_design['modules']['ot_hbm_su_pg_lane1_core']
    native = native_design['modules'][native_top]
    body = copy.deepcopy(native)
    body['attributes'].pop('top', None)
    for p in ['bank_read_data', 'lane_vm_waddr', 'lane_kv_waddr']:
        width, retained = (192, list(range(128))+list(range(160,192))) if p == 'bank_read_data' else (24, list(range(18)))
        bits = body['ports'][p]['bits']
        if len(bits) != 4*width:
            raise ValueError(f'Expected explicit four-lane native ABI: {p}')
        body['ports'][p]['bits'] = [bits[lane*width+i] for lane in range(4) for i in retained]
        if p in body['netnames']:
            body['netnames'][p]['bits'] = body['ports'][p]['bits']
    for lane in range(4):
        bank, leaf = f'm{2*lane}', f'm{2*lane+1}'
        connections = pair_connections(template, native, bank, leaf)
        if set(connections) != set(signed['ports']):
            raise ValueError('Mapped ports differ from actual signed BB')
        for name,bits in connections.items():
            expected_direction = 'input' if name == 'clk' else template['ports'][name]['direction']
            if signed['ports'][name]['direction'] != expected_direction:
                raise ValueError(f'Mapped direction differs from signed BB: {name}')
            if len(bits) != len(signed['ports'][name]['bits']):
                raise ValueError(f'Mapped width differs from signed BB: {name}')
        del body['cells'][bank]
        del body['cells'][leaf]
        body['cells'][f'u_p{lane}'] = {'hide_name':0,'type':'ot_hbm_su_pg_lane1_core','parameters':{},
            'attributes':{},'port_directions':{p:v['direction'] for p,v in signed['ports'].items()},'connections':connections}
    outer_name = native_top+'__p17_candidate'
    names = [outer_name, outer_name+'__fcore', outer_name+'__core']
    modules = {names[2]:body,'ot_hbm_su_pg_lane1_core':copy.deepcopy(signed)}
    for name, child, inst in [(names[0],names[1],'u_fcore'),(names[1],names[2],'u_core')]:
        modules[name]={'attributes':{},'ports':copy.deepcopy(body['ports']),'netnames':{},'cells':{inst:{'hide_name':0,'type':child,'parameters':{},'attributes':{},'port_directions':{p:v['direction'] for p,v in body['ports'].items()},'connections':{p:v['bits'] for p,v in body['ports'].items()}}}}
    modules[names[0]]['attributes']['top']='1'
    return {'creator':'SU explicit pair mapping candidate; phase contract pending','modules':modules}, outer_name


def main():
    import argparse,json,hashlib
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-json',type=Path,required=True)
    p.add_argument('--template-json',type=Path,required=True)
    p.add_argument('--signed-json',type=Path,required=True)
    p.add_argument('--native-top',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    inputs=[a.native_json,a.template_json,a.signed_json]
    design,top=candidate_group(*(json.loads(x.read_text()) for x in inputs),a.native_top)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'candidate.json').write_text(json.dumps(design)+'\n')
    receipt={'status':'PHASE_PROOF_PENDING_DO_NOT_ROUTE','top':top,'native_profile':{'MLAT':4,'ALAT':4},'signed_profile':{'MLAT':5,'ALAT':3,'face_in':1,'face_out':1},'parent_flops':'retained','input_sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs},'children':[{'master':'ot_hbm_su_pg_lane1_core','inst':f'u_fcore.u_core.u_p{i}'} for i in range(4)],'parent_profile':{'top':top,'parameters':{}}}
    (a.out/'mapping.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(top)

if __name__=='__main__': main()
