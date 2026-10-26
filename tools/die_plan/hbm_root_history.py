#!/usr/bin/env python3
"""Reproduce the 1a20967 HBM ROOT history/correspondence diagnosis.

Run inside ORFS on an existing {gold,gate}.{aig,map}, hyp.json snapshot;
this does not rebuild RTL, change the canonical LEC verdict, or waive points.
The fixed register map belongs to ot_hgi_coll_tkm_m_tp192__root_6a18a3e72633.
Every history assumption is proved from reset and by induction before use.
The three-cycle config invariant is deliberately NOT claimed one-inductive.
"""
import argparse
import collections
import itertools
import json
import os
from pathlib import Path
import lec

PRE = 'ff:u_dut.u_fcore.u_core.u_x.'
IDS = [60435,60411,60440,60407,60433,60413,60442,60405,
       60437,60415,60444,60409,60434,60417,60446,60406]
VALUES = [64755,64731,64760,64727,64753,64733,64762,64725,
          64757,64735,64764,64729,64754,64737,64766,64726]


def conjunction(m, lits):
    result = 1
    for lit in lits:
        result = m.AND(result, lit)
    return result


def member(m, lits, allowed):
    result = 0
    for values in allowed:
        cube = conjunction(m, [lit ^ (value ^ 1) for lit,value in zip(lits,values)])
        result = m.AND(result ^ 1, cube ^ 1) ^ 1
    return result


def config_history(aig, points):
    """Full golden transition graph, arbitrary initial state and fresh PIs each step."""
    m = lec.Aig()
    ni, nl = aig['I'], aig['L']
    state = [m.add_input(f'initial:{i}') for i in range(nl)]
    pis = [[m.add_input(f'pi:{t}:{i}') for i in range(ni)] for t in range(5)]
    history = []
    for t in range(5):
        mapping = {0:0}
        mapping.update({2*(i+1):v for i,v in enumerate(pis[t])})
        mapping.update({2*(ni+i+1):v for i,v in enumerate(state)})
        def evaluate(lit):
            return mapping[lit & ~1] ^ (lit & 1)
        def current(key):
            return evaluate(points[PRE+key])
        pipe = [current(f'_70908_[{b}]') for b in range(3)]
        onehot = conjunction(m,[m.AND(pipe[i],pipe[j]) ^ 1
                               for i in range(3) for j in range(i)])
        anypipe = conjunction(m,[x ^ 1 for x in pipe]) ^ 1
        setup = m.AND(anypipe, m.AND(current('_70860_[0]'),current('u.busy')) ^ 1) ^ 1
        history.append(m.AND(onehot,setup))
        for i in range(aig['A']):
            x,y = aig['ands'][2*i:2*i+2]
            mapping[2*(ni+nl+i+1)] = m.AND(evaluate(x),evaluate(y))
        state = [evaluate(lit) for lit in aig['latches']]
    reset = points['pi:rst_n[0]']
    reset0 = pis[0][(reset >> 1)-1] ^ (reset & 1) ^ 1
    m.outs = [m.AND(reset0,history[k] ^ 1) for k in (1,2,3)]
    m.onames = [f'CONFIG_RESET_BASE_t{k}' for k in (1,2,3)]
    m.outs.append(m.AND(conjunction(m,history[:3]),history[3] ^ 1))
    m.onames.append('CONFIG_SETUP_3_induction')
    return m


def profile(model, original):
    model.hyp = {(side,key):tuple(value) for side,key,value in original}
    for b in (0,1,2,27,28,29,30):
        model.hyp[('gold',PRE+f'_70864_[{b}]')] = ('eq','gold',PRE+'_70860_[1]',0)
    model.hyp[('gold',PRE+'_70864_[31]')] = ('const',0)
    model.hyp[('gold',PRE+'_70867_[0]')] = ('eq','gold',PRE+'_70860_[0]',0)
    for family,registers in (('ids',IDS),('values',VALUES)):
        for word,register in enumerate(registers):
            for bit in range(32):
                model.hyp[('gate',PRE+f'_{register}_[{bit}]')] = (
                    'eq','gold',PRE+f'u.{family}[{word}][{bit}]',0)
    # dec_el encodes ~s_[1:0] only in valid elements; all region bits are zero.
    # These same-slot tag/valid correlations are needed even among matched FFs.
    for register in range(70917,70925):
        for word in range(4):
            for bit,one in ((1,not (word & 1)),(2,word < 2),(85,False)):
                key = PRE+f'_{register}_[{86*word+bit}]'
                valid = PRE+f'_{register}_[{86*word+84}]'
                side = 'both' if key in model.tp else 'gold'
                model.hyp[(side,key)] = ('eq','gold',valid,0) if one else ('const',0)
    constraints = [
        ('gold',[PRE+'_70908_[2]',PRE+'_70893_[0]'],[[0,0],[0,1],[1,1]]),
        ('gold',[PRE+'u.busy',PRE+'_70893_[0]',PRE+'_70860_[0]'],
         [[b,q,f] for b,q,f in itertools.product((0,1),repeat=3) if not(b and not q and not f)]),
        # Distinct first keys preserve the canonical fail-closed obligation labels.
        ('gold',[PRE+'_70890_[0]',PRE+'u.busy']+
         [PRE+f'_70908_[{b}]' for b in range(3)]+[PRE+'_70860_[0]'],
         [list(v) for v in itertools.product((0,1),repeat=6)
          if not v[1] or any(v[2:5]) or v[0] != v[5]])]
    hkeys = [PRE+f'_70908_[{b}]' for b in range(3)]+[PRE+'_70860_[0]',PRE+'u.busy']
    hallowed = [list(v) for v in itertools.product((0,1),repeat=5)
                if sum(v[:3]) <= 1 and (not any(v[:3]) or v[3] and v[4])]
    model.cons = constraints+[('gold',hkeys,hallowed)]
    return constraints, 'cons:gold:'+hkeys[0]


def run(args):
    source,out = args.snapshot.resolve(),args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    (out/'status.json').write_text(json.dumps({'status':'RUNNING','equivalence_claim':False})+'\n')
    if args.solver_path:
        os.environ['LEC_SOLVER_PATH'] = str(args.solver_path.resolve())
    original = json.loads((source/'hyp.json').read_text())
    ingress = {PRE+f'_70864_[{b}]' for b in (0,1,2,27,28,29,30,31)}
    # The retained hyp.json may already include the eight proved ingress hints.
    original = [row for row in original if not (row[0] == 'gold' and row[1] in ingress)]
    if len(original) != 213:
        raise lec.LecError('expected 213 base relations, optionally plus eight ingress hints')
    gold,gate = lec.read_aig(source/'gold.aig'),lec.read_aig(source/'gate.aig')
    gm,tm = lec.read_map(source/'gold.map'),lec.read_map(source/'gate.map')
    model = lec.Lec(gold,gm,gate,tm)
    constraints,history_name = profile(model,original)
    if args.ordinary_correspondence:
        model.cons = []
        for tail,value in (('_70890_[0]',0),('_70893_[0]',1),('_70860_[0]',1),('_70867_[0]',1)):
            key = PRE+tail
            side = 'both' if key in model.tp else 'gold'
            model.hyp[(side,key)] = ('const',value)
    log = []
    def prove(m,tag,required=True):
        result = lec.prove(m,out,1000,log,tag=tag,single_cap=30)
        (out/(tag+'.json')).write_text(json.dumps(result,indent=1)+'\n')
        (out/'proof.log').write_text('\n'.join(log))
        print(tag,dict(collections.Counter(result.values())),flush=True)
        if required and (not result or any(v != 'proved' for v in result.values())):
            raise lec.Unproven(tag+' contains a failed or undecided obligation')
        return result
    if not args.ordinary_correspondence:
        prove(config_history(gold,lec.key_points(gold,gm)[0]),'config_history')
        base = lec.Lec(gold,gm,gate,tm)
        m,_ = base.build(with_compare=False,with_hyp=False)
        reset0 = 2*(m.inames.index('pi:rst_n[0]')+1) ^ 1
        m.outs = [m.AND(reset0,member(m,[base.dlit[(side,key)] for key in keys],allowed) ^ 1)
                  for side,keys,allowed in constraints]
        m.onames = ['RESET_BASE:'+keys[0] for side,keys,allowed in constraints]
        prove(m,'other_history_reset_bases')
    m,_ = model.build(with_compare=False,with_hyp=True)
    # The omitted next-state obligation is independently proved by THREE-induction above.
    ids = [i for i,name in enumerate(m.onames) if name != history_name]
    m.outs,m.onames = [m.outs[i] for i in ids],[m.onames[i] for i in ids]
    prove(m,'joint_correspondence')
    if args.emit_hints:
        args.emit_hints.write_text(json.dumps([[side,key,list(value)]
            for (side,key),value in sorted(model.hyp.items())],indent=1)+'\n')
    if args.proofs_only:
        (out/'status.json').write_text(json.dumps({'status':'PROOFS_ONLY','equivalence_claim':False})+'\n')
        return 0
    m,_ = model.build(with_compare=True,with_hyp=False)
    ids = [i for i,name in enumerate(m.onames) if not name.startswith('cons:')]
    m.outs,m.onames = [m.outs[i] for i in ids],[m.onames[i] for i in ids]
    result = prove(m,'actual_compare',required=False)
    complete = bool(result) and all(v == 'proved' for v in result.values())
    (out/'status.json').write_text(json.dumps({'status':'EQUIVALENT' if complete else 'UNPROVEN',
        'counts':dict(collections.Counter(result.values())), 'canonical_lec_verdict_changed':False},indent=1)+'\n')
    return 0 if complete else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--proofs-only',action='store_true')
    parser.add_argument('--ordinary-correspondence',action='store_true',
                        help='replace history with four source-derived, jointly proved constants')
    parser.add_argument('--emit-hints',type=Path,help='emit canonical untrusted-hint JSON only after joint proof')
    parser.add_argument('--solver-path',type=Path,help='optional matching Python pycryptosat directory')
    try:
        raise SystemExit(run(parser.parse_args()))
    except (lec.LecError,lec.Unproven) as error:
        parser.exit(2,str(error)+'\n')
