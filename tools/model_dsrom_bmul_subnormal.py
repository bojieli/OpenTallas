#!/usr/bin/env python3
"""Analytical opt-in BF product repair model; exhaustive static categories, no HDL build."""
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bf_spec',ROOT/'tools/dsrom_actual_element_numerical_oracle.py');O=importlib.util.module_from_spec(spec);spec.loader.exec_module(O)
def decode(code):
    e=(code>>7)&255;m=code&127
    if e:return (128+m,e-127)
    p=max(0,m.bit_length()-1);return (m<<(7-p),-133+p)
def corrected_encode(sign,biased,sig):
    """Proposed s4 finite nonzero product path; existing nf/overflow/zero guards precede."""
    if biased>=1:return (sign<<31)|(biased<<23)|(sig&0x7fffff)
    shift=1-biased
    if shift>=25:return 0
    main=sig>>shift;guard=(sig>>(shift-1))&1;sticky=bool(sig&((1<<(shift-1))-1))
    rounded=main+int(guard and (sticky or main&1))
    return ((sign<<31)|rounded) if rounded else 0

def proof():
    finite=0;nonfinite=0;zeros=0
    for code in range(65536):
        if ((code>>7)&255)==255:nonfinite+=1;continue
        sig,e=decode(code);value=Fraction(sig)*O.pow2(e-7)*(-1 if code&0x8000 else 1)
        assert value==O.f32(code<<16);finite+=1;zeros+=int(sig==0)
    cats={str(sh):{'pairs':0,'ties':0,'rounded_zero':0,'increment':0} for sh in range(1,26)}
    tests=0
    for sa in range(128,256):
        for sb in range(128,256):
            product=sa*sb;sig=product<<(8 if product&32768 else 9)
            for sh in range(1,26):
                cat=cats[str(sh)];cat['pairs']+=1
                exact=Fraction(sig,1<<sh);q,r=divmod(exact.numerator,exact.denominator)
                # Independent rational nearest-even, then encode in FP32 subnormal LSB units.
                rounded=q+int(r*2>exact.denominator or (r*2==exact.denominator and q&1))
                cat['ties']+=int(r*2==exact.denominator);cat['rounded_zero']+=int(rounded==0);cat['increment']+=int(rounded!=q)
                for sign in (0,1):
                    expected=((sign<<31)|rounded) if rounded else 0
                    assert corrected_encode(sign,1-sh,sig)==expected;tests+=1
    # Deep-underflow categories collapse to zero since every normalized sig<2**24.
    deep=0
    for shift in range(25,141):
        for sign in (0,1):
            for sig in (0x800000,0xfe0100,0xffffff):
                assert Fraction(sig,1<<shift)<Fraction(1,2)
                assert corrected_encode(sign,1-shift,sig)==0;deep+=1
    witnesses=[]
    for a,b in [(0x0080,0x3380),(0x0080,0x0080),(0x0080,0x3b80),(0x0080,0x3c00),(0x0080,0x3400),(0x0080,0x3381),(0x8080,0x3380)]:
        sa,ea=decode(a);sb,eb=decode(b);pq=sa*sb;be=ea+eb+(128 if pq&32768 else 127);sig=pq<<(8 if pq&32768 else 9)
        got=corrected_encode((a^b)>>15,be,sig);expected=O.mul(a<<16,b<<16);assert got==expected
        witnesses.append(dict(a=f'{a:04x}',b=f'{b:04x}',biased_exponent=be,shift=1-be,corrected=f'{got:08x}',independent_golden=f'{expected:08x}'))
    # Arbitrary normalized sig guard checks, even beyond the BF product lattice.
    assert corrected_encode(0,0,0xffffff)==0x00800000 # RNE carry into minimum normal
    return dict(status='STATIC_CATEGORY_PROOF_PASS_NOT_RTL_PASS',BF_decode_codes=65536,finite_decode_codes=finite,nonfinite_classified=nonfinite,zero_codes=zeros,normalized_significand_pairs=16384,shift_categories=cats,sign_checks=tests,deep_underflow_boundary_checks=deep,witnesses=witnesses,proof_scope='All BF16 decodes; all128x128 normalized BF significand products for every subnormal shift1..25 and both result signs; algebraic bound plus extrema for25..140. Exponents/sign combinations covered by reduction to these categories, not all2**32 BF input pairs. Existing nonfinite/overflow refusal retained. Not compiled RTL or full arithmetic qualification.')
if __name__=='__main__':print(json.dumps(proof(),indent=2,sort_keys=True))
