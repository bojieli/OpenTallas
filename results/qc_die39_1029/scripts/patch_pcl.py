import sys
p=sys.argv[1]; s=open(p).read()
def rep(a,b):
    global s
    assert s.count(a)==1,a[:60]; s=s.replace(a,b)
rep("""def pin_entry(load, dbu, via12):
""","""LEAF_ROLE = 'clock_leaf'
LEAF_MASTERS = ('CKINVDC', 'INV')


def load_pin(load):
    \"\"\"Actual clock terminal of one inventory load: CLK of a register, or A of a leaf-driver trunk-side inverter.\"\"\"
    name, master = load['inst'], load['master']
    if load.get('role') == LEAF_ROLE:
        if load.get('pin') != 'A' or not master.startswith(LEAF_MASTERS):
            raise ValueError(f'leaf-driver clock load is not an inverter A pin: {name}')
        return 'A'
    if not master.startswith(('DFF','SDFF')):
        raise ValueError(f'provider clock load is not a sequential cell: {name}')
    if load.get('pin', 'CLK') != 'CLK':
        raise ValueError(f'provider register clock load is not its CLK pin: {name}')
    return 'CLK'


def pin_entry(load, dbu, via12):
""")
rep("inst=load['inst'], pin='CLK', net=load['net'],","inst=load['inst'], pin=load_pin(load), net=load['net'],")
rep("""        if not load['master'].startswith(('DFF','SDFF')):
            raise ValueError(f'provider clock load is not a sequential cell: {name}')
""","""        load_pin(load)
""")
open(p,"w").write(s)
