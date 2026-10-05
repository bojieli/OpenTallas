import gzip
import hashlib
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
from dsrom_s81_qe_native_word_bridge import ReleasedQeOperationWords
import dsrom_s82_payload_interface as API

class BridgeTests(unittest.TestCase):
    def binding(self, alias, rows, index):
        with gzip.open(ROOT/'results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz','rt') as f:
            m=next(json.loads(line) for line in f if f'"alias":"{alias}"' in line)
        node=f'L0.I{index}'
        selected=dict(stage=m['stage'],rank=0,source_matrix_sha256=hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        dispatch=dict(source_dispatch_bound=True,fragments=[selected])
        e=SimpleNamespace(source=SimpleNamespace(resolve=lambda n,r:dict(fragments=[dict(matrix=m)]),bindings={node:dict(selector_slot=None)},nodes={node:dict(instruction=dict(unit=3,qe_mode=0,qe_nb=160,qe_nout=rows))}),dispatch=lambda n,r:dispatch)
        source=SimpleNamespace(root=Path(API.SNAPSHOT),descriptor=lambda name:(None,None,dict(dtype='F8_E8M0' if name.endswith('.scale') else 'F8_E4M3')))
        return ReleasedQeOperationWords(e,source,node,0),dispatch

    def test_full_qal_and_kval_real_pair_coverage(self):
        qal,_=self.binding('wq_a',320,7);kval,_=self.binding('wkv',128,8)
        self.assertEqual(len(qal.pairs),160);self.assertEqual(len(kval.pairs),64)
        covered=set()
        for plan in qal.matrix['plans']:
            _,_,first,n,stride,_,_=plan
            for j in range(n):covered.update((2*(first+j*stride),2*(first+j*stride)+1))
        self.assertEqual(covered,set(range(320)))
        with patch.object(API,'matrix_word',return_value=17) as codec:
            self.assertEqual(qal.read(0,0,4*qal.pairs[-1],0),17)
            codec.assert_called_once()
        with self.assertRaises(ValueError):kval.read(0,0,0,0)
        with self.assertRaisesRegex(ValueError,'unique matrix owner'):qal.read(0,0,0,4095)

    def test_actual_transport_and_rejection_cpp_callback(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);script=p/'provider.py'
            script.write_text('import sys,socket\nsys.path.insert(0,'+repr(str(ROOT/'tools'))+')\nfrom dsrom_s82_native_word_server import serve_connection\nfd=int(sys.argv[sys.argv.index("--fd")+1])\ndef read(s,r,m,w):\n if (s,r,m,w)!=(0,0,8,0): raise ValueError("wrong owner")\n return (1<<273)+123\nwith socket.socket(fileno=fd) as c: serve_connection(c,read)\n')
            cpp=p/'test.cpp';header=ROOT/'tools/runtime/dsrom/s81_qe_checkpoint_word_reader.hpp'
            cpp.write_text('#include '+json.dumps(str(header))+'\nint main(int argc,char**argv){(void)argc; DsromS81QeCheckpointWordReader p(argv[1],argv[2],"unused","unused","L0.I8",0);auto w=p.read(0,0,8,0);if(w[0]!=123||w[8]!=(1u<<17))return 2;try{p.read(0,0,0,0);return 3;}catch(const std::runtime_error&){}return 0;}\n')
            subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test'),sys.executable,str(script)],check=True)

if __name__=='__main__':unittest.main()
