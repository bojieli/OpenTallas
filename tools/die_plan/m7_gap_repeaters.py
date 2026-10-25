#!/usr/bin/env python3
"""Inactive SU M7 repeater proposal: project inserted buffers into real gap rows.

Call after repair_design and before detailed_placement, in both prototype and
production. A caller must capture newly inserted BUF/INV IDs and their intended
locations before legalization; pre-existing cells and all flop sites are fixed.
This geometry kernel does not add registers, change OBS, or authorize routing.
"""
import math


def gap_bands(type_raw, clearance=2.0):
    cores=type_raw.get('hard_cores',[])
    if not cores or any(c.get('obs_max')!='M6' for c in cores):
        raise ValueError('proposal requires actual M6-blocked hard cores')
    width,height=type_raw['outline_um']
    blocked=sorted((c['origin_um'][1],c['origin_um'][1]+c['outline_um'][1]) for c in cores)
    bands=[];lo=4.32
    for a,b in blocked:
        if a-clearance>lo:bands.append((lo,a-clearance))
        lo=max(lo,b+clearance)
    if lo<height-4.32:bands.append((lo,height-4.32))
    if not bands:raise ValueError('no real gap rows')
    return bands


def project(type_raw, x, y, cell_width=1.08, cell_height=.27, row=.27):
    """Keep the M7 ribbon x; move only to a legal gap row. Return a proposal.

    A placement adapter must legalize occupancy inside these bands and fail if
    it cannot retain x within a small local displacement. It must not send the
    instance to a side strip as a fallback. Do not infer x from the FAILED
    post-DPL location: the original repair coordinate is required.
    """
    width,height=type_raw['outline_um']
    if not 4.32<=x<=width-4.32-cell_width:raise ValueError('ribbon x outside legal core')
    sites=[]
    for lo,hi in gap_bands(type_raw):
        first=math.ceil(lo/row)*row;last=math.floor((hi-cell_height)/row)*row
        if first<=last:sites.append(min(max(round(y/row)*row,first),last))
    if not sites:raise ValueError('no row fits repeater')
    return x,min(sites,key=lambda py:abs(py-y))
