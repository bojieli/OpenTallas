"""Pin-driver checks only: these stimuli do not qualify RTL arithmetic/latency."""
import unittest
from tools.gpu_sys.ds_hbm_sm_engine20 import SMEngine20


class Pins:
    def __init__(self):
        self.dies = [dict(db_rdy=0, cpl_v=0, cpl_data=0) for _ in range(2)]
        self.driven = {}; self.edges = 0
    def snapshot(self): return {'dies':self.dies}
    def drive_die(self, index, **ports): self.driven[index] = ports
    def tick(self): self.edges += 1


def cpl(job=7, generation=3, position=1048575, token=128799):
    return token | position<<17 | 2<<37 | 123<<41 | generation<<73 | job<<77


class TestEngine(unittest.TestCase):
    def setup_engine(self):
        p = Pins(); e = SMEngine20(p, enable=True)
        e.launch(entry_pc=19, token=128799, position=1048575, job=7, generation=3)
        return p,e
    def reach_wait(self,p,e):
        for d in p.dies:d['db_rdy']=1
        e.poll(); e.poll(); e.poll()
        self.assertEqual(e.state,'WAIT')
    def test_real_ready_and_all_die_join(self):
        p,e=self.setup_engine(); self.assertIsNone(e.poll())
        self.assertFalse(any(v['cmd_we'] for v in p.driven.values()))
        self.reach_wait(p,e)
        p.dies[0].update(cpl_v=1,cpl_data=cpl());self.assertIsNone(e.poll())
        self.assertEqual(e.state,'WAIT')
        p.dies[1].update(cpl_v=1,cpl_data=cpl());r=e.poll()
        self.assertEqual((r.job,r.generation,r.position,r.token),(7,3,1048575,128799))
        self.assertEqual(r.cycles_by_die,(123,123))
        self.assertEqual(p.driven[0]['cpl_rdy'],0)
    def test_stale_completion_terminal(self):
        p,e=self.setup_engine();self.reach_wait(p,e)
        p.dies[0].update(cpl_v=1,cpl_data=cpl(generation=2))
        with self.assertRaisesRegex(RuntimeError,'identity'):e.poll()
        edges=p.edges
        with self.assertRaises(RuntimeError):e.poll()
        self.assertEqual(p.edges,edges)
    def test_no_overlap_or_narrowing(self):
        p,e=self.setup_engine()
        with self.assertRaises(RuntimeError):e.launch(entry_pc=0,token=0,position=0,job=0,generation=0)
        with self.assertRaises(ValueError):SMEngine20(p)
        fresh=SMEngine20(p,enable=True)
        with self.assertRaises(ValueError):fresh.launch(entry_pc=0,token=0,position=1048576,job=0,generation=0)


if __name__=='__main__':unittest.main()
