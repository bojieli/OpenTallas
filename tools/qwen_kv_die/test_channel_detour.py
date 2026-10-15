import unittest
import channel_detour


class DetourTest(unittest.TestCase):
    def test_real_obstacle_requires_initially_increasing_remaining_distance(self):
        source,target=(100.,80.),(20.,80.)
        obstacle=(40.,40.,100.,160.)
        result=channel_detour.route(source,target,[obstacle],(200.,200.),8.,8.,10.,45.,gap=1.)
        self.assertIsNotNone(result)
        distance=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
        self.assertGreater(distance(result['stages'][0]['output'],target),distance(source,target))
        prior=source;rects=[]
        for stage in result['stages']:
            self.assertLessEqual(distance(prior,stage['input']),45.)
            x,y=stage['x'],stage['y']
            self.assertTrue(x+8<=40 or x>=100 or y+8<=40 or y>=160)
            for a,b,c,d in rects:
                self.assertTrue(x+8+1<=a or c+1<=x or y+8+1<=b or d+1<=y)
            rects.append((x,y,x+8,y+8));prior=stage['output']
        self.assertLessEqual(distance(prior,target),45.)
        for path in [s['wire']for s in result['stages']]+[result['tail_wire']]:
            for a,b in zip(path,path[1:]):
                self.assertTrue(a[0]==b[0]or a[1]==b[1])
                if a[0]==b[0]:
                    self.assertFalse(40<a[0]<100 and min(max(a[1],b[1]),160)>max(min(a[1],b[1]),40))
                else:
                    self.assertFalse(40<a[1]<160 and min(max(a[0],b[0]),100)>max(min(a[0],b[0]),40))

    def test_sealed_channel_is_refused(self):
        result=channel_detour.route((100.,80.),(20.,80.),[(40.,0.,100.,200.)],
            (200.,200.),8.,8.,10.,45.,gap=1.)
        self.assertIsNone(result)


if __name__=='__main__':unittest.main()
