"""Core Strength backpack: all three core attributes, no minor attributes, set talent (exception added in 2.1.1)."""
import json, os
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__))+'/'
URL=os.environ.get('TD2_URL','http://127.0.0.1:8772/index.html')
SP=os.environ.get('TD2_OUT', HERE+'out/'); os.makedirs(SP, exist_ok=True)
errors=[]; dialogs=[]
def ok(c,m): print(('PASS ' if c else 'FAIL ')+m)
CORES=['Weapon Damage','Armor','Skill Tier']
# A file logged before 2.1.1: the app forced one core and one attribute on the Core Strength backpack
old={"app":"td2-drop-tracker","v":3,"backupTs":0,"settings":{"useBase":True},"drops":[
  {"id":"cs1","ts":1760000000000,"cat":"gear","set":"Core Strength","slot":"Backpack","rarity":"Gear Set","named":None,"core":"Armor","attrs":["Health"],"talent":None,"note":"Countdown"},
  {"id":"cs2","ts":1760000001000,"cat":"gear","set":"Core Strength","slot":"Backpack","rarity":"Gear Set","named":None,"core":"Armor","attrs":["Health"],"talent":None},
  {"id":"es","ts":1760000002000,"cat":"Equipo","clase":"Gear","set":"Core Strength","sub":"Mochila","core":"Blindaje","minors":["Salud"],"talent":None}]}
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    def on_d(d): dialogs.append(d.message); d.accept()
    pg.on('dialog', on_d)
    pg.goto(URL)
    L='#log'
    btn=lambda name, scope=L: pg.locator(scope).get_by_role('button', name=name, exact=True).first
    steps=lambda scope=L: pg.evaluate(f"[...document.querySelectorAll('{scope} .step')].map(s=>s.className.replace('step ',''))")

    # --- Log: Core Strength backpack ---
    btn('Gear Set').click(); btn('Backpack').click(); pg.locator(L+' select').first.select_option('Core Strength')
    st4=pg.locator(L+' .step').nth(3)
    ok(steps()==['done','done','done','done'], 'Core Strength backpack: nothing to pick in step 4 %s'%steps())
    ok(st4.locator('.chip').count()==0, 'no core or attribute chips')
    rows=st4.locator('.fixed .fixed-row').all_inner_texts()
    ok(len(rows)==3 and all(c in r for c,r in zip(CORES,rows)), 'shows the three cores as fixed: %s'%rows)
    ok('No minor attributes' in st4.inner_text() and 'Gear Set talent (comes with the set)' in st4.inner_text(), 'no minor attributes, set talent locked')
    ok(pg.locator('#logbar .missing').inner_text()=='Ready to save', 'ready to save right after step 3')
    pg.screenshot(path=SP+'cs-01-log.png', full_page=True)
    pg.locator('#logbar button').click()
    # --- Other pieces stay normal ---
    btn('Chest').click(); pg.locator(L+' select').first.select_option('Core Strength')
    st4=pg.locator(L+' .step').nth(3)
    ok(st4.locator('.chip').count()==3+12 and pg.locator('#logbar .missing').inner_text()=='Missing: core attribute, attribute', 'Core Strength chest: core + 1 attribute as usual')
    btn('Armor').click(); btn('Health').click(); pg.locator('#logbar button').click()
    btn('Backpack').click(); pg.locator(L+' select').first.select_option('Hard Wired')
    ok(pg.locator(L+' .step').nth(3).locator('.chip').count()==15, 'another Gear Set backpack: core + 1 attribute as usual')
    d=json.loads(pg.evaluate("localStorage.getItem('td2-drop-tracker-v1')"))['drops']
    ok(len(d)==2 and d[0]['set']=='Core Strength' and d[0]['slot']=='Backpack' and d[0]['core'] is None and d[0]['attrs']==[] and d[0]['talent'] is None, 'stored with no core, attributes or talent: %s'%d[0])
    ok(d[1]['core']=='Armor' and d[1]['attrs']==['Health'], 'Core Strength chest stored normally')

    # --- History ---
    pg.locator('nav.tabs button[data-go="hist"]').click()
    tags=pg.locator('.drop .tags').all_inner_texts()
    t_bp=tags[1]
    ok(all(c in t_bp for c in CORES) and 'Gear Set talent' in t_bp and 'Health' not in t_bp, 'history: backpack shows the three cores and the set talent: %r'%t_bp)
    summ=pg.locator('.card').first.locator('.tags').inner_text()
    ok('Weapon Damage: 1' in summ and 'Armor: 2' in summ and 'Skill Tier: 1' in summ, 'summary counts the backpack under each core: %r'%summ)
    with pg.expect_download() as dl:
        pg.get_by_role('button', name='Export CSV').click()
    csv=open(dl.value.path(), encoding='utf-8-sig').read().splitlines()
    ok(any('Core Strength,Backpack,Gear Set,,Weapon Damage + Armor + Skill Tier,,,,Gear Set talent' in l for l in csv), 'CSV core column lists all three cores')
    pg.screenshot(path=SP+'cs-02-hist.png', full_page=True)

    # --- Odds ---
    pg.locator('nav.tabs button[data-go="odds"]').click()
    O='#odds-form'
    btn('Gear Set', O).click(); btn('Backpack', O).click(); pg.locator(O+' select').first.select_option('Core Strength')
    res=pg.locator('#odds-results').inner_text()
    ok(pg.locator('#odds-results .big').inner_text()=='100%' and 'Every Core Strength Backpack rolls the same' in res, 'odds: 100%, always the same roll')
    ok('Your drops of this item\n1' in res, 'odds: counts your drops of it: %r'%res[-60:])
    ok(pg.locator(O+' .step').nth(3).locator('.chip').count()==0, 'odds step 4: nothing to pick')
    pg.screenshot(path=SP+'cs-03-odds.png', full_page=True)
    ctx.close()

    # --- Old files: placeholders removed, and they don't skew the other pieces ---
    ctx=b.new_context(viewport={'width':390,'height':844})
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(URL)
    pg.evaluate("t => localStorage.setItem('td2-drop-tracker-v1', t)", json.dumps(old)); pg.reload()
    ok(pg.locator('#count').inner_text()=='3 drops', 'old file loads: 3 drops')
    pg.locator('nav.tabs button[data-go="log"]').click()
    btn('Weapon').click(); btn('Pistol').click(); btn('High End').click(); btn('Headshot Damage').click()
    pg.locator(L+' .step').nth(3).locator('select').select_option('Salvage'); pg.locator('#logbar button').click()
    d=json.loads(pg.evaluate("localStorage.getItem('td2-drop-tracker-v1')"))['drops']
    cs=[x for x in d if x['set']=='Core Strength']
    ok(len(cs)==3 and all(x['core'] is None and x['attrs']==[] and x['talent'] is None for x in cs), 'old Core Strength backpacks (v3 and Spanish v1) migrated: no core, no attributes')
    ok(cs[0].get('note')=='Countdown' and cs[2]['slot']=='Backpack', 'notes and slot kept')
    pg.locator('nav.tabs button[data-go="odds"]').click()
    O='#odds-form'
    btn('Gear Set', O).click(); btn('Chest', O).click(); pg.locator(O+' select').first.select_option('Core Strength')
    btn('Armor', O).click()
    big=pg.locator('#odds-results .big').inner_text()
    ok(big=='33.3%', 'Core Strength chest: the old backpacks no longer count toward its core odds (%s)'%big)
    ctx.close()
    b.close()
print('ERRORS', errors)
print('DIALOGS', dialogs)
