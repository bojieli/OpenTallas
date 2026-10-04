import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dsrom_s81_qe_native_word_bridge import DelayedExpertWords
import dsrom_s82_payload_interface as API

class DelayedTests(unittest.TestCase):
    digest='ab'*32
    ids=[41,65,158,164,259,266] # Test tuple only, never a production default.
    def actor(self):
        source=SimpleNamespace(root=Path(API.SNAPSHOT))
        execution=SimpleNamespace(source=SimpleNamespace(bindings={'L20.I97':dict(selector_slot=0,source_node_semantic_sha256=self.digest)},nodes={'L20.I97':dict(instruction=dict(unit=3,qe_mode=0))}))
        return DelayedExpertWords(execution,source,'L20.I97',0,2)

    def test_unbound_then_exact_once_held_capture(self):
        a=self.actor()
        with self.assertRaisesRegex(ValueError,'unbound'):a.read(37,0,8,0)
        with patch('dsrom_s81_qe_native_word_bridge.ReleasedQeOperationWords',return_value=SimpleNamespace(read=lambda *x:17)) as factory:
            a.bind(self.digest,0,2,self.ids)
            self.assertEqual(a.read(37,0,8,0),17)
            self.assertEqual(factory.call_args.kwargs,dict(fragment=2,expert_ids=self.ids))
            with self.assertRaises(ValueError):a.bind(self.digest,0,2,self.ids)
            self.assertEqual(factory.call_count,1)

    def test_wrong_source_rank_fragment_or_tuple_quarantines(self):
        for digest,rank,fragment,ids in [('cd'*32,0,2,self.ids),(self.digest,1,2,self.ids),(self.digest,0,1,self.ids),(self.digest,0,2,[41]*6)]:
            a=self.actor()
            with self.assertRaises(ValueError):a.bind(digest,rank,fragment,ids)
            self.assertTrue(a.fault)
            with self.assertRaises(ValueError):a.bind(self.digest,0,2,self.ids)

    def test_cpp_prespan_child_ready_and_bind_after_worker_start(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            script=p/'child.py'
            script.write_text('''import sys,socket
from types import SimpleNamespace
from pathlib import Path
sys.path.insert(0,'''+repr(str(ROOT/'tools'))+''')
import dsrom_s81_qe_native_word_bridge as B
import dsrom_s82_payload_interface as API
B.ReleasedQeOperationWords=lambda *a,**k:SimpleNamespace(read=lambda *x:(1<<273)+k['expert_ids'][0])
e=SimpleNamespace(source=SimpleNamespace(bindings={'L20.I97':dict(selector_slot=0,source_node_semantic_sha256='ab'*32)},nodes={'L20.I97':dict(instruction=dict(unit=3,qe_mode=0))}))
a=B.DelayedExpertWords(e,SimpleNamespace(root=Path(API.SNAPSHOT)),'L20.I97',0,2)
fd=int(sys.argv[sys.argv.index('--fd')+1])
with socket.socket(fileno=fd) as c:B.serve_delayed_connection(c,a)
''')
            cpp=p/'test.cpp'
            cpp.write_text('#include '+json.dumps(str(ROOT/'tools/runtime/dsrom/s81_qe_checkpoint_word_reader.hpp'))+'''
#include <thread>
int main(int argc,char**argv){(void)argc;
 DsromS81QeCheckpointWordReader p(argv[1],argv[2],"unused","unused","L20.I97",0,2,{},true);
 auto before=p.source_child_pid();
 try{p.read(37,0,8,0);return 2;}catch(const std::runtime_error&){}
 std::thread worker([&](){p.bind_captured_eids({41,65,158,164,259,266},"'''+self.digest+'''",0,2);});worker.join();
 auto w=p.read(37,0,8,0);if(w[0]!=41||w[8]!=(1u<<17)||before!=p.source_child_pid())return 3;
 try{p.bind_captured_eids({41,65,158,164,259,266},"'''+self.digest+'''",0,2);return 4;}catch(const std::runtime_error&){}
 return 0;
}
''')
            subprocess.run(['g++','-std=c++17','-pthread','-Wall','-Wextra','-Werror',str(cpp),'-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test'),sys.executable,str(script)],check=True)

if __name__=='__main__':unittest.main()
