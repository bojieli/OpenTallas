"""Trust-boundary checks: missing/stale/externally supplied native joins refuse."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import kv_static as K


class StaticJoin(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'rtl').mkdir()
        self.path='rtl/native.sv'
        (self.root/self.path).write_text('''module native #(parameter integer MUT=0)(
input wire ck,rst_n,input wire [7:0]pi,output reg[7:0]po);
always @(posedge ck)if(!rst_n)po<=0;else po<=pi;
endmodule
''')
        ops=[dict(id='op0',kind='hbm_command',cycle=4,operands=[dict(instance='u',port='pi')],results=[dict(instance='u',port='po')])]
        import json
        (self.root/'programme.json').write_text(json.dumps(dict(schema='opentallas.qwen_kv_static.programme.v1',operations=ops,emitted_instruction_count=1)))
        (self.root/'compiler.py').write_text('# fixed compiler source\n')
        pin=lambda p:dict(path=p,sha256=hashlib.sha256((self.root/p).read_bytes()).hexdigest())
        self.graph=dict(schema='opentallas.qwen_kv_static.join.v1',
            source_files=[pin(self.path)],
            compiler_image=dict(schedule='fixed_cycle',normal_backpressure=False,
                programme=pin('programme.json'),compiler_sources=[pin('compiler.py')],
                operations=ops),
            external_inputs=[dict(name='clk',width=1,kind='clock'),dict(name='rst_n',width=1,kind='reset'),dict(name='phy',width=8,kind='analog_phy')],
            external_outputs=[dict(name='phy_out',width=8,kind='analog_phy',instance='u',port='po',lo=0)],
            instances=[dict(name='u',role='pc_path',source=self.path,module='native',sha256=pin(self.path)['sha256'],parameters=dict(MUT=0),
                inputs={p:[dict(external=n,lo=0,width=w)] for p,n,w in [('ck','clk',1),('rst_n','rst_n',1),('pi','phy',8)]})])
        self.roles=patch.object(K,'ROLES',{'pc_path':(self.path,'native',1)})
        self.deps=patch.object(K,'PC_SOURCES',[])
        self.roles.start();self.deps.start();self.addCleanup(self.roles.stop);self.addCleanup(self.deps.stop)

    def compile(self,g=None):return K.compile_graph(g or self.graph,self.root)

    def test_actual_source_emission_and_no_qualification(self):
        text,report=self.compile()
        self.assertIn('native #(.MUT(0)) u',text)
        self.assertIn('assign phy_out = n_u__po[7:0];',text)
        self.assertFalse(report['native_qualified']);self.assertFalse(report['physical_qualified'])
        self.assertNotIn('blackbox',text)

    def test_missing_operand(self):
        del self.graph['instances'][0]['inputs']['pi']
        with self.assertRaisesRegex(ValueError,'all exact input'):self.compile()

    def test_no_parameter_default(self):
        self.graph['instances'][0]['parameters']={}
        with self.assertRaisesRegex(ValueError,'every parameter'):self.compile()

    def test_stale_source(self):
        with (self.root/self.path).open('a') as f:f.write('// changed\n')
        with self.assertRaisesRegex(ValueError,'stale RTL'):self.compile()

    def test_golden_internal_input(self):
        self.graph['external_inputs'][2]['kind']='reference_result'
        with self.assertRaisesRegex(ValueError,'cannot be external'):self.compile()

    def test_phy_cannot_supply_internal_control(self):
        self.graph['instances'][0]['inputs']['ck']=[dict(external='phy',lo=0,width=1)]
        with self.assertRaisesRegex(ValueError,'cannot be supplied by a PHY'):self.compile()

    def test_width_truncation(self):
        self.graph['instances'][0]['inputs']['pi'][0]['width']=7
        with self.assertRaisesRegex(ValueError,'7 connected bits'):self.compile()

    def test_no_dynamic_programme(self):
        self.graph['compiler_image']['normal_backpressure']=True
        with self.assertRaisesRegex(ValueError,'fixed compiler cycles'):self.compile()

    def test_missing_population(self):
        self.graph['instances']=[]
        with self.assertRaisesRegex(ValueError,'census mismatch'):self.compile()

    def test_operation_requires_output(self):
        self.graph['compiler_image']['operations'][0]['results']=[]
        with self.assertRaisesRegex(ValueError,'operation coverage differs'):self.compile()

    def test_stale_compiler(self):
        (self.root/'compiler.py').write_text('# replacement')
        with self.assertRaisesRegex(ValueError,'stale compiler/image'):self.compile()

    def test_no_unchecked_width_expression(self):
        with self.assertRaises(ValueError):K.integer_expr('__import__("os").system("true")',{})

class OptInCli(unittest.TestCase):
    def test_static_missing_graph_never_falls_back(self):
        import os,subprocess,sys
        with tempfile.TemporaryDirectory() as out:
            env=dict(os.environ,OT_KV_STATIC='1')
            p=subprocess.run([sys.executable,str(K.ROOT/'tools/qwen_kv_die/kv_die.py'),'plan','--split','--out',out],env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,2);self.assertIn('no fallback netlist',p.stderr)
            self.assertTrue((Path(out)/'static_requirements.json').exists())
            self.assertFalse((Path(out)/'kv_die.v').exists())

    def test_static_case_and_legacy_expansion_refused(self):
        import os,subprocess,sys
        with tempfile.TemporaryDirectory() as out:
            env=dict(os.environ,OT_KV_STATIC='1')
            for script,args,message in [('kv_die.py',['case','--split','--out',out],'static physical case held'),('kv_expand.py',['--run',out],'cannot inherit legacy')]:
                p=subprocess.run([sys.executable,str(K.ROOT/'tools/qwen_kv_die'/script)]+args,env=env,capture_output=True,text=True)
                self.assertEqual(p.returncode,2);self.assertIn(message,p.stderr)

class CriticalNativeEdges(unittest.TestCase):
    @staticmethod
    def endpoint(n,p):return [dict(instance=n,port=p,lo=0,width=1)]

    def test_writer_expectations_are_not_link_echoes(self):
        w=dict(name='wrn',role='writer',parameters=dict(VMAP=1),inputs={})
        link=dict(name='link',role='link',inputs={})
        prog=dict(name='prg',role='writer_programme',parameters=dict(MUT=0,VMAP=1),inputs={})
        for p,sp in K.WRITER_LINK_MAP.items():w['inputs'][p]=self.endpoint('link',sp)
        for p,sp in K.WRITER_PROGRAMME_MAP.items():w['inputs'][p]=self.endpoint('prg',sp)
        for p,sp in [('kvn_compiled_identity','compiled_identity'),('kvn_compiled_generation','compiled_generation')]:link['inputs'][p]=self.endpoint('prg',sp)
        ins={'wrn':w,'link':link,'prg':prog};K.validate_native_edges(ins)
        w['inputs']['compiled_word_slot']=self.endpoint('link','kvn_word_slot')
        with self.assertRaisesRegex(ValueError,'wrong native producer'):K.validate_native_edges(ins)

    def test_ectl_actual_return_latency_and_peer(self):
        k=dict(name='ki',role='k_issuer',parameters=dict(RESPONSE_LAT=8,MUT=0),inputs=dict(rq=self.endpoint('a','rq')))
        a=dict(name='a',role='ectla',parameters=dict(STATIC_QK=1,ROW_RETURN_LAT=15),inputs=dict(rs=self.endpoint('ki','rs')))
        land=dict(name='land',role='landing',inputs={})
        for p in ('req_valid','req_t','req_v','req_epoch','req_layer'):land['inputs'][p]=self.endpoint('ki',p)
        for p in ('rsp_valid','rsp_data','rsp_t','rsp_v','rsp_epoch','rsp_layer'):k['inputs'][p]=self.endpoint('land',p)
        ins=dict(ki=k,a=a,land=land);K.validate_native_edges(ins)
        a['parameters']['ROW_RETURN_LAT']=21
        with self.assertRaisesRegex(ValueError,'ROW_RETURN_LAT=L'):K.validate_native_edges(ins)

class ActualTopology(unittest.TestCase):
    def test_full_shape_known_joins_and_unknowns_are_explicit(self):
        graph,gaps=K.template()
        self.assertEqual(len(graph['instances']),374)
        by={i['name']:i for i in graph['instances']}
        for stack in ('WS','WN','ES','EN'):
            for g in range(8):
                land=by[f'slg_{stack}_{g}']
                self.assertEqual(land['inputs']['req_valid'][0]['instance'],f'ki_{stack}_{g}')
                self.assertEqual(land['inputs']['expected_put'][0]['instance'],f'lcal_{stack}_{g}')
                for q,ep in enumerate(reversed(land['inputs']['actual_data'])):
                    pc=4*(4,5,0,1,2,3,6,7).index(g)+q
                    self.assertEqual(ep['instance'],f'pc_{stack}_{pc}')
                self.assertIsNone(by[f'ki_{stack}_{g}']['parameters']['RESPONSE_LAT'])
        for p in K.WRITER_PROGRAMME_MAP:
            self.assertEqual(by['wrn']['inputs'][p][0]['instance'],'wprg')
        self.assertFalse(gaps['native_qualified']);self.assertFalse(gaps['physical_qualified'])
        with self.assertRaisesRegex(ValueError,'incomplete template cannot emit'):K.compile_graph(graph)

if __name__=='__main__':unittest.main()
