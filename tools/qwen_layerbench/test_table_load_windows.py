import copy,unittest
from table_load_windows import validate

class Windows(unittest.TestCase):
    def fixture(self):
        return [dict(user=u,stage=s,start=((s-1)*4+u)*100,
            first_read=((s-1)*4+u)*100+93,last_read=((s-1)*4+u)*100+99,
            read_slots=88,manifest_sha256='a'*64,consumer_sha256='b'*64)
            for s in range(1,37) for u in range(4)]
    def test_positive(self):self.assertEqual(validate(self.fixture(),'a'*64)['windows'],144)
    def test_mutants(self):
        for key,value in [('stage',37),('user',4),('read_slots',87),('first_read',91),('start',0),('manifest_sha256','c'*64)]:
            w=self.fixture();w[1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(w,'a'*64)
        w=self.fixture();w[0]['last_read']=1000
        with self.assertRaises(ValueError):validate(w,'a'*64)

if __name__=='__main__':unittest.main()
