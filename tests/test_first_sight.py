"""First Sight (Named AR): its perk only changes base stats, so it rolls an attribute and a talent (exception added in 2.1.2)."""
import json, os
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__))+'/'
URL=os.environ.get('TD2_URL','http://127.0.0.1:8772/index.html')
SP=os.environ.get('TD2_OUT', HERE+'out/'); os.makedirs(SP, exist_ok=True)
errors=[]; dialogs=[]
def ok(c,m): print(('PASS ' if c else 'FAIL ')+m)
def pct(x): return float(x.replace('%','').replace(',',''))
PERK='+30% Headshot Damage, -50% Reload Speed'
# A file logged before 2.1.2: First Sight had its talent locked, so it was stored without one
old={"app":"td2-drop-tracker","v":3,"backupTs":0,"settings":{"useBase":True},"drops":[
  {"id":"fs-old","ts":1760000000000,"cat":"weapon","set":None,"slot":"Assault Rifle","rarity":"Named","named":"First Sight","core":None,"attrs":["Critical Hit Chance"],"talent":None,"note":"Summit"}]}
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    def on_d(d): dialogs.append(d.message); d.accept()
    pg.on('dialog', on_d)
    pg.goto(URL)
    L='#log'
    btn=lambda name, scope=L: pg.locator(scope).get_by_role('button', name=name, exact=True).first
    step=lambda n, scope=L: pg.locator(scope+' .step').nth(n)
    missing=lambda: pg.locator('#logbar .missing').inner_text()

    # --- Log: First Sight ---
    btn('Weapon').click(); btn('Assault Rifle').click(); btn('Named').click()
    step(2).locator('select').select_option('First Sight')
    st4=step(3)
    ok(PERK in st4.locator('.perk').inner_text() and 'base stats' in st4.inner_text().lower(), 'First Sight: base-stat perk shown as fixed')
    ok(st4.locator('.chip').count()==5 and st4.locator('.chip', has_text='Damage to Health').count()==0, 'First Sight: 5 attribute chips (core 2 excluded)')
    tal=st4.locator('select')
    n_ar=pg.evaluate("[...document.querySelectorAll('#log .step')[3].querySelectorAll('select option')].length")-1
    ok(tal.count()==1 and n_ar>20 and tal.locator('option', has_text='Near Sighted').count()==1 and tal.locator('option', has_text='Salvage').count()==0,
       'First Sight: talent picker with the AR talents (%d)'%n_ar)
    ok(missing()=='Missing: attribute, talent', 'needs attribute and talent: %r'%missing())
    btn('Headshot Damage').click()
    ok(missing()=='Missing: talent', 'attribute picked, still needs the talent')
    step(3).locator('select').select_option('Near Sighted')
    ok(missing()=='Ready to save', 'ready to save with attribute + talent')
    pg.screenshot(path=SP+'fs-01-log.png', full_page=True)
    st4.locator('.perk').scroll_into_view_if_needed(); pg.screenshot(path=SP+'fs-01b-step4.png')
    pg.locator('#logbar button').click()
    d=json.loads(pg.evaluate("localStorage.getItem('td2-drop-tracker-v1')"))['drops']
    ok(d[0]=={**d[0], 'cat':'weapon','slot':'Assault Rifle','rarity':'Named','named':'First Sight','core':None,'attrs':['Headshot Damage'],'talent':'Near Sighted'},
       'stored with attribute and talent: %s'%d[0])

    # --- Other Named ARs stay locked ---
    step(2).locator('select').select_option('Burn Out')
    st4=step(3)
    ok(st4.locator('select').count()==0 and 'Perfect On Empty' in st4.locator('.perk').inner_text() and missing()=='Missing: attribute', 'Burn Out: talent still locked')
    btn('Critical Hit Damage').click(); pg.locator('#logbar button').click()

    # --- History & CSV ---
    pg.locator('nav.tabs button[data-go="hist"]').click()
    tags=pg.locator('.drop .tags').all_inner_texts()
    fs=tags[1]
    ok('Headshot Damage' in fs and 'Near Sighted' in fs and PERK in fs, 'history: First Sight shows attribute, talent and perk: %r'%fs)
    with pg.expect_download() as dl:
        pg.get_by_role('button', name='Export CSV').click()
    csv=open(dl.value.path(), encoding='utf-8-sig').read().splitlines()
    ok(any(',Assault Rifle,Named,First Sight,,Headshot Damage,,Near Sighted,"'+PERK+'"' in l for l in csv), 'CSV has its talent and perk')
    pg.screenshot(path=SP+'fs-02-hist.png', full_page=True)

    # --- Odds ---
    pg.locator('nav.tabs button[data-go="odds"]').click()
    O='#odds-form'
    btn('Weapon', O).click(); btn('Assault Rifle', O).click(); btn('Named', O).click()
    step(2, O).locator('select').select_option('First Sight')
    ok(step(3, O).locator('select').count()==1 and PERK in step(3, O).locator('.perk').inner_text(), 'odds step 4: talent can be picked, perk fixed')
    step(3, O).locator('select').select_option('Near Sighted')
    K=n_ar
    big=pct(pg.locator('#odds-results .big').inner_text())
    exp=2/(K+1)*100   # this item: 1 of 1 Near Sighted, no other random-talent weapons -> (1 + K·1/K) / (1 + K)
    ok(abs(big-exp)<0.06, 'First Sight Near Sighted: %.2f%% (expected %.2f%%)'%(big,exp))
    res=pg.locator('#odds-results').inner_text()
    ok('Drops of this item\n1' in res and 'With this roll\n1' in res, 'odds: your First Sight drops counted')
    theo=pg.locator('#odds-results .kv', has_text='Theoretical').locator('.v').inner_text()
    ok(abs(pct(theo)-100/K)<0.06, 'theory: 1 in %d talents (%s)'%(K,theo))
    btn('Headshot Damage', O).click()
    big2=pct(pg.locator('#odds-results .big').inner_text())
    ok(0<big2<big, 'attribute + talent combined (%.2f%% < %.2f%%)'%(big2,big))
    ok('First Sight only changes the weapon’s base stats' in pg.locator('#odds-results details').text_content(), 'method explains the exception')
    pg.screenshot(path=SP+'fs-03-odds.png', full_page=True)
    # High End AR: First Sight's talent counts toward the High End weapon talent estimate
    btn('High End', O).click(); step(3, O).locator('select').select_option('Near Sighted')
    big3=pct(pg.locator('#odds-results .big').inner_text())
    ok(abs(big3-exp)<0.06, 'High End AR Near Sighted uses First Sight’s talent: %.2f%% (expected %.2f%%)'%(big3,exp))
    ctx.close()

    # --- Old file: First Sight without a talent still loads and isn't counted as a miss ---
    ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(URL)
    pg.evaluate("t => localStorage.setItem('td2-drop-tracker-v1', t)", json.dumps(old)); pg.reload()
    ok(pg.locator('#count').inner_text()=='1 drop', 'old file loads: 1 drop')
    pg.locator('nav.tabs button[data-go="hist"]').click()
    t0=pg.locator('.drop .tags').first.inner_text()
    ok('Critical Hit Chance' in t0 and PERK in t0, 'old First Sight drop shown with its attribute and perk')
    pg.locator('nav.tabs button[data-go="odds"]').click()
    O='#odds-form'
    btn('Weapon', O).click(); btn('Assault Rifle', O).click(); btn('Named', O).click()
    step(2, O).locator('select').select_option('First Sight')
    btn('Critical Hit Chance', O).click()
    res=pg.locator('#odds-results').inner_text()
    ok('Drops of this item\n1' in res and 'With this roll\n1' in res and 'no talent recorded' not in res, 'attribute only: the old drop counts')
    step(3, O).locator('select').select_option('Near Sighted')
    res=pg.locator('#odds-results').inner_text()
    ok('Drops of this item\n0' in res and '1 other drop of this item has no talent recorded' in res, 'talent asked: the old drop is left out, with a note')
    rows=pg.locator('#odds-results table.bd tbody tr').all_inner_texts()
    ok(len(rows)==3 and '1 / 1' in rows[0] and '0 / 0' in rows[1] and 'Based on 1 drop of this item' in res,
       'breakdown: its attribute still counts (1 / 1), its talent doesn’t (0 / 0): %r'%rows)
    pg.screenshot(path=SP+'fs-04-old.png', full_page=True)
    pg.locator('nav.tabs button[data-go="log"]').click()
    btn('Weapon').click(); btn('Pistol').click(); btn('High End').click(); btn('Headshot Damage').click()
    step(3).locator('select').select_option('Salvage'); pg.locator('#logbar button').click()
    d=json.loads(pg.evaluate("localStorage.getItem('td2-drop-tracker-v1')"))['drops']
    fs=[x for x in d if x['named']=='First Sight']
    ok(len(fs)==1 and fs[0]['talent'] is None and fs[0]['attrs']==['Critical Hit Chance'] and fs[0].get('note')=='Summit', 'old drop kept unchanged when saving')
    ctx.close()
    b.close()
print('ERRORS', errors)
print('DIALOGS', dialogs)
