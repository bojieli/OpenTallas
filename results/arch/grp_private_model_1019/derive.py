"""Read-only small-source ledger; arguments are exact frozen graph/source snapshots."""
import argparse, hashlib, json, re
from pathlib import Path

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def derive(source, graphs):
    text = source.decode()
    expected = 'df66545140a103b45170c9132cf19e521945c61c8fc649e836df4bb9c49e6e97'
    assert digest(source) == expected, 'selected source identity changed'
    modules = {}
    for name in ['qkd_kvs_grp', 'qkd_kvs_grp_h']:
        body = re.search(r'module ' + name + r'\s*\((.*?)endmodule', text, re.S).group(0)
        ports = {n: {'direction': d, 'bits': abs(int(a or 0)-int(b or 0))+1}
                 for d,a,b,n in re.findall(r'(input|output) wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)', body.split(');')[0])}
        for n in ['x__tok', 'x__tep', 'x__est']:
            assert len(re.findall(r'\b'+n+r'\b', body)) == 2
        assert 'assign y__tok = x__tok;' in body
        assert 'assign y__tep = x__tep;' in body
        assert 'assign y__est__0_1 = x__est[0:0];' in body
        extra = name.endswith('_h')
        if extra:
            rest = body.replace('assign o_dn = {i_ctl[193:183], i_ctl[270:194], i_ctl[182:0]};', '')
            assert 'i_ctl[270:194]' not in rest
            assert max(int(a) for a,b in re.findall(r'i_ctl\[(\d+):(\d+)\]', rest)) == 193
        ins = sum(v['bits'] for k,v in ports.items() if v['direction']=='input' and k not in ['ck','hck','rst_n','hrst_n'])
        outs = sum(v['bits'] for v in ports.values() if v['direction']=='output')
        modules[name] = {'module_sha256': digest(body.encode()), 'ports': ports,
                        'removed_input_bits':46 + (77 if extra else 0),
                        'removed_output_bits':34 + (271 if extra else 0),
                        'remaining_nonclock_nonreset_input_bits':ins-46-(77 if extra else 0),
                        'remaining_output_bits':outs-34-(271 if extra else 0)}
    records = {}
    for graph_name, raw in graphs.items():
        lines = raw.decode().splitlines()
        instances = []
        for line_no, line in enumerate(lines,1):
            m = re.match(r'\s*(qkd_kvs_grp(?:_h)?)\s+(slg_\w+)\s*\((.*)\);', line)
            if not m:
                continue
            typ, name, ports = m.groups()
            connections = dict(re.findall(r'\.(\w+)\(([^()]*)\)', ports))
            assert not any(k in connections for k in ['y__tok','y__tep'])
            if typ.endswith('_h'):
                assert 'o_dn' not in connections
            net = re.match(r'\w+',connections['y__est__0_1']).group(0)
            uses=[]
            for use_line_no, use_line in enumerate(lines,1):
                if net not in use_line or use_line_no==line_no or re.match(r'\s*wire\b',use_line):
                    continue
                for port, expr in re.findall(r'\.(\w+)\(([^()]*)\)', use_line):
                    if re.search(r'\b'+re.escape(net)+r'\b',expr):
                        uses.append({'line':use_line_no,'port':port,'expression':expr,'instance':use_line.strip().split(' (')[0]})
            assert len(uses)==4 and all(u['port']=='x__est__0_1' for u in uses)
            instances.append({'module':typ,'instance':name,'line':line_no,'connections':connections,
                              'live_est_consumers':uses})
        assert len(instances)==32
        assert sum(x['module'].endswith('_h') for x in instances)==4
        records[graph_name]={'sha256':digest(raw),'bytes':len(raw),'instances':instances}
    return {'schema':'grp_private_consumer_model_v2','source_sha256':expected,'modules':modules,'graphs':records}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('source',type=Path)
    p.add_argument('gen7_bound',type=Path)
    p.add_argument('gen8_prep',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    result=derive(a.source.read_bytes(),{'GEN7_BOUND':a.gen7_bound.read_bytes(),'GEN8_PREP_NOT_FINAL':a.gen8_prep.read_bytes()})
    a.output.write_text(json.dumps(result,indent=2)+'\n')
