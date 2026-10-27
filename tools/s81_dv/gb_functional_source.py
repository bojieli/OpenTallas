"""Restore the canonical seam implementation in a physical structural-cut copy.

The selected band wiring stays byte-identical. Empty physical interface views
are not functional RTL; only the exact existing canonical seam is admitted.
"""
import hashlib
import re


def seam_module(text):
    m = re.search(r'^module s81b_fint\b.*?^endmodule\b', text, re.M | re.S)
    if not m:
        raise ValueError('s81b_fint definition absent')
    return m


def overlay(structural, canonical):
    cut, real = seam_module(structural), seam_module(canonical)
    header = cut.group().split(';', 1)[0]
    if header != real.group().split(';', 1)[0]:
        raise ValueError('seam interface differs from canonical')
    if cut.group().split(';', 1)[1].strip() != 'endmodule':
        raise ValueError('physical seam is not an empty interface; review its source explicitly')
    body = real.group()
    if not all(x in body for x in ('posedge cka', 'posedge ckb', 'b <= a', 'assign q = b')):
        raise ValueError('canonical seam does not carry its two boundary stages')
    result = structural[:cut.start()] + body + structural[cut.end():]
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
    return result, dict(structural_sha256=sha(structural), canonical_seam_sha256=sha(body),
                        functional_sha256=sha(result), band_wiring_unchanged=True,
                        boundary_edges=2, added_edges=0, production_adopted=False)
