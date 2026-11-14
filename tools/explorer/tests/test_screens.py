"""One PNG per view and theme (light, dark) into the shots dir (EXPLORER_SHOTS, default tests/_shots)."""
import pytest
from playwright.sync_api import expect
from helpers import *

pytestmark = pytest.mark.slow
HASH = {'overview': '#/overview', 'plan': '#/plan/s81', 'layout': '#/layout/%s?inst=%s' % (SIGNED_TYPE, S_INST), 'element': '#/element/' + ROUTED_TYPE,
        'dataflow': '#/dataflow/s81', 'token': '#/token/s81', 'closure': '#/closure/s81'}


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('v', VIEWS)
def test_screenshot(page, v, theme):
    page.add_init_script("try { localStorage.setItem('otx.theme', JSON.stringify('%s')); } catch (e) {}" % theme)
    goto(page, HASH[v], engine=v in ('layout', 'element'))
    assert page.evaluate('document.documentElement.dataset.theme') == theme
    if v == 'plan': page.wait_for_timeout(800)
    if v == 'overview': page.wait_for_timeout(2500)
    if v in ('layout', 'element'): page.wait_for_timeout(2500)
    p = shot(page, '%s-%s' % (v, theme))
    assert p.stat().st_size > 5000
