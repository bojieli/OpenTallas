"""Receipt validation unit fixtures, not substitutes for actual source SAT proof."""
import copy, hashlib, json, tempfile
from pathlib import Path
import ctlm6_bound_macro as B

def digest(data): return hashlib.sha256(data).hexdigest()
def main():
    cells={'dc':dict(type='$_MUX_',connections={'A':['x'],'B':[3],'S':[4],'Y':[5]},
                     port_directions={'A':'input','B':'input','S':'input','Y':'output'},attributes={'src':'fixture.sv:1'}),
           'sink':dict(type='$_NOT_',connections={'A':[5],'Y':[6]},port_directions={'A':'input','Y':'output'})}
    ports={'q':{'direction':'output','bits':[5]}}
    raw=b'unit fixture only'
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp); artifacts={}
        for key,text in [('positive','SAT proof finished - no model found: SUCCESS!'),
                         ('negative','SAT proof finished - model found: FAIL!'),('cut','unit fixture cut')]:
            (base/key).write_text(text)
            artifacts[key]={'file':key,'sha256':digest(text.encode())}
        receipt=dict(schema='opentallas.undef_mux_observability.v1',verdict='PASS',
             raw_sha256=digest(raw),normalized_graph_sha256=digest(json.dumps(dict(cells=cells,ports=ports),sort_keys=True,separators=(',',':')).encode()),
             unknown=[dict(cell='dc',pin='A',known_pin='B',select=4,known=3,source='fixture.sv:1')],
             observability_contract='all_effective_next_state_reset_clock_macro_inputs_outputs',**artifacts)
        path=base/'receipt.json'
        def run(c=cells,p=ports,r=receipt,source=raw):
            path.write_text(json.dumps(r)); cc,pp=copy.deepcopy(c),copy.deepcopy(p)
            out=B.refine_undef_mux(cc,pp,source,path)
            return cc,pp,out
        cc,pp,out=run()
        assert 'dc' not in cc and cc['sink']['connections']['A']==[3] and pp['q']['bits']==[3]
        assert len(out['source_arms'])==1
        def refused(**kw):
            try:run(**kw)
            except ValueError:return
            raise AssertionError('mutant accepted')
        refused(source=b'changed source')
        for key,value in [('verdict','FAIL'),('normalized_graph_sha256','0'*64),('unknown',[]),('observability_contract','outputs_only')]:
            r=copy.deepcopy(receipt);r[key]=value;refused(r=r)
        for pin,value in [('B',['x']),('S',['x']),('S',['z']),('A',['z'])]:
            c=copy.deepcopy(cells);c['dc']['connections'][pin]=value;refused(c=c)
        c=copy.deepcopy(cells);c['sink']['connections']['A']=['x'];refused(c=c)
        for key in ['positive','negative','cut']:
            r=copy.deepcopy(receipt);r[key]['sha256']='0'*64;refused(r=r)
        r=copy.deepcopy(receipt);r['cut']['file']='../cut';refused(r=r)
        (base/'negative').write_text('PASS but no causal counterexample')
        r=copy.deepcopy(receipt);r['negative']['sha256']=digest((base/'negative').read_bytes());refused(r=r)
    print('UNDEF_RECEIPT_EXACT_HASH_ARMS_ARTIFACTS_AND_STRICT_REFUSALS PASS')
if __name__=='__main__':main()
