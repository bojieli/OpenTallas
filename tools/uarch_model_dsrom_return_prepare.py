#!/usr/bin/env python3
"""Default-off full-return extension to the unified model; original module unchanged."""
import uarch_model as U

def area_ledger(design, actual_return=False, NP=8192, R=128, NBF=1024, RD=64, ROOTD=128):
    baseline=U.area_ledger(design)
    if not actual_return:
        return baseline
    if NP != 8192 or R != 128 or NBF != 1024:
        raise ValueError('full-target model requires NP8192/R128/NBF1024')
    nodes=2*NP-R
    storage=nodes*(2*RD*65+65+1)+R*ROOTD*(65+66)
    adders=nodes+R
    out=dict(baseline)
    old=out['return_adders']
    out['return_adders']=adders*U.UNIT['fp32_add_um2']/1e6
    out['return_storage_register_proxy']=storage*U.DFF_UM2/1e6
    # Distributed return follows the source tree in the ROM field. Actual location,
    # local fan-in channels and area excluded here require the physical owner's model.
    out['rom_field_strip_used_mm2']+=out['return_adders']-old+out['return_storage_register_proxy']
    out['fits']=bool(out['rom_field_strip_used_mm2'] <= out['rom_field_strip_avail_mm2'] and out['hub_logic_mm2'] <= out['hub_avail_mm2'])
    out['actual_return_scope']='Exact NP8192/R128/NBF1024 topology; conditional DFF/register implementation proxy plus unified adder unit. Queue/control/mux/clock/CDC/routing excluded. No physical qualification/adoption.'
    return out
