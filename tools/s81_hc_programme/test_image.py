import copy
import unittest
import image

class ImageTests(unittest.TestCase):
    def command(self,op=127):
        return dict(op=op,y_tag=0x12345678,scalar_age=1,ss_age=42,done_age=20000,post_ages=list(range(100,120)),stream_issue=4)

    def test_full_last_op_and_twenty_literal_ages(self):
        words=image.encode([self.command()])
        self.assertEqual(len(words),4096)
        bundle=sum(words[127*11+i]<<(72*i)for i in range(11))
        self.assertEqual(bundle&0xffffffff,0x12345678)
        self.assertEqual((bundle>>96)&0xffffffff,20000)
        self.assertEqual([(bundle>>(128+32*i))&0xffffffff for i in range(20)],list(range(100,120)))
        self.assertEqual(bundle>>768,0)
        self.assertFalse(any(words[:127*11]+words[128*11:]))

    def test_missing_duplicate_width_and_phase_fail(self):
        c=self.command()
        for changed in [dict(c,post_ages=[1]*19),dict(c,done_age=-1),dict(c,op=128),dict(c,y_tag=True)]:
            with self.assertRaises(ValueError):image.encode([changed])
        with self.assertRaises(ValueError):image.encode([c,c])
        for bad in [[dict(c,stream_issue=1)],[c,dict(c,stream_issue=24)]]:
            with self.assertRaises(ValueError):image.validate_issue_edges(bad)
        self.assertEqual(image.validate_issue_edges([c,dict(c,stream_issue=28)]),[dict(stream_issue=4,serial_delivery=17),dict(stream_issue=28,serial_delivery=35)])

    def test_actual_mailbox_phase_ages(self):
        # Serial output edges17,18,19; source mailbox samples on18,19,20.
        self.assertEqual([image.endpoint_done_edge(0,d)for d in (3,4,5)],[27,28,29])
        with self.assertRaises(ValueError):image.endpoint_done_edge(1,3)

if __name__=='__main__':unittest.main()
