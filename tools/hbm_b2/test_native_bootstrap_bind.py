import json
import tempfile
import unittest
from pathlib import Path
from native_bootstrap_bind import attach,literal,parameter


def output(name,port,width): return dict(direction='output',width=width,segments=[('n',name+'__'+port,0,width-1)])
def inp(net,width): return dict(direction='input',segments=[('n',net,0,width-1)])
def fixture():
    native=dict(cfg_v=1,cfg_target=8,cfg_addr=12,cfg_data=256,desc_v=1,desc_base=12,desc_limit=13,desc_loops=16,launch_v=1)
    leaf=dict(master='ot_hbm_host_cfg_leaf2',params='.NT(2), .NF(3)',ports={})
    leaf['ports'].update(clk=inp('clock',1),rst_n=inp('por',1))
    for port,width in native.items():leaf['ports']['a_'+port]=output('hleaf_NW','a_'+port,width)
    for port,width in dict(ready=2,active=2,fault=3).items():
        leaf['ports']['t_'+port]=inp('old_'+port,width)
        leaf['ports']['s_'+port]=output('hleaf_NW','s_'+port,width)
    status=dict(master='ot_hbm_status_join_fa',params=".NT(5), .NF(5), .TGTS(40'h0504030201)",ports={})
    for port in ('ready','active'):
        status['ports']['t_'+port]=dict(direction='input',segments=[('n','before',0,0),('n','hleaf_NW__s_'+port,0,1),('n','after',0,1)])
    status['ports']['t_fault']=dict(direction='input',segments=[('n','before_fault',0,1),('n','hleaf_NW__s_fault',0,2)])
    return {'hleaf_NW':leaf,'host_status':status,
        'host_cp_ingress':dict(master='ot_hbm_host_static_ingress_obs',params=".TARGET_MASK(256'h1)",ports={}),
        'u_mu_fused_root':dict(ports={})}


class BootstrapBindTest(unittest.TestCase):
    def test_slot_insertion_preserves_all_existing_target_bits(self):
        instances=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'audit.json';path.write_text(json.dumps(dict(candidate=225,verdict='NO_EXISTING_ALLOCATION_OR_DECODE_ALIAS_FOUND',unresolved=[])))
            report=attach(instances,225,path,lambda n,p,w,r:inp('required_reset',w),output)
        self.assertEqual(report['status_targets_lsb_first'],[1,2,3,225,4,5])
        self.assertEqual(report['inserted_status_target_bit'],3)
        self.assertEqual(parameter(instances['hleaf_NW']['params'],'NT'),'3')
        self.assertEqual(parameter(instances['hleaf_NW']['params'],'NF'),'4')
        self.assertEqual(parameter(instances['host_status']['params'],'NT'),'6')
        self.assertEqual(parameter(instances['host_status']['params'],'NF'),'6')
        self.assertEqual(literal(parameter(instances['host_cp_ingress']['params'],'TARGET_MASK')),1|(1<<225))
        self.assertEqual(instances['u_mu_fused_root']['ports']['job']['segments'],[('n','u_mu_fused_programme__job',0,216)])
        self.assertEqual(instances['u_mu_fused_programme']['ports']['root_done']['segments'],[('n','u_mu_fused_root__done',0,0)])
        self.assertEqual(instances['hleaf_NW']['ports']['t_fault']['segments'][-1],('n','u_mu_fused_programme__fault',0,0))

    def test_partial_namespace_audit_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'audit.json';path.write_text(json.dumps(dict(candidate=225,verdict='NO_EXISTING_ALLOCATION_OR_DECODE_ALIAS_FOUND',unresolved=['unknown_decoder'])))
            with self.assertRaisesRegex(ValueError,'complete exact namespace'):
                attach(fixture(),225,path,lambda *a:None,output)

    def test_disabled_low_targets_rejected_even_with_complete_audit(self):
        for target in (8,15):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'audit.json'
                path.write_text(json.dumps(dict(candidate=target,verdict='NO_EXISTING_ALLOCATION_OR_DECODE_ALIAS_FOUND',unresolved=[])))
                with self.assertRaisesRegex(ValueError,'16..255'):
                    attach(fixture(),target,path,lambda *a:None,output)

    def test_lowest_enabled_native_target_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'audit.json'
            path.write_text(json.dumps(dict(candidate=16,verdict='NO_EXISTING_ALLOCATION_OR_DECODE_ALIAS_FOUND',unresolved=[])))
            report=attach(fixture(),16,path,lambda n,p,w,r:inp('required_reset',w),output)
        self.assertEqual(report['target'],16)

    def test_existing_allocation_mutant_is_rejected(self):
        instances=fixture()
        instances['host_status']['params']=".NT(5), .NF(5), .TGTS(40'h0504e10201)"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'audit.json';path.write_text(json.dumps(dict(candidate=225,verdict='NO_EXISTING_ALLOCATION_OR_DECODE_ALIAS_FOUND',unresolved=[])))
            with self.assertRaisesRegex(ValueError,'already participates'):
                attach(instances,225,path,lambda *a:None,output)


if __name__=='__main__':unittest.main()
