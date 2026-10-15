import unittest
from geometry_search import analyze, search, span

class GeometrySearchTests(unittest.TestCase):
    def test_pin_extents_and_mirror_not_centers(self):
        a=dict(n='a',m='leaf',x=0,y=0,w=10,h=20,o='R0')
        b=dict(n='b',m='leaf',x=30,y=0,w=10,h=20,o='R0')
        p=dict(face='W',range_um=[2,4])
        self.assertEqual(span(a,p,b,p),32)
        a['o']='MX'
        self.assertEqual(span(a,p,b,p),46)

    def test_missing_endpoints_are_not_zero_cost(self):
        model={'a':dict(n='a',m='leaf',x=0,y=0,w=10,h=20),'b':dict(n='b',m='leaf',x=30,y=0,w=10,h=20)}
        plans={'leaf':{'p':dict(face='W',range_um=[2,4])}}
        raw={'buses':[dict(b='known',c='data',n=8,e=[['a','p'],['b','p']]),dict(b='unknown',c='data',n=512,e=[['a','p'],['b','missing']])]}
        known,missing,incident,row=analyze(raw,model,plans)
        self.assertEqual(len(known),1);self.assertEqual(len(missing),1)
        self.assertEqual(row(known[0])['bit_um'],256)
        self.assertEqual(incident['a'],[0])

    def test_orientation_search_preserves_model_and_counts_unknown(self):
        model={'a':dict(n='a',m='leaf',x=0,y=0,w=10,h=20,o='R0'),'b':dict(n='b',m='leaf',x=30,y=0,w=10,h=20,o='R0')}
        plans={'leaf':{'p':dict(face='W',range_um=[2,4])}}
        raw={'die':dict(w=100,h=100),'buses':[dict(b='known',c='data',n=8,e=[['a','p'],['b','p']]),dict(b='unknown',c='data',n=1,e=[['a','p'],['b','bad']])]}
        known,_,incident,_=analyze(raw,model,plans)
        baseline,proposals=search(raw,model,plans,known,incident)
        self.assertEqual(baseline,256)
        best=proposals[0]
        self.assertEqual(best['group'],'a');self.assertEqual(best['value'],'MY')
        self.assertEqual(best['known_bit_um_saved'],80)
        self.assertEqual(best['unresolved_incident_nets'],1)
        self.assertEqual(model['a']['o'],'R0')
        self.assertFalse(best['qualification'])

if __name__=='__main__':unittest.main()
