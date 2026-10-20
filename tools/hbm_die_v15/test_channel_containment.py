import unittest
from channel_containment import channel_containment


def oracle(pl, channels):
    return sorted(n for n,v in pl.items() for m,u in pl.items() if m!=n and channels(m) and
                  u['x']<=v['x'] and v['x']+v['w']<=u['x']+u['w'] and
                  u['y']<=v['y'] and v['y']+v['h']<=u['y']+u['h'])


class ChannelContainment(unittest.TestCase):
    def test_empty_and_no_channel_parents(self):
        self.assertEqual(channel_containment({}, lambda _: []), [])
        p={'a':dict(x=0,y=0,w=10,h=10)}
        self.assertEqual(channel_containment(p,lambda _: []), [])

    def test_overlap_boundary_orientation_and_duplicate_semantics(self):
        p={'parent':dict(x=0,y=0,w=10,h=20,o='R0'),
           'other_parent':dict(x=0,y=0,w=10,h=20,o='MX'),
           'boundary':dict(x=0,y=0,w=10,h=20,o='R90'),
           'inside':dict(x=1,y=1,w=2,h=2,o='MX'),
           'partial_overlap':dict(x=9,y=19,w=2,h=2,o='R180'),
           'outside':dict(x=11,y=0,w=1,h=1,o='R0')}
        calls=[]
        def channels(n):
            calls.append(n)
            return [dict(x_um=[2,3],y_um=[0,20])] if n in ['parent','other_parent'] else []
        actual=channel_containment(p,channels)
        self.assertEqual(calls,list(p))
        self.assertEqual(actual,oracle(p,channels))
        self.assertEqual(actual.count('inside'),2)
        self.assertNotIn('partial_overlap',actual)
        # Diagnostic retains legacy bbox semantics even when the name is not
        # inside the actual carved channel, and ignores orientation metadata.
        self.assertEqual(actual.count('boundary'),2)


if __name__ == '__main__':
    unittest.main()
