#!/usr/bin/env python3
"""Import the Chip Explorer's curated element stories (site/chip_explorer DATA.stories, built by
tools/chip_explorer_stories.py) into stories/curated.json for the /explorer page.

Each card keeps its full content (facts with records, tried variants, naive/trick diagrams) and gains `attach`: the
element / block names it belongs to (its closure blocks plus the identifiers named in its `element` line).  More stories
go in stories/*.json as {"cards": [...]} with the same card shape (a missing field renders as absent); a card with
"status": "planned" is a hook a story stream fills in later.

  python3 stories_import.py [--site /home/ubuntu/OpenTallas/site/chip_explorer/index.html]
"""
import argparse, json, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
# cards whose element line names a mechanism, not a block: the die masters / elements they are about
ATTACH = {'ds-frame': ['dsfd_bf', 'dsfd_q'], 'ds-dspark': [], 'hbm-credit': ['hfd_coll', 'hfd_coll_pkt_fifo_ii1', 'hfd_coll_pkt_fifo_ii3'],
          'hbm-smsu': ['hfd_sm', 'hfd_su_full'], 'qwen-kvmap': ['qfd_ctrl_shift'], 'qwen-allreduce': ['qfd_sp_tree_top'],
          'x-reach': ['hfd_rly', 'hfd_stn', 'dsfd_stnh_512x1'], 'x-h1': [], 'x-hc1': []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='/home/ubuntu/OpenTallas/site/chip_explorer/index.html')
    a = ap.parse_args()
    t = pathlib.Path(a.site).read_text()
    m = re.search(r'(?:const|var|let) DATA\s*=\s*', t)
    d, _ = json.JSONDecoder().raw_decode(t[m.end():])
    st = d['stories']
    cards = []
    for c in st['cards']:
        att = []
        for b in c.get('blocks') or []:
            if b.get('block') and b['block'] not in att: att.append(b['block'])
        for tok in re.findall(r'[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_*]+', c.get('element', '')):
            tok = tok.rstrip('*_')
            if tok[0].islower() and tok not in att: att.append(tok)
        for tok in ATTACH.get(c['id'], []):
            if tok not in att: att.append(tok)
        cards.append(dict(c, attach=att))
    rec = dict(schema='opentallas.explorer.stories.v1', source=a.site, built=d['meta'].get('date', {}).get('v'),
               loop_taken=st.get('loop_taken'), loop_src=st.get('loop_src'), legend=st.get('legend'), inputs=st.get('inputs'),
               cards=cards)
    out = HERE / 'stories' / 'curated.json'
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + '\n')
    print(len(cards), 'cards ->', out)
    for c in cards: print(' ', c['id'], c['attach'])


if __name__ == '__main__':
    main()
