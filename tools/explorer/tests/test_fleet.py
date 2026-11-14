"""Fleet view: hosts (load, RAM, admission, jobs, disks) and the job table (die / item / stage / elapsed), on the
fleet-viz collectors proxied by /api/v1/fleet/*.  Uses the conftest browser."""
import json, os, time, urllib.request
import pytest

BASE = os.environ.get('EXPLORER_URL', 'http://127.0.0.1:8770')
HOSTS = ['EPYC2', 'EPYC7', 'EPYC8', 'EPYC9', 'EPYC10', 'INTEL1', 'INTEL2', 'localhost']


def jget(path):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=30).read())


def test_fleet_api_contract():
    f = jget('/api/v1/fleet/fleet')
    assert {'hosts', 'totals', 'loop', 'history', 'recent', 'fresh', 'generated_at'} <= set(f)
    labels = {h['label'] for h in f['hosts']}
    assert set(HOSTS) <= labels, labels
    up = [h for h in f['hosts'] if h['state'] == 'up']
    assert len(up) >= 5 and all({'load', 'mem_total', 'mem_used', 'cores', 'jobs'} <= set(h) for h in up)
    j = jget('/api/v1/fleet/fleetjobs')
    assert j['rows'] and all({'host', 'kind', 'start', 'die', 'item', 'stage', 'attempt'} <= set(r) for r in j['rows'][:200])
    assert sum(1 for r in j['rows'] if r['item']) > 0.2 * len(j['rows']), 'die / item parsed for a fair share of the jobs'
    assert {'jobs', 'status'} <= set(jget('/api/v1/fleet/jobs')) and 'verdicts' in jget('/api/v1/fleet/verdicts')
    try:
        urllib.request.urlopen(BASE + '/api/v1/fleet/nope', timeout=10); assert False, 'unknown fleet endpoint must be 404'
    except urllib.error.HTTPError as e:
        assert e.code == 404 and 'error' in json.loads(e.read())
    assert any(d['id'] == 'fleet' and d['state'] == 'fresh' for d in jget('/api/v1/meta')['datasets'])


def test_fleet_probe_has_admission_and_disks():
    p = jget('/api/v1/fleet/probe'); t0 = time.time()
    while len(p['hosts']) < 5 and time.time() - t0 < 60: time.sleep(3); p = jget('/api/v1/fleet/probe')
    ok = [h for h in p['hosts'].values() if h['admit'] and h['disks']]
    assert len(ok) >= 5, p
    assert all('admit_gb' in h['admit'] and any(d['mount'] == '/' for d in h['disks']) for h in ok)


def open_fleet(browser, hash_='/#/fleet'):
    pg = browser.new_page(viewport={'width': 1600, 'height': 1000}); pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.goto(BASE + hash_, wait_until='load')
    pg.wait_for_selector('[data-testid=fleet-hosts] [data-host]', timeout=30000)
    pg.wait_for_selector('[data-testid=fleet-jobs] tbody tr', timeout=40000)
    return pg


def test_fleet_view_hosts_and_totals(browser):
    pg = open_fleet(browser)
    assert pg.evaluate("window.otx.store.get().view") == 'fleet'
    cards = pg.eval_on_selector_all('[data-testid=fleet-hosts] [data-host]', 'els => els.map(e => e.dataset.host)')
    assert cards == HOSTS, cards                                         # the eight fleet hosts, fixed order
    txt = pg.inner_text('[data-testid=host-EPYC8]')
    for word in ('Load', 'RAM', 'Admit', 'Jobs', 'running', 'waiting'): assert word in txt, (word, txt)
    pg.wait_for_function("document.querySelector('[data-testid=host-EPYC8]').innerText.includes('GB free')", timeout=60000)   # admission + disks from the probe
    assert 'Root' in pg.inner_text('[data-testid=host-EPYC8]') and 'scratch' in pg.inner_text('[data-testid=host-EPYC8]')
    tot = pg.inner_text('[data-testid=fleet-totals]')
    assert 'hosts up' in tot and 'cores busy' in tot and 'jobs running' in tot and 'waiting for RAM' in tot
    assert 'live' in pg.inner_text('[data-testid=fleet-live]')
    assert pg.inner_text('[data-testid=asof]').startswith('data as of')
    assert 'Fleet' in pg.inner_text('[data-testid=view-fleet]')          # first-class entry of the main navigation
    assert not pg.errs, pg.errs
    pg.close()


def test_fleet_jobs_table_filter_sort_select(browser):
    pg = open_fleet(browser)
    head = pg.inner_text('[data-testid=fleet-jobs] thead')
    for col in ('Host', 'Die', 'Item', 'Stage', 'Elapsed'): assert col in head
    n_all = pg.inner_text('[data-testid=fleet-count]')
    pg.click('[data-testid=host-EPYC9]')                                  # host card filters the jobs, lands in the URL
    pg.wait_for_function("window.otx.store.get().params.host === 'EPYC9'")
    pg.wait_for_function("(a) => document.querySelector('[data-testid=fleet-count]').innerText !== a", arg=n_all)
    hosts = set(pg.eval_on_selector_all('[data-testid=fleet-jobs] tbody tr td:first-child', 'els => els.map(e => e.innerText)'))
    assert hosts == {'EPYC9'}, hosts
    assert 'ram admission' in pg.inner_text('[data-testid=insp-body]').lower()    # inspector Host tab
    pg.click('[data-testid=fleet-host-clear]')
    pg.wait_for_function("!window.otx.store.get().params.host")
    pg.fill('[data-testid=fleet-filter]', 's81')
    pg.wait_for_function("(a) => document.querySelector('[data-testid=fleet-count]').innerText !== a", arg=n_all)
    pg.fill('[data-testid=fleet-filter]', '')
    pg.click('[data-testid=fleet-kind-wait]'); pg.wait_for_function("window.otx.store.get().params.kind === 'wait'")
    kinds = set(pg.eval_on_selector_all('[data-testid=fleet-jobs] tbody tr td:nth-child(2)', 'els => els.map(e => e.innerText)'))
    assert kinds <= {'waiting'}, kinds
    pg.click('[data-testid=fleet-kind-all]')
    pg.click('[data-testid=fleet-sort-mem]')
    assert pg.get_attribute('[data-testid=fleet-sort-mem]', 'aria-sort') == 'descending'
    mem = pg.eval_on_selector_all('[data-testid=fleet-jobs] tbody tr td:nth-child(8)', 'els => els.slice(0, 6).map(e => parseFloat(e.innerText.replace(/,/g, "")))')
    mem = [m for m in mem if m == m]
    assert mem == sorted(mem, reverse=True), mem
    pg.click('[data-testid=fleet-jobs] tbody tr:first-child td:nth-child(7)')   # a row fills the inspector Job tab
    pg.wait_for_selector('[data-testid=fleet-job-card]')
    card = pg.inner_text('[data-testid=fleet-job-card]')
    for k in ('die', 'item', 'stage', 'started', 'RAM', 'directory'): assert k in card, (k, card)
    pg.click('[data-testid=fleet-refresh]')
    assert not pg.errs, pg.errs
    pg.close()


def test_fleet_old_paths_and_key(browser):
    pg = browser.new_page(viewport={'width': 1400, 'height': 900})
    pg.goto(BASE + '/fleet', wait_until='load')
    pg.wait_for_function("window.otx && window.otx.store.get().view === 'fleet'", timeout=20000)   # the old bookmark lands on the Fleet view
    pg.keyboard.press('1'); pg.wait_for_function("window.otx.store.get().view === 'overview'")
    pg.keyboard.press('8'); pg.wait_for_function("window.otx.store.get().view === 'fleet'")
    pg.close()
