"""Opt-in physical egress ABI; default static VM remains L12 until integrated.
64 independently clocked64bit router stripes,8 independently clocked valid leaves.
Input is the actual group_data/group_valid and release metadata after P+11.
R0 samples at P+12, R1 data/valid at P+13, II=1. Global fault-tree age is external.
"""
OPT_IN = 'VM_READ_ROUTER_L13'
READ_LATENCY_DEFAULT = 12
READ_LATENCY_OPT_IN = 13
# READ_PIPE 2: dsfd_vm_static_read_router_p, every leaf input pin-registered (native capture audit 2026-10-15)
OPT_IN_PINREG = 'VM_READ_ROUTER_L14'
READ_LATENCY_OPT_IN_PINREG = 14
DATA_RESET_PINS = 64
VALID_RESET_PINS = 8
DATA_ROOTS = 64
VALID_ROOTS = 8
SLOTS = 32
DATA_BITS = 512
STRIPE_BITS = 64
INIT_RESET_EDGES = 3
GLOBAL_FAULT_TREE_AGE = None

def read_latency(*, opt_in=False, pinreg=False):
    if pinreg:
        return READ_LATENCY_OPT_IN_PINREG
    return READ_LATENCY_OPT_IN if opt_in else READ_LATENCY_DEFAULT

def require_fault_age(age):
    if not isinstance(age, int) or isinstance(age,bool) or age < 0:
        raise ValueError('actual physically implemented fixed fault-tree age required')
    return age
