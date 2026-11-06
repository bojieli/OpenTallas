#!/usr/bin/env python3
"""Encode the optional P1 owned HC root launch using the existing F20 fields.

No calendar, transport or arithmetic qualification. The default payload retains
the legacy24-row command; owned mode requires the explicit root parameter option.
"""

def launch_payload(time,*,npos=1,wslot=1,eps=0x358637bd,global_row=None):
    if not 0<=time<1<<20 or not 1<=npos<=8 or not 0<=wslot<4 or not 0<=eps<1<<32:
        raise ValueError('HC launch time/npos/slot/eps out of range')
    if global_row is not None and (not 0<=global_row<24 or npos!=1):
        raise ValueError('owned launch requires global row0..23 and P1')
    word=time|(1<<64)|(npos<<65)|(wslot<<69)|(eps<<71)
    if global_row is not None:word|=global_row<<26
    return word


def program_word(time,*,pc=0,**fields):
    if not 0<=pc<1024:raise ValueError('HC programme pc out of range')
    return (0xc7a1<<240)|(pc<<224)|launch_payload(time,**fields)


def root_parameters(*,global_row=None):
    if global_row is not None and not 0<=global_row<24:raise ValueError('global HC row out of range')
    return dict(NOUT=24 if global_row is None else 1,WROW0=0,OROW0=0 if global_row is None else -1)
