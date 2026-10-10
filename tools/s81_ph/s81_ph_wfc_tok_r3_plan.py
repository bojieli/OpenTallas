#!/usr/bin/env python3
"""Own-master pin plan for approved two-edge WFC token lookup; old contracts untouched."""
import json
import s81_ph_mtp_plan as M

def main():
    spec=dict(next(s for s in M.SPECS if s['master']=='dsfd_wfc_tok'))
    spec.update(master='dsfd_wfc_tok_r3',w_um=129.6,h_um=120.96,
                note='Approved +1edge SOURCE prompt lookup successor, separate master; two-edge fixed prompt read. '
                'Rounded 120um target up to10.8um width/2.16um height lattice. '
                'Measured predecessor7145um2 cells plus200um2 allowance; estimated utilisation46.9%.')
    ports=M.TP.plan(spec)
    rec=M.TP.write(spec['master'],spec['w_um'],spec['h_um'],spec['domain'],ports,spec)
    print(json.dumps(dict(master=spec['master'],outline=[spec['w_um'],spec['h_um']],pins=sum(len(p['pins']) for p in ports.values()))))
if __name__=='__main__':main()
