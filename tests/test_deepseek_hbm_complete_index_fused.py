from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_fused as F
import deepseek_hbm_complete_index_consumer as C
class Fused(unittest.TestCase):
    def test_finite_actualsource_and_exceptional_weights_fullmacro(self):
        rng=np.random.default_rng(20261001)
        q=np.stack([F.C.V.qdq_fp4_e8m0(rng.normal(size=128).astype(np.float32)) for _ in range(32)])
        keys=np.stack([F.C.V.qdq_fp4_e8m0(rng.normal(size=128).astype(np.float32)) for _ in range(64)])
        weights=np.ones(32,np.float32);weights.view(np.uint32)[::8]=[0x7fc10000,0xffc20000,0x7f800000,0xff800000]
        prepared=F.prepare_query(q)
        with np.errstate(invalid='ignore'):
            got,receipt=F.scores(q,keys,weights,5456,True,prepared)
            expected=C.reference_scores(q,keys[np.arange(5456)%64],weights,np.arange(5456))[:64]
        self.assertTrue(np.array_equal(got.astype(np.float64).view(np.uint64),expected.view(np.uint64)))
        self.assertEqual(receipt['path'],'finite fused ordinary GPU shader')
        self.assertEqual(receipt['fused_kernel'].metrics['shared_warp_issues'],17024)
        q2=q.copy();q2[0,0]=0
        with self.assertRaises(ValueError):F.scores(q2,keys,weights,5456,True,prepared)
    def test_large_finite_products_and_actual_scale253_exception(self):
        raw=np.zeros(128,np.float32);raw[0]=np.float32(2.**100);raw[1]=-raw[0]
        kraw=np.zeros(128,np.float32);kraw[:2]=np.float32(2.**100)
        q=np.tile(F.C.V.qdq_fp4_e8m0(raw),(32,1));keys=np.tile(F.C.V.qdq_fp4_e8m0(kraw),(2,1));w=np.ones(32,np.float32)
        got,r=F.scores(q,keys,w,5464,True)
        ref=C.reference_scores(q,np.tile(keys,(2732,1)),w,np.arange(5464))[:2]
        self.assertTrue(np.array_equal(got.astype(np.float64).view(np.uint64),ref.view(np.uint64)))
        raw[0]=np.finfo(np.float32).max
        with np.errstate(over='ignore'):q=np.tile(F.C.V.qdq_fp4_e8m0(raw),(32,1))
        with np.errstate(invalid='ignore'):
            got,r=F.scores(q,keys,w,5464,True)
            ref=C.reference_scores(q,np.tile(keys,(2732,1)),w,np.arange(5464))[:2]
        self.assertEqual(r['path'],'ordinary exceptional continuation')
        self.assertTrue(np.array_equal(got.astype(np.float64).view(np.uint64),ref.view(np.uint64)))
        self.assertEqual(r['FP64_arithmetic'],0)
    def test_actual_tails_subnorm_signedzero_and_finite253(self):
        rows=[]
        for e in [-126,-120,-50,0,100,125,126]:
            raw=np.resize(np.array([0.,-0.,.5,-.5,1,-1,1.5,-1.5,2,-2,3,-3],np.float64)*2.**e,128).astype(np.float32)
            for block in range(4):raw[block*32+31]=np.float32((3.125 if e==126 else 6)*2.**e)
            raw[1]=-np.nextafter(np.float32(0),np.float32(1))
            rows.append(F.C.V.qdq_fp4_e8m0(raw))
        q=np.array([rows[i%len(rows)] for i in range(32)])
        prepared=F.prepare_query(q);self.assertFalse(prepared.exceptional)
        # This actual producer row reaches253 without decodedInf.
        packed,decoded,_=F.C.quantize_pack(np.array([raw]))
        self.assertEqual(int(packed[0,64]),253);self.assertTrue(np.all(np.isfinite(decoded)))
        keys=np.array([rows[i%len(rows)] for i in range(64)]);w=np.linspace(-2,3,32,dtype=np.float32)
        for tail,n in [(16,5456),(24,5464),(40,10920),(48,10928)]:
            with np.errstate(over='ignore',invalid='ignore'):
                got,r=F.scores(q,keys[:tail],w,n,True,prepared)
                expected=C.reference_scores(q,keys[np.arange(n)%64],w,np.arange(n))[:tail]
            self.assertTrue(np.array_equal(got.astype(np.float64).view(np.uint64),expected.view(np.uint64)))
            self.assertEqual(r['path'],'finite fused ordinary GPU shader')
    def test_decoder_masks_dead_padding_and_cache_version(self):
        values=np.zeros((2,32),np.float32);values[:,0]=1
        got,e,run=F.decode_owned(values);expected,ee,_=F.X.decode(values)
        self.assertTrue(np.array_equal(got,expected));self.assertTrue(np.array_equal(e,ee))
        self.assertEqual(run.counts['STORE'],32)
        q=np.ones((32,128),np.float32);prepared=F.prepare_query(q)
        with self.assertRaises(ValueError):prepared.units[0].flags.writeable=True
        self.assertEqual(F.scores(q,np.ones((2,128),np.float32),np.ones(32,np.float32),5456,True,prepared)[0].tolist(),[4096.,4096.])

class Proof(unittest.TestCase):
    def test_exhaustive_code_scale_lattice_and_costs(self):
        import deepseek_hbm_complete_index_fused_model as M
        proof=M.lattice_proof()
        self.assertEqual(proof['enumerated_pairs'],253*16)
        self.assertGreater(proof['excluded_actual_decoded_nonfinite_pairs'],0)
        model=M.model()
        self.assertFalse(model['hardware_admitted'])
        self.assertTrue(model['candidate_extent_fits_64KiB'])
        self.assertEqual(model['SM0_local2_invocations_all8calls'],1113)
        self.assertLess(model['finite_steady_shared_issues_per_SM_local2'],2574)
    def test_finite_weights_and_mixed_key_fallback(self):
        q=np.ones((32,128),np.float32);keys=np.ones((2,128),np.float32);w=np.linspace(-1,2,32,dtype=np.float32)
        for exceptional in [False,True]:
            if exceptional:keys.view(np.uint32)[1,0]=0x7fc12300
            with np.errstate(invalid='ignore'):
                got,r=F.scores(q,keys,w,5456,True)
                expected=C.reference_scores(q,keys[np.arange(5456)%2],w,np.arange(5456))[:2]
            self.assertTrue(np.array_equal(got.astype(np.float64).view(np.uint64),expected.view(np.uint64)))
            self.assertEqual(r['path'],'ordinary exceptional continuation' if exceptional else 'finite fused ordinary GPU shader')
    def test_finite_inputs_opposite_block_overflow_source_nan(self):
        raw=np.full(128,np.float32(2.**100));q=np.tile(F.C.V.qdq_fp4_e8m0(raw),(32,1))
        raw[32:64]*=-1;keys=np.tile(F.C.V.qdq_fp4_e8m0(raw),(2,1));w=np.ones(32,np.float32)
        self.assertTrue(np.all(np.isfinite(q)) and np.all(np.isfinite(keys)))
        with np.errstate(over='ignore',invalid='ignore'):
            got,r=F.scores(q,keys,w,5456,True)
            expected=C.reference_scores(q,keys[np.arange(5456)%2],w,np.arange(5456))[:2]
        self.assertTrue(np.array_equal(got.astype(np.float64).view(np.uint64),expected.view(np.uint64)))
        self.assertEqual(r['path'],'finite fused ordinary GPU shader')
        self.assertTrue(np.all(np.isnan(got)))
    def test_finite_is_not_arbitrary_f32_admission(self):
        q=np.ones((32,128),np.float32);q[0,0]=np.float32(1.123)
        with self.assertRaises(ValueError):F.prepare_query(q)

class FactoryAuthority(unittest.TestCase):
    def test_rehashed_foreign_cache_clone_and_revocation(self):
        import dataclasses,hashlib,copy
        q=np.ones((32,128),np.float32);keys=np.ones((2,128),np.float32);w=np.ones(32,np.float32)
        p=F.prepare_query(q);u=tuple(np.zeros_like(a) for a in p.units)
        fake=dataclasses.replace(p,units=u,decoded_hash=hashlib.sha256(b''.join(a.tobytes() for a in u+p.exponents)).hexdigest())
        for foreign in [fake,dataclasses.replace(p),copy.copy(p),copy.deepcopy(p)]:
            with self.assertRaisesRegex(ValueError,'foreign cloned'):F.scores(q,keys,w,5456,True,prepared=foreign)
        got,_=F.scores(q,keys,w,5456,True,prepared=p)
        self.assertEqual(got.tolist(),[4096.,4096.])
        F.release_query(p)
        with self.assertRaisesRegex(ValueError,'expired'):F.scores(q,keys,w,5456,True,prepared=p)
        fresh=F.prepare_query(q);self.assertGreater(fresh.epoch,p.epoch)
        self.assertEqual(F.scores(q,keys,w,5456,True,prepared=fresh)[0].tolist(),[4096.,4096.])
    def test_identity_preserving_rehash_cannot_override_registry(self):
        import hashlib
        q=np.ones((32,128),np.float32);p=F.prepare_query(q)
        altered=tuple(a.copy() for a in p.units);altered[0][0,0]=0
        object.__setattr__(p,'units',altered)
        object.__setattr__(p,'decoded_hash',hashlib.sha256(b''.join(a.tobytes() for a in p.units+p.exponents)).hexdigest())
        with self.assertRaisesRegex(ValueError,'factory query metadata'):F.scores(q,np.ones((2,128),np.float32),np.ones(32,np.float32),5456,True,prepared=p)
