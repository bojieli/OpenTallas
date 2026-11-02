"""Default-OFF finite reset-image obligations; never imported by the LEC gate.

An upper image proof establishes all projection correlations for every native
power-up state/input trace. A separate onto witness leaves each independent
slot coordinate free and chooses one legal initial state/input trace for other
coordinates. Proving every projected output equals that free-coordinate model
establishes surjectivity. Unknown/unknown ternary values provide no evidence.
Callers must independently validate the typed bijection/primitive controls and
prove joint next-state/output correspondence before accepting any relation.
"""
from functools import lru_cache


def reset_prefixes(d, reset):
    """Yield exact sound ternary constants after each edge, as lec.reset_state."""
    st = {}
    yield st
    while True:
        base = d['I'] + d['L'] + 1
        val = [None] * (base + d['A'])
        val[0] = 0
        for v, b in reset.items():
            val[v] = b
        for v, b in st.items():
            val[v] = b
        for k in range(d['A']):
            a, b = d['ands'][2*k:2*k+2]
            x, y = val[a >> 1], val[b >> 1]
            x = None if x is None else x ^ (a & 1)
            y = None if y is None else y ^ (b & 1)
            val[base+k] = 0 if x == 0 or y == 0 else 1 if x == y == 1 else None
        st = {}
        for i, lit in enumerate(d['latches']):
            x = val[lit >> 1]
            if x is not None:
                st[d['I'] + i + 1] = x ^ (lit & 1)
        yield st


def reset_image_miter(F, d, reset, cycles, slots, correlations, *, onto=False):
    """Build native Boolean obligations, with no hypotheses or constraints.

    slots: {semantic_name: native logical latch literal}; correlations:
    [(semantic_name, native logical load literal, slot_semantic_name)].
    onto=False proves each final load==final slot for arbitrary init/input.
    onto=True fixes only non-slot initial state and non-reset PI trace to an
    explicit legal witness; independent slot initial logical bits remain free.
    It proves slots==their own seed and loads==corresponding seed after reset.
    Both sides of an isomorphism require BOTH obligations to prove.
    """
    if type(cycles) is not int or cycles <= 0:
        raise ValueError('positive native reset edge count required')
    if not reset or any(type(v) is not int or not 1 <= v <= d['I'] or b not in (0, 1)
                        for v, b in reset.items()):
        raise ValueError('actual native reset PI/polarity required')
    sv = [lit >> 1 for lit in slots.values()]
    if len(set(sv)) != len(sv):
        raise ValueError('independent coordinates are not injective')
    loads = [lit >> 1 for _, lit, _ in correlations]
    if len(set(loads)) != len(loads) or set(loads) & set(sv):
        raise ValueError('load coordinates must be distinct from each other and slots')
    for v in sv + loads:
        if not d['I'] < v <= d['I'] + d['L']:
            raise ValueError('projection must name native latch variables')
    if any(key not in slots for _, _, key in correlations):
        raise ValueError('unknown projection correlation')
    prefixes = reset_prefixes(d, reset)
    known = [next(prefixes) for _ in range(cycles+1)]
    # A slot known after native reset cannot be an independent onto coordinate.
    if any(v in known[-1] for v in sv):
        raise ValueError('reset-fixed slot cannot have arbitrary initial image')
    m = F.Aig()
    seeds = {name: m.add_input('slot_seed:' + name) for name in slots} if onto else {}
    init = {}
    for v in range(d['I']+1, d['I']+d['L']+1):
        init[v] = known[-1].get(v, 0) if onto else m.add_input('initial:' + str(v))
    if onto:
        for name, lit in slots.items():
            init[lit >> 1] = seeds[name] ^ (lit & 1)
    pi = {(t, v): (reset[v] if v in reset else 0 if onto else m.add_input(f'pi:{t}:{v}'))
          for t in range(cycles) for v in range(1, d['I']+1)}
    base = d['I'] + d['L'] + 1

    @lru_cache(None)
    def value(t, lit):
        if lit <= 1:
            return lit
        if lit & 1:
            return value(t, lit ^ 1) ^ 1
        v = lit >> 1
        if v <= d['I']:
            return pi[t, v]
        if v < base:
            if t == 0:
                return init[v]
            if v in known[t]:
                return known[t][v]
            return value(t-1, d['latches'][v-d['I']-1])
        a, b = d['ands'][2*(v-base):2*(v-base)+2]
        x = value(t, a)
        return 0 if x == 0 else m.AND(x, value(t, b))

    def obligation(name, a, b):
        m.onames.append(name)
        m.outs.append(m.XOR(a, b))
    if onto:
        for name, lit in slots.items():
            obligation('onto_slot:' + name, value(cycles, lit), seeds[name])
    for name, lit, reference in correlations:
        obligation(('onto_load:' if onto else 'upper_load:') + name,
                   value(cycles, lit), seeds[reference] if onto else value(cycles, slots[reference]))
    return m, dict(kind='ONTO_EXPLICIT_LEGAL_WITNESS' if onto else 'UPPER_ALL_NATIVE_INIT_AND_INPUTS',
                   cycles=cycles, independent_coordinates=len(slots), load_correlations=len(correlations),
                   initial_non_slot_witness='native reset-known value, else zero' if onto else 'arbitrary',
                   nonreset_pi_witness=0 if onto else 'arbitrary_per_edge',
                   no_hypotheses=True, no_constraints=True, no_gate_integration=True)
