from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from deepseek_hbm_complete_memory import PersistentMemory,FiniteCollective,Backpressure

class CompleteMemory(unittest.TestCase):
    def test_actual_commit_and_final_consumer_release(self):
        m=PersistentMemory();m.preload(('kv',0),b'old')
        t=m.submit(('kv',0),write=True,payload=b'new')
        self.assertEqual(m.values[('kv',0)],b'old')
        with self.assertRaises(ValueError):m.consume(t)
        with self.assertRaises(Backpressure):m.fence()
        m.actual_backend_event(t);self.assertEqual(m.values[('kv',0)],b'new')
        with self.assertRaises(Backpressure):m.submit(('kv',0))
        m.consume(t);m.fence();r=m.submit(('kv',0));m.actual_backend_event(r)
        with self.assertRaises(Backpressure):m.submit(('kv',0),write=True,payload=b'next')
        self.assertEqual(m.consume(r),b'new');m.fence()
    def test_fourcredits_safe_length_stale_epoch(self):
        m=PersistentMemory();ts=[m.submit(('x',i),write=True,payload=b'x') for i in range(4)]
        with self.assertRaises(Backpressure):m.submit(('extra',),write=True,payload=b'x')
        with self.assertRaises(ValueError):m.submit(('bad',),write=True,payload=b'x',sectors=17)
        with self.assertRaises(ValueError):m.submit(('bad',),write=True,payload=b'x'*33,sectors=1)
        m.actual_backend_event(ts[0]);m.consume(ts[0]);new=m.submit(('x',5),write=True,payload=b'y')
        self.assertEqual(new.tag,ts[0].tag)
        with self.assertRaises(ValueError):m.actual_backend_event(ts[0])
    def test_persistence_large_object_and_collective_produced_values(self):
        m=PersistentMemory();data=bytes(range(256))*9;m.write_object(('ckv',1),data)
        self.assertEqual(m.read_object(('ckv',1)),data);m.fence()
        f=FiniteCollective();got=f.publish('all_gather',[(0,b'A'),(95,b'B')],lambda s:b''.join(x for _,x in s))
        self.assertEqual(got,b'AB');self.assertTrue(f.events[0]['consumer_done'])
        self.assertFalse(f.memory.values);self.assertFalse(f.memory.pending)
        self.assertIsNone(f.events[0]['cycles'])

if __name__=='__main__':unittest.main()
