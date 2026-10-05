import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_minimum_return_binding as B


class BindingTests(unittest.TestCase):
    def test_bound_cfg_and_literal_ports_refuse_stale_or_missing_sources(self):
        class Join:
            by_stage={0:[dict(matrix=dict(rows=2,segments=[[0,32]],plans=[[0,0,0,1,1,0,1]]))]}
            def cfg(self, stage, rank, pair, word):
                return word+1
        # Unit port boundary, not a substitute canonical mapping/provider.
        c = dict(inventory_bound=True,no_READY=True,RD=64,ROOTD=128,QD=128,
                 RST=1,BYPASS=1,region_bounds=list(range(129)),
                 nodes=[dict(a=0,b=1,region=0,id=4834)])
        f = dict(stage=0,rank=0,phase=0,key=0,source_matrix_sha256='a'*64)
        profile = dict(source_matrix_sha256='a'*64,phase_rows=2,
                       root_return_counts=[2]+[0]*127,root_rows=[[0,1]]+[[]]*127)
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)/'e0.cfg.hex'
            cfg.write_text(''.join(f'{n:012x}\n' for n in range(1,26)))
            kw = dict(pair=0,positions=1,phrom0=2<<46,phrom1=2,cfg_path=cfg,
                      identity=17,format=1,output_base=1024,
                      output_position_stride=2,ME=False)
            with patch.object(B,'emitted_phase_profile',return_value=profile):
                result=B.bind_return_phase(Join(),c,f,**kw)
                self.assertEqual(result['whole_root_quota'],2)
                self.assertEqual(result['component_rows'],[0,1])
                self.assertEqual(result['branch_a_leaf'],0)
                self.assertFalse(result['field_complete'])
                for change in [dict(phrom0=3<<46),dict(identity=1<<47),
                               dict(output_base=1<<19),dict(positions=True)]:
                    with self.assertRaises(ValueError):
                        B.bind_return_phase(Join(),c,f,**(kw|change))
                cfg.write_text(''.join('000000000000\n' for _ in range(25)))
                with self.assertRaises(ValueError):
                    B.bind_return_phase(Join(),c,f,**kw)
                cfg.write_text('000000000001\n')
                with self.assertRaises(ValueError):
                    B.bind_return_phase(Join(),c,f,**kw)


if __name__=='__main__':unittest.main()
