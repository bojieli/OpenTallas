"""Typed, hash-bound die infrastructure is distinct from arbitrary unregistered data."""
import copy
import hashlib
import json
from pathlib import Path
import re
import geom_rules as G


def digest(decl):
    body=dict(ports=sorted(decl['ports'],key=lambda p:p['name']),arcs=sorted(decl['arcs'],key=lambda a:(a['source'],a['sink'])))
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def vehicle(tmp_path,role='clock'):
    p=tmp_path/'dump.tsv';p.write_text('D\t0\t0\t100\t100\n'
        'C\t1\tB\tBUFx2_ASAP7_75t_R\t10\t10\t11\t11\tbuf\n'
        'C\t2\tS\tDFF\t20\t20\t21\t21\tff\n'
        'P\t0\ta\tINPUT\tSIGNAL\tM4\t0\t10\n'
        'P\t1\tz\tOUTPUT\tSIGNAL\tM4\t100\t10\n'
        'N\tSIGNAL\tp0\ti1\nN\tSIGNAL\ti1\tp1\n')
    decl=dict(schema='opentallas.ft_ports.v1',source='core_infra_plan.json',
              ports=[dict(name='a',direction='INPUT'),dict(name='z',direction='OUTPUT')],
              arcs=[dict(source='a',sink='z',kind=role,cells=['buf'])])
    decl['sha256']=digest(decl)
    model=dict(schema='opentallas.ft_interface_model.v1',ft_sha256=decl['sha256'],status='declared',
               arcs=[dict(source='a',sink='z',kind=role,tt_ps=None,ff_ps=None)])
    return G.Design(p),model,decl


def test_clock_and_reset_equivalence_keep_explicit_inventory(tmp_path):
    for role in ('clock','reset'):
        D,M,C=vehicle(tmp_path,role)
        r=G.declared_infra_arcs(D,M,C)
        assert r['pins']==['a','z'] and not r['errors']
        assert r['arcs'][0]['role']==role and r['arcs'][0]['owner']=='die' and r['arcs'][0]['width']==1
        assert r['arcs'][0]['equivalence']=='y=x for both binary inputs'
        assert G.pin_reg_metrics(D,re.compile('^strap_'),frozenset(r['pins']))['pins_unregistered']==0
        assert G.pin_reg_metrics(D,re.compile('^strap_'))['pins_unregistered']==2


def test_missing_digest_role_owner_width_and_endpoint_mutants(tmp_path):
    D,M,C=vehicle(tmp_path)
    bad=[]
    bad.append(({},C));m=copy.deepcopy(M);m['ft_sha256']='stale';bad.append((m,C))
    m=copy.deepcopy(M);m['arcs'][0]['kind']='data';bad.append((m,C))
    m=copy.deepcopy(M);m['owner']='core';bad.append((m,C))
    m=copy.deepcopy(M);m['arcs'][0]['width']=2;bad.append((m,C))
    m=copy.deepcopy(M);m['arcs'][0]['sink']='nonexistent';bad.append((m,C))
    c=copy.deepcopy(C);c['ports'][0]['direction']='OUTPUT';bad.append((M,c))
    for m,c in bad:
        r=G.declared_infra_arcs(D,m,c)
        assert not r['pins'] and r['errors']


def test_logic_data_fanout_disconnection_cycle_and_polarity_rejected(tmp_path):
    for mut in ('logic','data','extra_port','disconnected','cycle','invert'):
        D,M,C=vehicle(tmp_path)
        if mut=='logic':D.cells[1]=('L',)+D.cells[1][1:]
        if mut=='data':D.nets[1][2].append(('i',2,False))
        if mut=='extra_port':D.nets[1][2].append(('p',99,False))
        if mut=='disconnected':D.nets[1][2].clear()
        if mut=='cycle':D.nets[1][2].clear();D.nets[1][2].append(('i',1,False));D.cell_in[1]=[(1,False)]
        if mut=='invert':D.cells[1]=('B','INVx1_ASAP7_75t_R')+D.cells[1][2:]
        r=G.declared_infra_arcs(D,M,C)
        assert not r['pins'] and r['arcs'][0]['status']=='FAIL',mut
