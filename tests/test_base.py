import json
from playwright.sync_api import sync_playwright
import os
HERE=os.path.dirname(os.path.abspath(__file__))+'/'
URL=os.environ.get('TD2_URL','http://127.0.0.1:8771/index.html')
SP=os.environ.get('TD2_OUT', HERE+'out/'); os.makedirs(SP, exist_ok=True)
errors=[]
def ok(c,m): print(('PASS ' if c else 'FAIL ')+m)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':390,'height':844}); pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(URL)
    ok(pg.locator('#count').inner_text()=='0 drops', 'own drops 0')
    pg.locator('nav.tabs button[data-go="odds"]').click()
    F='#odds-form'; btn=lambda n: pg.locator(F).get_by_role('button', name=n, exact=True).first
    btn('Brand Set').click(); btn('Gloves').click(); pg.locator(F+' select').first.select_option('Česká Výroba s.r.o.'); btn('High End').click()
    ok('Red Horizon season · 3 drops bundled with the app' in pg.locator('.basetoggle').inner_text(), 'base toggle in step 4 (old-format drop migrated too)')
    btn('Critical Hit Chance').click()
    txt=pg.locator('#odds-results').inner_text()
    ok('Based on 3 drops of this item' in txt and 'Includes 3 drops from the base data (Red Horizon season) along with your 0' in txt, 'base data used for estimate')
    ok('Drops of this item\n0' in txt, 'own counts exclude base')
    with_base=pg.locator('#odds-results .big').inner_text()
    pg.locator('.basetoggle input').uncheck()
    without=pg.locator('#odds-results .big').inner_text()
    ok(with_base!=without and 'Includes' not in pg.locator('#odds-results').inner_text(), 'toggle off changes estimate: %s -> %s'%(with_base, without))
    pg.locator('nav.tabs button[data-go="hist"]').click()
    ok('The app includes 3 base drops (Red Horizon season)' in pg.locator('#hist').inner_text() and 'currently aren’t' in pg.locator('#hist').inner_text(), 'history explains base data')
    b.close()
print('ERRORS', errors)
