"""Finite E4M3 input markers for the selected posted formatter. No arithmetic producer claim."""
from fractions import Fraction
import struct
def fp8_to_fp32_bits(code):
 if not isinstance(code,int) or not 0<=code<=255: raise ValueError("FP8 byte required")
 sign=(code>>7)&1;e=(code>>3)&15;m=code&7
 if e==15 and m==7:raise ValueError("nonfinite FP8 code excluded by selected formatter")
 if e==0 and m==0:return sign<<31
 value=Fraction(m,512) if e==0 else Fraction(8+m,8)*Fraction(2)**(e-7)
 if sign:value=-value
 return int.from_bytes(struct.pack(">f",float(value)),"big")
