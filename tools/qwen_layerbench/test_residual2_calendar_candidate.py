import copy
import unittest
from pathlib import Path
import dv_lower as D
import programme_store as P
import residual2_calendar_candidate as R


def manifest():
    stages=[]
    for st in range(1,37):
        slices=[]
        for sid in range(12):
            users=[]
            for u in range(4):
                args=dict(nout=3,nin=128,a=416+4096*u,aso=128,asi=1,bsrc=1,b=2048*u,bso=128,bsi=1,
                          c=4096*u,cso=128,csi=1,ma=1,ad=2,dst=1,d=4096*u,dso=128,dsi=1,red=1,redsq=1,rb=D.W_SC|sid,rso=12)
                a=D.su_word(**args);args['b']+=384;b=D.su_word(**args)
                users.append([dict(addr=i,payload_hex=f'{(a<<512) if i==0 else (b if i==1 else 0):0256x}') for i in range(6)])
            slices.append(dict(slice=sid,prog_users=users))
        stages.append(dict(stage=st,slices=slices))
    return dict(parameters=P.NATIVE_COMPACT_PARAMETERS,stages=stages)


class ResidualCallerTest(unittest.TestCase):
    def test_native_word_pidx_selects_different_actual_operand(self):
        m=manifest();self.assertEqual(R.verify_native_pair(m),1728)
        records=m['stages'][0]['slices'][0]['prog_users'][0]
        def operand(pidx):
            row=int(records[pidx>>1]['payload_hex'],16)
            word=(row>>(512*(pidx&1)))&((1<<457)-1)
            return D.su_unpack(word)['b']
        self.assertEqual((operand(1),operand(2)),(0,384))
        scale={0:1,384:2}
        self.assertEqual(1*scale[operand(2)]+1,3)
        self.assertNotEqual(1*scale[operand(1)]+1,3) # wrong original caller is causal
        bad=copy.deepcopy(m);bad['stages'][23]['slices'][4]['prog_users'][2][1]['payload_hex']='0'
        with self.assertRaisesRegex(ValueError,'layout'):R.verify_native_pair(bad)

    def test_actual_selected_calr_changes_only_twelve_phase2_pidx_fields(self):
        base=D.ROOT/'results/rtl/qe3_ctlm3_1021/selected_source/rtl/test/qwen_dv/calr_port'
        words,dw=R.decode_image(base);out,sites=R.patch(words,dw)
        self.assertEqual(len(sites),12)
        self.assertEqual({s['dst'] for s in sites},set(range(12)))
        self.assertEqual([s['index'] for s in sites],[430,433,435,436,442,445,448,451,454,457,459,460])
        self.assertEqual(sum((a^b).bit_count() for a,b in zip(words,out)),24)
        for desc in (dw[3],dw[4]):self.assertEqual(R.entries(words,desc),R.entries(out,desc))
        for lane in (0,1):
            physical=P.physical_rows(out+[0]*2048,lane)[:256]
            for a in range(2048):
                decoded=sum(((physical[a//8]>>(8*b+a%8))&1)<<b for b in range(266))
                self.assertEqual(decoded,(out[a]>>(266*lane))&((1<<266)-1))
        with self.assertRaisesRegex(ValueError,'cohort'):R.patch(out,dw) # cannot patch already-fixed data

if __name__=='__main__':unittest.main()
