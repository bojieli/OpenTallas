"""Functional health transport names preserve bit-level connectivity."""
from collections import defaultdict
from pathlib import Path
import tempfile
import types
import unittest
import kv_health_plane as H
import die_port_bind as P


class FunctionalTransport(unittest.TestCase):
    def fixture(self, consumer='n_rly__spare[3:0]', extra=''):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        p=Path(t.name)/'die.v'
        p.write_text("module die;\n wire [3:0] src;\n wire [3:0] n_rly__spare;\n wire [3:0] out;\n"+extra+"\n relay rly (.a(src[3:0]),.b(n_rly__spare[3:0]));\n receiver next (.a("+consumer+"),.b(out));\nendmodule\n")
        nets,_,_,insts=P.parse_die(str(p))
        return types.SimpleNamespace(nets=nets,cells={i:(m,pr,c) for m,i,pr,c in insts},bits=lambda x:P.expr_bits(x,nets))

    def test_partial_bus_every_consumer_and_health_signal(self):
        d=self.fixture(); edits=defaultdict(dict);sig={'transport':'n_rly__spare[2]','untouched':'src[1]'}
        ren=H.name_functional_transport(d,edits,{'rly':{'a':{2},'b':{2}}},sig)
        self.assertEqual(ren,{('n_rly__spare',2):('n_hp_transport_rly_b2',0)})
        self.assertEqual(edits['rly']['b'][1],('n_hp_transport_rly_b2',0))
        self.assertEqual(edits['next']['a'][1],edits['rly']['b'][1])
        self.assertEqual([b for b in edits['next']['a'] if b[0]=='n_rly__spare'],[('n_rly__spare',3),('n_rly__spare',1),('n_rly__spare',0)])
        self.assertEqual(sig['transport'],'n_hp_transport_rly_b2[0]');self.assertEqual(sig['untouched'],'src[1]')

    def test_existing_connection_edit_preserved(self):
        d=self.fixture();edits=defaultdict(dict);edits['next']['a']=[('src',0),('n_rly__spare',2),('src',1),('src',2)]
        H.name_functional_transport(d,edits,{'rly':{'a':{2},'b':{2}}},{})
        self.assertEqual(edits['next']['a'],[('src',0),('n_hp_transport_rly_b2',0),('src',1),('src',2)])

    def test_name_collision_refused(self):
        d=self.fixture(extra='wire [0:0] n_hp_transport_rly_b2;')
        with self.assertRaisesRegex(ValueError,'name collision'):
            H.name_functional_transport(d,defaultdict(dict),{'rly':{'a':{2},'b':{2}}},{})

    def test_unparsed_consumer_refused(self):
        d=self.fixture(consumer='n_rly__spare[3:0] ^ src')
        with self.assertRaisesRegex(ValueError,'unparsed functional transport consumer'):
            H.name_functional_transport(d,defaultdict(dict),{'rly':{'a':{2},'b':{2}}},{})

    def test_nonprivate_real_bus_keeps_identity(self):
        d=self.fixture();d.cells['rly']=(d.cells['rly'][0],{},dict(a='src',b='out'))
        e=defaultdict(dict);sig={'transport':'out[2]'}
        self.assertEqual(H.name_functional_transport(d,e,{'rly':{'a':{2},'b':{2}}},sig),{})
        self.assertEqual(dict(e),{});self.assertEqual(sig,{'transport':'out[2]'})


if __name__=='__main__':unittest.main()
