#!/usr/bin/env python3
"""Exact declared-state price of selected CTL VM calendar; no source activation."""
import argparse,json

def state(read=88,write=85,lwb=15):
    if read<0 or write<0 or lwb<1: raise ValueError('nonnegative calendar and positive LWB required')
    metadata=2+4+2*lwb+2+6
    fields={'scalar_addr_pipe':96*(read+1),'four_region_meta':4*metadata*(read+1),
            'four_write_expected':8*(write+2),'write_q':2248,'drain_expected':8,
            'drain_sector_q':128,'drain_round_q':8,'fault_state':5}
    return dict(read=read,write=write,lwb=lwb,fields=fields,VM_FF=sum(fields.values()),CTL_direct_FF=8933,CTL_relay_FF=6,CTL_total_FF=sum(fields.values())+8933+6)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--read',type=int,default=88);p.add_argument('--write',type=int,default=85);a=p.parse_args()
    base=state();new=state(a.read,a.write)
    print(json.dumps(dict(baseline=base,candidate=new,VM_delta_FF_per_CTL=new['VM_FF']-base['VM_FF'],paired_CTL_delta_FF=2*(new['VM_FF']-base['VM_FF']),qualification='Exact selected declarations, not mapped cells. Candidate dates are caller supplied and unadopted. No blind addition of physical distance minima to existing88/85 calendar.'),indent=1))
if __name__=='__main__':main()
