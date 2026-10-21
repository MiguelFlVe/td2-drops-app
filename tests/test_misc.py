import json
from playwright.sync_api import sync_playwright
import os
HERE=os.path.dirname(os.path.abspath(__file__))+'/'
URL=os.environ.get('TD2_URL','http://127.0.0.1:8772/index.html')
SP=os.environ.get('TD2_OUT', HERE+'out/'); os.makedirs(SP, exist_ok=True)
errors=[]; dialogs=[]
def ok(c,m): print(('PASS ' if c else 'FAIL ')+m)
# v1.7 (Spanish) file as the user has it now
old={"app":"td2-drop-tracker","v":2,"backupTs":0,"settings":{"useBase":True},
  "catalog":{"gearCores":["Daño de arma","Blindaje","Nivel de habilidad"],"gearMinors":["Salud"]},
  "drops":[
   {"id":"a","ts":1760000000000,"cat":"Equipo","clase":"Gear","sub":"Mochila","core":"Daño de arma","minors":["Probabilidad de crítico"],"talent":None},
   {"id":"b","ts":1760000001000,"cat":"Equipo","clase":"Brand","set":"Ceska Vyroba","sub":"Pechera","core":"Rojo","minors":["Probabilidad de crítico","Daño crítico"],"talent":"Obliterate","note":"Countdown"},
   {"id":"c","ts":1760000002000,"cat":"Equipo","clase":"Gear","sub":"Pechera","core":"Blindaje","minors":["Salud"],"talent":"Foundry Bulwark"},
   {"id":"d","ts":1760000003000,"cat":"Arma","sub":"Rifle de Asalto","core1":"Daño de rifle de asalto","core2":"Daño a la salud","minors":["Daño a objetivos fuera de cobertura"],"talent":"Optimist"}]}
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---------- native mode: open existing v1.7 file ----------
    ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    ctx.add_init_script(open(HERE+'mock_bridge.js').read())
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    def on_d(d): dialogs.append(d.message); d.accept()
    pg.on('dialog', on_d)
    pg.goto(URL)
    ok(pg.locator('#onboard').is_visible() and 'Choose where to save your drops' in pg.locator('#onboard').inner_text(), 'onboarding in English')
    pg.evaluate("t => { localStorage.setItem('mock:file:td2-drops.json', t); window.__mockNextName='td2-drops.json'; }", json.dumps(old))
    pg.get_by_role('button', name='Open existing file').click(); pg.wait_for_timeout(100)
    ok(pg.locator('#count').inner_text()=='4 drops', 'v1.7 file opened: 4 drops')
    pg.locator('nav.tabs button[data-go="hist"]').click()
    titles=pg.locator('.drop-title').all_inner_texts(); subs=pg.locator('.drop-sub').all_inner_texts()
    print(titles); print(subs)
    ok(titles==['High End Assault Rifle','Foundry Bulwark Chest','Česká Výroba s.r.o. Chest','Unknown Gear Set Backpack'], 'migrated titles (set recovered, brand renamed)')
    tags=pg.locator('.drop .tags').all_inner_texts(); print(tags)
    ok('Damage to Targets Out of Cover' in tags[0] and 'Optimist' in tags[0], 'weapon attrs/talent translated')
    ok('Weapon Damage' in tags[2] and 'Critical Hit Chance' in tags[2] and 'Obliterate' in tags[2], 'brand core/attrs translated (Rojo -> Weapon Damage)')
    ok('Armor' in tags[1] and 'Health' in tags[1] and 'Gear Set talent' in tags[1], 'gear set (talent field) migrated to set, talent locked')
    # save something -> file rewritten as v3 English
    pg.locator('nav.tabs button[data-go="log"]').click()
    L='#log'; btn=lambda n: pg.locator(L).get_by_role('button', name=n, exact=True).first
    btn('Weapon').click(); btn('Pistol').click(); btn('High End').click()
    st4=pg.locator(L+' .step').nth(3)
    ok('None on pistols' in st4.inner_text() and len(st4.locator('.chip').all_inner_texts())==13, 'pistol: no core 2, 13 attributes')
    btn('Headshot Damage').click(); st4.locator('select').select_option('Salvage'); pg.locator('#logbar button').click()
    f=json.loads(pg.evaluate("localStorage.getItem('mock:file:td2-drops.json')"))
    ok(f['v']==3 and f['catalog']['v']==4 and len(f['catalog']['namedGear'])==69, 'file rewritten as v3 with the English catalog (v4)')
    ok(all(d['cat'] in ('brand','gear','weapon') for d in f['drops']) and f['drops'][1]['set']=='Česká Výroba s.r.o.' and f['drops'][1]['note']=='Countdown', 'drops rewritten in new format, notes kept')
    # reload keeps everything
    pg.reload(); ok(pg.locator('#count').inner_text()=='5 drops', 'restart: data reloaded from file')
    # external change + missing file
    f['drops'].append(dict(f['drops'][-1], id='ext'))
    pg.evaluate("t => localStorage.setItem('mock:file:td2-drops.json', t)", json.dumps(f)); pg.evaluate('window.__onResume()')
    ok(pg.locator('#count').inner_text()=='6 drops', 'external change picked up')
    pg.evaluate("localStorage.removeItem('mock:file:td2-drops.json')"); pg.evaluate('window.__onResume()')
    ok('Couldn’t open td2-drops.json' in pg.locator('#banner').inner_text(), 'missing-file banner in English')
    pg.evaluate("t => localStorage.setItem('mock:file:td2-drops.json', t)", json.dumps(f))
    pg.evaluate("window.__mockNextName='td2-drops.json'")
    pg.locator('#banner').get_by_role('button', name='Open file').click(); pg.wait_for_timeout(100)
    ok(pg.locator('#banner').is_hidden(), 'reopened file, banner cleared')
    # back button
    pg.locator('nav.tabs button[data-go="hist"]').click()
    ok(pg.evaluate('window.__onBack()')==True and pg.evaluate('window.__onBack()')==False, 'back: History -> Log -> exit')
    # export copy name
    pg.locator('nav.tabs button[data-go="hist"]').click()
    pg.get_by_role('button', name='Save a copy').click(); pg.wait_for_timeout(50)
    ok(pg.evaluate('window.__mockLog.slice(-1)[0].name').startswith('td2-drops-backup-'), 'backup file name in English')
    ctx.close()
    # ---------- browser mode: v1.7 localStorage + catalog edit ----------
    ctx=b.new_context(viewport={'width':390,'height':844}); pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('dialog', on_d)
    pg.goto(URL); pg.evaluate("t => localStorage.setItem('td2-drop-tracker-v1', t)", json.dumps({'v':2,'drops':old['drops'],'catalog':old['catalog']})); pg.reload()
    ok(pg.locator('#count').inner_text()=='4 drops', 'browser: v1.7 data migrated')
    pg.locator('nav.tabs button[data-go="cat"]').click()
    tas=pg.locator('#catalog textarea')
    ng=tas.nth(6)
    ng.fill(ng.input_value()+'\nTest Mask|Airaldi Holdings|Mask|Test Perk\nBroken line|Airaldi Holdings|Helmet|x')
    pg.locator('#catsave').click()
    ok(any('couldn’t be read' in m for m in dialogs), 'bad Named line reported')
    pg.locator('nav.tabs button[data-go="log"]').click()
    L='#log'; btn=lambda n: pg.locator(L).get_by_role('button', name=n, exact=True).first
    btn('Brand Set').click(); btn('Mask').click(); pg.locator(L+' select').first.select_option('Airaldi Holdings')
    ok(not pg.locator(L).get_by_role('button', name='Named', exact=True).is_disabled(), 'catalog addition enables Named for Airaldi mask')
    btn('Named').click(); ok(pg.locator(L).get_by_text('Test Perk').count()>=1, 'new Named item usable')
    ctx.close(); b.close()
print('ERRORS', errors)
