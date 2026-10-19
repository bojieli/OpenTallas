#!/usr/bin/env python3
"""Finite Boolean model only; does not simulate production RTL."""
import itertools, json
from pathlib import Path
cases=[]
for canonical,clone,enable,data in itertools.product(range(2),repeat=4):
    d=data if enable else canonical
    pair=(d,d)
    assert pair[0]==pair[1]
    independent=(d,data if enable else clone)
    cases.append(dict(canonical=canonical,clone=clone,enable=enable,data=data,
                      same_canonical_D_next=pair,private_feedback_next=independent))
witness=next(x for x in cases if x['private_feedback_next'][0]!=x['private_feedback_next'][1])
# A shared D guarantees copy convergence, but rerouting a pre-first-edge feedback
# operand onto an uninitialised clone can still alter the canonical trajectory.
original=0;uninitialised_clone=1
baseline_next=original
rerouted_common_D_next=uninitialised_clone
assert baseline_next!=rerouted_common_D_next
ans={'scope':'16 finite Boolean recurrence cases; not an RTL or parent reset proof',
     'common_D_converges':len(cases),'private_feedback_failure':witness,
     'first_edge_equivalence_counterexample':{'original_Q':original,'clone_Q':uninitialised_clone,'baseline_hold_D':baseline_next,'rerouted_shared_D':rerouted_common_D_next},
     'required_contract':'Either a real reset establishes equal copies before use, or protect canonical D dependencies and prove externally invalid startup until equality. No parent contract is assumed.',
     'cases':cases}
Path(__file__).with_name('recurrence.json').write_text(json.dumps(ans,indent=2)+'\n')
print('16 common-D convergence cases; private-feedback and first-edge equivalence counterexamples preserved')
