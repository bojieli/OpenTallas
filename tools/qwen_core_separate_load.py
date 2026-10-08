#!/usr/bin/env python3
"""Opt-in structural separation of issue and NEXT load in emitted Qwen core.

Apply after all existing core emitters. A completed issue empties NEXT; LOAD
runs on the following edge. This removes ready/chase/issue logic from wide
NEXT and descriptor capture enables. Adds at most one edge per non-END issue.
No pipeline register, arithmetic change, external handshake or reset exception.
"""

def apply(text):
    marker='    parameter integer DEC_LA = 0'
    assert text.count(marker)==1
    text=text.replace(marker,'    parameter integer DEC_LA_SEPARATE_LOAD = 0,\n'+marker,1)
    candidates=[
      '    wire load = (st == S_RUN) && (fq_n != 0) && (!nx_v || issue_ld);',
      '    wire load = (st == S_RUN) && (fq_n != 0) && (!nx_v || issue);']
    found=[x for x in candidates if x in text]
    assert len(found)==1, 'expected exactly one emitted LOAD equation'
    old=found[0]
    issue='issue_ld' if 'issue_ld' in old else 'issue'
    new=f'''    // Separate LOAD removes the issue/ready cone from all NEXT captures.
    wire load = (st == S_RUN) && (fq_n != 0) &&
                (!nx_v || ((DEC_LA_SEPARATE_LOAD == 0) && {issue}));'''
    return text.replace(old,new,1)
