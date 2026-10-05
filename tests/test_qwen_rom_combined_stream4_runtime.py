from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
old_path=sys.path[:]
try:
    sys.path.insert(0,str(ROOT/'tools'))
    import qwen_rom_combined_stream4_runtime_emit as emitter
    import qwen_rom_combined_stream4_layer_prepare as prepare
    import qwen_rom_combined_stream4_link as link
finally:
    sys.path[:]=old_path


class StreamRuntimeTests(unittest.TestCase):
    def test_single_store_initialization_release_and_real_retirement(self):
        s=emitter.emit(ROOT)
        self.assertNotIn('CombinedHBM',s)
        self.assertNotIn('hbm_stack_binding.hpp',s)
        self.assertIn('stream4_runtime_binding.hpp',s)
        self.assertIn('hbm[d]->clocks(clock_event.core_high)',s)
        self.assertIn('stream4_mlp_program_base(mem[d].desc)',s)
        self.assertIn('wire_stream4_kv_free(*die[d],actual_mlp_base[d])',s)
        self.assertIn('stream4_layer_terminal(*die[d])',s)
        self.assertLess(s.index('for(int d=0;d<D;++d)hbm[d]->eval();'),s.index('preload_hbm(*die[d]'))
        header=(ROOT/'tools/runtime/qwen_combined/stream4_runtime_binding.hpp').read_text()
        self.assertIn('BorrowedStream4Memory<Vhbm> borrowed',header)
        self.assertIn('bool qwen_stream4_wire_native_tagged_rows(Vdie&,Vhbm&);',header)
        self.assertNotIn('__attribute__((weak))',header)
        self.assertEqual(header.count('Vhbm model;'),1)
        first_eval=s.index('    for(int d=0;d<D;++d)die[d]->eval();')
        initial_wire=s.rfind('for(int d=0;d<D;++d)hbm[d]->wire();',0,first_eval)
        self.assertGreater(initial_wire,s.index('tile->rst_n=0;'))
        edge_start=s.index('coll.clk=clock_event.core_high;')
        edge_wire=s.index('for(int d=0;d<D;++d)hbm[d]->wire();',edge_start)
        edge_eval=s.index('for(int d=0;d<D;++d)die[d]->eval();',edge_start)
        self.assertLess(edge_wire,edge_eval)
        self.assertLess(s.index('die[d]->hclk=clock_event.service_high;',edge_start-500),edge_wire)

    def test_odd_clock_rising_period_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp);src=t/'clock.cpp';exe=t/'clock'
            src.write_text('''#include "stream4_clock_driver.hpp"
#include <cassert>
int main(){
 qwen_stream4::ClockDriver c({833333,416666},{1024000,512000});
 uint64_t prev=0;unsigned rises=0;
 while(rises<100){auto e=c.next();if(e.core_rise()){
   if(rises)assert(e.time_fs-prev==833333);
   prev=e.time_fs;++rises;}}
 assert(c.core_rises()==100);
}
''')
            subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I'+str(ROOT/'tools/runtime/qwen_combined'),str(src),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([str(exe)],check=True)

    def test_prepare_failure_restores_old_native_selection(self):
        p=prepare.predecessor;old_runtime,old_selection=p.runtime,p.selected
        with patch.object(p,'prepare',side_effect=ValueError('wrong actual source')):
            with self.assertRaisesRegex(ValueError,'wrong actual source'):prepare.prepare()
        self.assertIs(p.runtime,old_runtime);self.assertIs(p.selected,old_selection)

    def test_old_tag13_ack_models_rejected(self):
        b=dict(die=['-GG=6144','-GSW=64','-GNW=18','-GSNW=18','-GD=4','-GREAL_MEM=1',
                   '-GNEAR_HBM=1','-GHBM_STREAM4=1','-GNSTK=4','-GWBW=4'],
               coll=['-GN=4','-GTAGW=44'],hbm=['-GNPC=32','-GTAGW=13','-GNSTK=1'],tile=[])
        with self.assertRaisesRegex(ValueError,'single four-stack STREAM4 model'):
            link.require_models(b,Path('/unused'),Path('/unused'))


if __name__=='__main__':unittest.main()
