"""NEW assumed HBM power interface, cloned from same-outline source PHY rails.
No target DFI pins/OBS are edited; no vendor/analog/IR qualification is implied.
"""
import hashlib
import re
try:
    from .assumed_access import pg_layers
except ImportError:
    from assumed_access import pg_layers

def add_hbm_pg(target,source):
    def size(s):return re.search(r'SIZE ([\d.]+) BY ([\d.]+)',s).groups()
    if size(target)!=size(source):raise ValueError('HBM source/target outline mismatch')
    if pg_layers(target,'VDD') or pg_layers(target,'VSS'):raise ValueError('HBM target already exposes a power interface')
    blocks=[]
    for net in ['VDD','VSS']:
        if pg_layers(source,net)!={'M4'}:raise ValueError('HBM source must provide M4-only PG')
        blocks.append(re.search(r'(?ms)^  PIN '+net+r'\n.*?^  END '+net+r'\s*$',source)[0].rstrip())
    idx=target.index('  OBS\n')
    candidate=target[:idx]+'\n'.join(blocks)+'\n'+target[idx:]
    candidate='# ASSUMED HBM PG INTERFACE v1; declared rails only; no analog/IP/IR qualification.\n'+candidate
    receipt=dict(schema='opentallas.assumed-hbm-pg-interface.v1',status='ASSUMED_UNQUALIFIED',
      target_original_sha256=hashlib.sha256(target.encode()).hexdigest(),source_sha256=hashlib.sha256(source.encode()).hexdigest(),
      candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),width_um=size(target)[0],height_um=size(target)[1],
      area_delta_um2=0,latency_delta_cycles=0,signal_interface_delta='none',obstruction_delta='none',
      supply_interface_delta='added VDD/VSS M4 rails cloned verbatim from same-outline ot_hbm3e_phy source',
      claim='Declared external power interface only; no vendor/internal analog, IR/EM or full-die qualification.')
    return candidate,receipt
