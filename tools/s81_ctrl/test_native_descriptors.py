#!/usr/bin/env python3
"""Compiler mechanism gate; synthetic signals are not production engine proof."""
import copy
import hashlib
import tempfile
from pathlib import Path
from native_descriptors import compile_jobs

def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / 'synthetic_native_contract.json'
        source.write_text('{"fixture":"compiler mechanism only"}\n')
        schema = {'engine':2, 'status':'OWNER_NATIVE_CONTRACT',
                  'endpoint':'synthetic_test_only',
                  'evidence':[{'path':source.name,
                               'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}],
                  'signals':{'data':{'width':512,'fields':[{'name':'payload','lsb':0,'width':512}]},
                             'opcode':{'width':7,'fields':[{'name':'op','lsb':0,'width':7,'allowed':[3]}]},
                             'position':{'width':21,'fields':[{'name':'pos','lsb':0,'width':21}]}}}
        registry={'schemas':{'fixture':schema},'jobs':{
            'fullwidth':{'schema':'fixture','signals':{'data':{'payload':{'ref':'payload'}},
                                                    'opcode':{'op':3},'position':{'pos':{'ref':'position'}}}}}}
        payload=(1<<511)|(1<<256)|0x0123456789abcdef
        request={'context':{'payload':payload,'position':(1<<21)-1},
                 'jobs':[{'id':'fullwidth','engine':2}]}
        result=compile_jobs(request,registry,root)
        assert result['command_table_eligible'] and not result['dispatch_eligible']
        assert int(result['rows'][0]['signals']['data']['hex'],16)==payload
        assert int(result['rows'][0]['signals']['position']['hex'],16)==(1<<21)-1
        checks=2
        def rejected(req=request, reg=registry):
            result=compile_jobs(req,reg,root)
            assert not result['dispatch_eligible'] and not result['rows']
        req=copy.deepcopy(request);req['jobs'].append({'id':'missing','engine':1});rejected(req);checks+=1
        req=copy.deepcopy(request);req['jobs'][0]['engine']=1;rejected(req);checks+=1
        req=copy.deepcopy(request);req['context']['position']=1<<21;rejected(req);checks+=1
        req=copy.deepcopy(request);req['context']['payload']=-1;rejected(req);checks+=1
        req=copy.deepcopy(request);del req['context']['payload'];rejected(req);checks+=1
        reg=copy.deepcopy(registry);reg['jobs']['fullwidth']['signals']['opcode']['op']=4;rejected(reg=reg);checks+=1
        reg=copy.deepcopy(registry);reg['schemas']['fixture']['status']='UNBOUND';rejected(reg=reg);checks+=1
        reg=copy.deepcopy(registry);reg['schemas']['fixture']['signals']['data']['fields'][0]['width']=511;rejected(reg=reg);checks+=1
        reg=copy.deepcopy(registry);reg['schemas']['fixture']['signals']['data']['fields'].append({'name':'overlap','lsb':0,'width':1});reg['jobs']['fullwidth']['signals']['data']['overlap']=0;rejected(reg=reg);checks+=1
        reg=copy.deepcopy(registry);del reg['jobs']['fullwidth']['signals']['position'];rejected(reg=reg);checks+=1
        source.write_text('changed');rejected();checks+=1
        print(f'NATIVE_DESCRIPTOR_COMPILER mechanism_only=1 payload_width=512 position_width=21 checks={checks} PASS')

if __name__=='__main__':
    main()
