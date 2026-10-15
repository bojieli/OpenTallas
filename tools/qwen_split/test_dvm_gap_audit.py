import unittest
from dvm_gap_audit import audit

class GapAuditTests(unittest.TestCase):
    def test_flush_column_does_not_split_slack(self):
        rect=lambda n,x,y,w,h:dict(n=n,x=x,y=y,w=w,h=h)
        model={'insts':[rect('left',0,0,10,10),rect('right',20.648,0,10,10),rect('irrelevant',10.1,50,1,1)]}
        candidate={'moves':[{'after':rect('h_0',10,0,10,10)}]}
        r=audit(model,candidate)
        self.assertEqual(r['columns'][0]['sides']['W']['clearance_um'],0)
        self.assertEqual(r['columns'][0]['sides']['E']['clearance_um'],.648)
        self.assertFalse(r['qualification'])

if __name__=='__main__':unittest.main()
