#!/usr/bin/env python3
"""Separate four-edge token master sized in uarch_model before RTL."""
import json
import s81_ph_mtp_plan as M

def main():
    spec=dict(next(s for s in M.SPECS if s['master']=='dsfd_wfc_tok'))
    spec.update(master='dsfd_wfc_tok_hard',w_um=162.0,h_um=151.2,
        note='Default-off HARD_READ=1: full eight-user/16-slot token table; pin capture, '
             '16-slot bank read, eight-user select, tag/output. Four response edges, '
             '+3 cycles original/+2 r3. Model tools/uarch_model.py dsrom_wfc_token_hard_model. '
             '7145um2 measured predecessor plus880um2 register proxy; own closure required.')
    ports=M.TP.plan(spec)
    M.TP.write(spec['master'],spec['w_um'],spec['h_um'],spec['domain'],ports,spec)
    print(json.dumps(dict(master=spec['master'],outline=[162.0,151.2],pins=sum(len(p['pins']) for p in ports.values()))))
if __name__=='__main__':main()
