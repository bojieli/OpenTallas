"""Remote-only lowering and host-control checks; no arithmetic/RTL claim."""
import argparse,json,resource
from pathlib import Path
import qwen_r25_decode_program as P
from qwen_r25_decode_host import DecodeHost,loader_payload

class Pins:
    """Protocol test fixture only; production shell never manufactures results."""
    def __init__(self,negative=None):
        self.cp=[[dict(db_rdy=1,cpl_v=0,cpl_job=0,cpl_generation=0,cpl_position=0,cpl_status=0,cpl_token=0) for _ in range(2)] for _ in range(4)]
        self.inputs=[None]*4;self.pending={};self.mem={};self.negative=negative;self.now=0;self.launches=0
    def snapshot(self):return [[dict(c) for c in d] for d in self.cp]
    def stage_batch(self,b):return True  # Protocol fixture; no actual descriptor qualification.
    def drive_die(self,die,ports):self.inputs[die]=ports
    def tick(self):
        for die,d in enumerate(self.cp):
            packed=loader_payload(self.inputs[die]);assert packed.bit_length()<=343
            for band,c in enumerate(d):
                p=self.inputs[die][band];key=(die,band)
                tuplebits=(packed>>(148 if band==0 else 0))&((1<<148)-1)
                assert (tuplebits>>74)&((1<<18)-1)==151935
                if p['cmd_we']:
                    assert c['db_rdy'];self.mem[key,p['cmd_addr']]=p['cmd_wdata']
                if p['db_v'] and c['db_rdy']:
                    assert self.mem[key,1]==2<<60
                    c['db_rdy']=0;self.pending[key]=self.now+2+die+band;self.launches+=1
                if p['cpl_rdy'] and c['cpl_v']:c.update(cpl_v=0,db_rdy=1)
                if self.pending.get(key)==self.now:
                    token=151935
                    if key==(3,1) and self.negative=='truncate':token&=(1<<17)-1
                    c.update(cpl_v=1,cpl_status=0,cpl_token=token,cpl_job=p['db_job'],cpl_generation=p['db_generation'],cpl_position=p['db_pos'])
                    if key==(3,1) and self.negative=='stale':c['cpl_generation']^=1
                    del self.pending[key]
        self.now+=1


def host_gate(negative=None):
    pins=Pins(negative)
    h=DecodeHost(pins,[dict(name='head',words=[(1<<60)|(65535<<44)|256,2<<60],result=True)],token=151935,position=8191,job=41,generation=13)
    for _ in range(40):
        if h.step()=='DONE':break
    assert h.state=='DONE' and h.result==151935 and pins.launches==8
    return dict(token=h.result,processors=pins.launches,cycles=h.cycles)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--su-tools',required=True,type=Path);ap.add_argument('--image-tools',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    p=P.compile_program(a.su_tools,a.image_tools)
    import sys,importlib,hashlib
    sys.path.insert(0,str(a.image_tools.resolve()));image=importlib.import_module('qwen_r25_int8_image')
    p['fmt3_source_sha256']=hashlib.sha256(Path(image.__file__).read_bytes()).hexdigest()
    p['fmt3_matrix_geometry']=image.qwen_tp4_shapes()
    for s in p['fmt3_matrix_geometry'].values():
        assert s['x_addresses_per_sm']<=128 and s['rows_per_sm']<=4096
    # QKV and gate/up are explicitly separate images, not fused code-row shards.
    for batch in p['batches']:
        for op in batch['operations']:
            names={'qkv':['q','k','v'],'gu':['gate','up']}.get(op['kernel'],[op['kernel']])
            if op['unit']=='SM':op['parameters']['image_manifest_geometry']={n:p['fmt3_matrix_geometry'][n] for n in names}
    assert len(p['batches'])==38
    assert all(b['command_words_needed']<=256 for b in p['batches'])
    assert len(p['batches'][1]['operations'])==24
    assert p['SU']['programs']['rope']['fields'][0]['abase']==16384
    assert p['SU']['programs']['qknorm']['fields'][2]['obase']==16384
    assert p['HBM']['max_stack_allocated_bytes']<=p['HBM']['stack_capacity_bytes']
    rows=p['HBM']['per_die'];assert all(rows[i]['base']+rows[i]['bytes']<=rows[i+1]['base'] for i in range(len(rows)-1))
    for e in rows:
        for x in (e['base'],e['base']+e['bytes']-1):
            m=P.service_address(x)
            assert m['byte_address37']>>35==m['stack']
            assert ((m['byte_address37']&((1<<35)-1))>>5)==m['sector30']
            s=m['sector30'];assert m['canonical_pc']==(((s>>2)&31)^((s>>7)&31)^((s>>12)&31))
    seen=set()
    for pos in range(8192):
        for sector in range(4):
            m=P.kv_sweep_address(0,pos,sector);key=(m['pc'],m['bank'],m['row'],m['col'])
            assert key not in seen;seen.add(key)
            assert m['j']*32+m['pc']==pos*4+sector
    assert len(seen)==32768
    try:P.link(p,{})
    except ValueError as e:assert 'missing actual production kernel binding' in str(e)
    else:raise AssertionError('missing dispatcher accepted')
    host=host_gate();neg={}
    for n,expected in [('stale','stale completion identity'),('truncate','TP4 global token mismatch')]:
        try:host_gate(n)
        except RuntimeError as e:assert expected in str(e);neg[n]=str(e)
        else:raise AssertionError('mutant not killed')
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'program.json').write_text(json.dumps(p,indent=2)+'\n')
    (a.out/'gate.json').write_text(json.dumps(dict(status='PASS_LOWERING_AND_HOST_PROTOCOL_ONLY',actual_RTL_executed=False,host=host,negative_controls=neg,missing_entries=p['missing_production_entries'],peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),indent=2)+'\n')
    print('QWEN_R25_PROGRAM_GATE_PASS host_and_lowering_only production_entries_missing='+str(len(p['missing_production_entries'])))
if __name__=='__main__':main()
