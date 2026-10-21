#!/usr/bin/env python3
"""Persist same-edge unreset producer copies for measured hw alias loads."""
from pathlib import Path
import argparse,re,json,hashlib

def transform(text):
    original=text
    m=re.search(r'assign hw = \{([^;]+)\};',text)
    assert m,'exact constructor hw concatenation missing'
    bits=m.group(1).split(',');assert len(bits)==1567
    newbits=list(bits);extra=[];groups=[]
    for f in range(5):
        q=f'n_{2028+f}';d=f'n_{3177+f}';inst=114+f
        ff=f'(* keep=1, keep_hierarchy="yes" *) qfd_s8tap_bmath_dff_p #(.ID(0)) u_{inst}(.C(n_2),.D({d}),.Q({q}));'
        assert text.count(ff)==1,'exact unreset C/D/Q producer changed'
        places=sorted(1566-j for j,v in enumerate(bits) if v==q)
        assert places==list(range(479+12*f,491+12*f)),places
        assert len(re.findall(r'\b'+q+r'\b',text))==14,'unexpected nonalias consumer'
        qs=[q]+[f'{q}_hwcopy{c}' for c in range(1,4)]
        for c in range(1,4):
            extra.append(f'wire {qs[c]};')
            extra.append(f'(* keep=1, keep_hierarchy="yes" *) qfd_s8tap_bmath_dff_p #(.ID({10000+4*f+c})) u_hwcopy_{inst}_{c}(.C(n_2),.D({d}),.Q({qs[c]}));')
        for a,bit in enumerate(places):newbits[1566-bit]=qs[a//3]
        groups.append(dict(original_instance=f'u_{inst}',original_q=q,C='n_2',D=d,reset=None,hw_bits=places,copies=qs,aliases_per_copy=3,predicted_MAIN_loads=12,predicted_FALLBACK_loads=24))
    text=text[:m.start(1)]+','.join(newbits)+text[m.end(1):]
    marker='\n// Exact existing-edge TAP aliases: independent cold-state validity requires\n// the qualified existing parent reset/landing grace; no reset or mask added.\n'+'\n'.join(extra)+'\n'
    pos=text.index('endmodule');text=text[:pos]+marker+text[pos:]
    # Exact restoration certificate: every original equation/FF survives untouched.
    restored=text.replace(marker,'',1);mm=re.search(r'assign hw = \{([^;]+)\};',restored)
    restored=restored[:mm.start(1)]+m.group(1)+restored[mm.end(1):]
    assert restored==original
    return text,dict(groups=groups,added_scalar_unreset_flops=15,added_cycles=0,original_C_D_Q_equations_preserved=True,exact_delta_restoration_byte_identical=True,qualification='CONSTRUCTION_ONLY; requires executed source body/causal proof and combined actual native census',cold_grace_receipt='results/arch/codex_slice2_native_1021/resume1340/tap_copy_grace/pass_d576/receipt.json')

def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--record',required=True);a=p.parse_args()
    f=Path(a.source);old=f.read_text();new,record=transform(old);f.write_text(new)
    record.update(input_sha256=hashlib.sha256(old.encode()).hexdigest(),output_sha256=hashlib.sha256(new.encode()).hexdigest())
    Path(a.record).write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
