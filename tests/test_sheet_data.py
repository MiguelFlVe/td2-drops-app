"""2.2: data from the Division 2 Gear Spreadsheet — native cores, 13 weapon attributes, Named gear rolls, catalog v3 -> v4."""
import json, os
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__))+'/'
URL=os.environ.get('TD2_URL','http://127.0.0.1:8772/index.html')
SP=os.environ.get('TD2_OUT', HERE+'out/'); os.makedirs(SP, exist_ok=True)
errors=[]; dialogs=[]
def ok(c,m): print(('PASS ' if c else 'FAIL ')+m)
def pct(x): return float(x.replace('%','').replace(',',''))
CORES=['Weapon Damage','Armor','Skill Tier']
W13=['Accuracy','Critical Hit Chance','Critical Hit Damage','Damage to Armor','Damage to Health','Damage to Targets Out of Cover',
     'Headshot Damage','Magazine Size','Optimal Range','Rate of Fire','Reload Speed','Stability','Swap Speed']

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
    pick=lambda v, scope=L: pg.locator(scope+' select').first.select_option(v)
    stored=lambda: json.loads(pg.evaluate("localStorage.getItem('td2-drop-tracker-v1')"))

    # --- Native cores in Log drop ---
    btn('Brand Set').click(); btn('Chest').click(); pick('Habsburg Guard'); btn('High End').click()
    st4=step(3)
    ok(st4.locator('.fixed').inner_text().startswith('Armor') and 'native core of this brand' in st4.inner_text().lower(), 'Habsburg Guard chest: core fixed to Armor')
    ok(btn('Weapon Damage').count()==0 and missing()=='Missing: 2 attributes, talent', 'no core chips; core not asked for: %r'%missing())
    btn('Health').click(); btn('Headshot Damage').click(); st4.locator('select').select_option('Mad Bomber')
    st4.scroll_into_view_if_needed(); pg.screenshot(path=SP+'s22-01-native-core.png')
    pg.locator('#logbar button').click()
    pick('Murakami Industries'); btn('High End').click()
    ok(step(3).locator('.fixed').inner_text().startswith('Skill Tier'), 'Murakami: Skill Tier')
    btn('Gear Set').click(); btn('Holster').click(); pick('System Corruption')
    ok(step(3).locator('.fixed').inner_text().startswith('Weapon Damage') and 'native core of this gear set' in step(3).inner_text().lower(), 'System Corruption holster: Weapon Damage')
    btn('Chest').click(); pick('System Corruption')
    ok(step(3).locator('.fixed').inner_text().startswith('Armor'), 'System Corruption chest: Armor (split by slot)')
    btn('Gloves').click(); pick('Core Strength')
    ok(pg.locator(L).get_by_role('button', name='Skill Tier', exact=True).count()==1 and 'random on this item' in step(3).inner_text(), 'Core Strength gloves: random core, picked by hand')
    btn('Mask').click(); pick('Refactor')
    ok(pg.locator(L).get_by_role('button', name='Armor', exact=True).count()==1, 'Refactor: no core in the catalog, so it stays random')
    btn('Kneepads').click(); pick("Hunter's Fury")
    btn('Critical Hit Damage').click(); pg.locator('#logbar button').click()
    d=stored()['drops']
    ok(d[0]['core']=='Armor' and d[0]['attrs']==['Health','Headshot Damage'] and d[0]['talent']=='Mad Bomber', 'native core stored with the drop')
    ok(d[1]['set']=="Hunter's Fury" and d[1]['core']=='Weapon Damage', "Hunter's Fury kneepads stored with Weapon Damage")

    # --- Named gear exceptions ---
    btn('Brand Set').click(); btn('Kneepads').click(); pick('Česká Výroba s.r.o.'); btn('Named').click()
    st4=step(3)
    txt=st4.inner_text()
    ok(st4.locator('.chip').count()==0 and 'Critical Hit Damage' in txt and 'Critical Hit Chance' in txt and 'Bewildered' in txt, 'Turmoil: attributes already rolled, nothing to pick')
    ok(missing()=='Ready to save', 'Turmoil: ready to save right away')
    st4.scroll_into_view_if_needed(); pg.screenshot(path=SP+'s22-02-turmoil.png')
    pg.locator('#logbar button').click()
    t=stored()['drops'][-1]
    ok(t['named']=='Turmoil' and t['core']=='Weapon Damage' and t['attrs']==[] and t['talent'] is None, 'Turmoil stored: native core, no random attributes: %s'%t)
    btn('Mask').click(); pick('Douglas & Harding'); btn('Named').click()
    chips=step(3).locator('.chip').all_inner_texts()
    ok(len(chips)==11 and 'Headshot Damage' not in chips, 'Punch Drunk: free attribute can’t be Headshot Damage (%d)'%len(chips))
    btn('Gloves').click(); pick('Zwiadowka Sp. z o.o.'); btn('Named').click()
    ok('Weapon Handling' not in step(3).locator('.chip').all_inner_texts(), "Eagle's Grasp: free attribute can’t be Weapon Handling")
    pick('Sokolov Concern'); btn('Named').click()
    ok('Status Effects' not in step(3).locator('.chip').all_inner_texts(), 'Firm Handshake: free attribute can’t be Status Effects')

    # --- Weapons: 13 attributes, talents by type, new Named ---
    btn('Weapon').click(); btn('Pistol').click(); btn('High End').click()
    ok(step(3).locator('.chip').all_inner_texts()==W13, 'pistol: the 13 weapon attributes')
    btn('Light Machine Gun').click(); btn('High End').click()
    lmg=step(3).locator('select option').all_inner_texts()
    ok('Stabilize' in lmg and 'Damage to Targets Out of Cover' not in step(3).locator('.chip').all_inner_texts(), 'LMG: Stabilize can roll; core 2 excluded')
    btn('Submachine Gun').click(); btn('Named').click()
    ok(step(2).locator('select option', has_text='The Sleigher').count()==1, 'The Sleigher (SMG) in the catalog')

    # --- History & CSV for Turmoil ---
    pg.locator('nav.tabs button[data-go="hist"]').click()
    tg=pg.locator('.drop').first.locator('.tags').inner_text()
    ok('Critical Hit Damage' in tg and 'Critical Hit Chance' in tg and 'Bewildered' in tg and 'Weapon Damage' in tg, 'history: Turmoil shows its fixed attributes: %r'%tg)
    with pg.expect_download() as dl:
        pg.get_by_role('button', name='Export CSV').click()
    csv=open(dl.value.path(), encoding='utf-8-sig').read().splitlines()
    ok(any('Named,Turmoil,Weapon Damage,Critical Hit Damage,Critical Hit Chance,,Bewildered' in l for l in csv), 'CSV: Turmoil with its fixed attributes')

    # --- Odds: Turmoil rolls the same every time ---
    pg.locator('nav.tabs button[data-go="odds"]').click()
    O='#odds-form'
    btn('Brand Set', O).click(); btn('Kneepads', O).click(); pick('Česká Výroba s.r.o.', O); btn('Named', O).click()
    r=pg.locator('#odds-results').inner_text()
    ok(pg.locator('#odds-results .big').inner_text()=='100%' and 'Every Turmoil rolls the same' in r and 'Your drops of this item\n1' in r, 'odds: Turmoil 100%%: %r'%r[:120])
    ctx.close()

    # --- A 2.1.x file: catalog v3 upgraded, off-core drops flagged ---
    ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    ctx.add_init_script(open(HERE+'mock_bridge.js').read())
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('dialog', on_d)
    pg.goto(URL)
    v3={'v':3,'brands':['5.11 Tactical','Airaldi Holdings','Petrov Defense Group','Habsburg Guard','My New Brand'],
        'gearSets':['Core Strength',"Hunter's Fury"],'gearAttrs':['Critical Hit Chance','Health','Skill Damage'],
        'weaponAttrs':['Critical Hit Chance','Critical Hit Damage','Headshot Damage','Damage to Armor','Damage to Health','Damage to Targets Out of Cover'],
        'chestTalents':['Glass Cannon'],'backpackTalents':['Energize','Empathic Resolve'],
        'weaponTalents':[{'n':'Stabilize','w':['Assault Rifle','Submachine Gun']},{'n':'My Talent','w':['Pistol']}],
        'namedGear':[{'n':'My Named','set':'Airaldi Holdings','slot':'Mask','perk':'Test perk'}],
        'namedWeapons':[{'n':'Lexington','type':'Assault Rifle','perk':'+1,782 Base Damage','base':'Police M4'}]}
    old={'app':'td2-drop-tracker','v':3,'backupTs':0,'settings':{'useBase':True},'catalog':v3,'drops':[
        {'id':'a1','ts':1,'cat':'brand','set':'Airaldi Holdings','slot':'Backpack','rarity':'High End','named':None,'core':'Weapon Damage','attrs':['Critical Hit Chance','Health'],'talent':'Energize'},
        {'id':'a2','ts':2,'cat':'brand','set':'Airaldi Holdings','slot':'Backpack','rarity':'High End','named':None,'core':'Skill Tier','attrs':['Skill Damage','Health'],'talent':'Energize'},
        {'id':'p1','ts':3,'cat':'brand','set':'Petrov Defense Group','slot':'Holster','rarity':'High End','named':None,'core':'Skill Tier','attrs':['Critical Hit Chance','Health'],'talent':None},
        {'id':'n1','ts':4,'cat':'brand','set':'My New Brand','slot':'Mask','rarity':'High End','named':None,'core':'Armor','attrs':['Health','Skill Damage'],'talent':None}]}
    pg.evaluate("t => { localStorage.setItem('mock:file:td2-drops.json', t); window.__mockNextName='td2-drops.json'; }", json.dumps(old))
    pg.get_by_role('button', name='Open existing file').click(); pg.wait_for_timeout(100)
    ok(pg.locator('#count').inner_text()=='4 drops', '2.1.x file opens: 4 drops')
    pg.locator('nav.tabs button[data-go="hist"]').click()
    hist=pg.locator('#hist').inner_text()
    ok(pg.locator('.tag.warn-tag').count()==2 and '2 drops logged with a core their items can’t drop with' in hist, 'history flags the 2 off-core drops')
    warn=pg.locator('.drop', has=pg.locator('.tag.warn-tag')).locator('.drop-title').all_inner_texts()
    ok(sorted(warn)==['Airaldi Holdings Backpack','Petrov Defense Group Holster'] and 'Core should be Weapon Damage' in pg.locator('.tag.warn-tag').first.inner_text(), 'flagged: %s'%warn)
    pg.screenshot(path=SP+'s22-03-hist-offcore.png', full_page=True)
    # catalog upgraded in memory and written back on the next save
    pg.locator('nav.tabs button[data-go="log"]').click()
    btn('Weapon').click(); btn('Pistol').click(); btn('High End').click()
    ok(len(step(3).locator('.chip').all_inner_texts())==13, 'upgraded catalog: 13 weapon attributes')
    btn('Headshot Damage').click(); step(3).locator('select').select_option('My Talent'); pg.locator('#logbar button').click()
    f=json.loads(pg.evaluate("localStorage.getItem('mock:file:td2-drops.json')"))
    c=f['catalog']
    ok(c['v']==4 and c['brandCores'].get('Airaldi Holdings')=='Weapon Damage' and 'My New Brand' not in c['brandCores'], 'catalog v4: native cores added, own brand left random')
    ok('My New Brand' in c['brands'] and 'Uzina Getica' in c['brands'] and 'Empathic Resolve' in c['backpackTalents'] and len(c['backpackTalents'])==23, 'your additions kept, new defaults added')
    stab=[t for t in c['weaponTalents'] if t['n']=='Stabilize'][0]['w']
    ok(sorted(stab)==['Assault Rifle','Light Machine Gun','Submachine Gun'] and any(t['n']=='My Talent' for t in c['weaponTalents']), 'Stabilize gets LMG; own talent kept')
    ok(any(x['n']=='My Named' for x in c['namedGear']) and len(c['namedGear'])==70 and any(x['n']=='The Sleigher' for x in c['namedWeapons']), 'own Named kept, default Named added')
    ok(c['setCores'].get("Hunter's Fury")=='Weapon Damage' and 'Core Strength' not in c['setCores'] and c['setCores']['System Corruption']['Chest']=='Armor', 'Gear Set cores (Core Strength random, System Corruption split)')
    ok([x['id'] for x in f['drops']][:4]==['a1','a2','p1','n1'] and f['drops'][1]['core']=='Skill Tier', 'drops unchanged (off-core drops kept for you to review)')
    # random core for an own brand without core
    btn('Brand Set').click(); btn('Mask').click(); pick('My New Brand')
    ok(step(3).count()==1, 'own brand selectable')
    btn('High End').click()
    ok(pg.locator(L).get_by_role('button', name='Armor', exact=True).count()==1, 'own brand without a core: core picked by hand')
    # Odds for Airaldi backpack: the off-core drop isn't counted as yours
    pg.locator('nav.tabs button[data-go="odds"]').click()
    O='#odds-form'
    btn('Brand Set', O).click(); btn('Backpack', O).click(); pick('Airaldi Holdings', O); btn('High End', O).click()
    step(3, O).locator('select').select_option('Energize')
    r=pg.locator('#odds-results').inner_text()
    ok('Drops of this item\n1' in r and 'With this roll\n1' in r and '1 other drop of this item was logged with a core other than Weapon Damage' in r, 'odds: off-core drop left out of your counts, with a note')
    ctx.close()

    # --- Catalog editing: cores ---
    ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('dialog', on_d)
    pg.goto(URL)
    pg.locator('nav.tabs button[data-go="cat"]').click()
    tas=pg.locator('#catalog textarea')
    br=tas.nth(0).input_value()
    ok('Airaldi Holdings | Weapon Damage' in br and 'Uzina Getica | Armor' in br and 'Murakami Industries | Skill Tier' in br, 'catalog shows brand cores')
    gs=tas.nth(1).input_value()
    ok('System Corruption | Mask, Gloves, Holster: Weapon Damage; Backpack, Chest, Kneepads: Armor' in gs and '\nCore Strength\n' in gs and '\nRefactor\n' in gs, 'catalog shows set cores (split and random)')
    pg.screenshot(path=SP+'s22-04-catalog.png', full_page=False)
    tas.nth(0).fill(br.replace('Airaldi Holdings | Weapon Damage', 'Airaldi Holdings'))
    tas.nth(1).fill(gs.replace('\nRefactor\n', '\nRefactor | Mask, Chest, Holster: Armor; backpack, gloves, kneepads: Skill Tier\n').replace('Aegis | Armor', 'Aegis | Purple'))
    n=len(dialogs)
    pg.locator('#catsave').click()
    ok(any('set line' in m and 'Aegis | Purple' in m for m in dialogs[n:]), 'bad set line reported')
    c=json.loads(pg.evaluate("localStorage.getItem('td2-drop-tracker-v1')"))['catalog']
    ok('Airaldi Holdings' not in c['brandCores'] and c['setCores']['Refactor']=={'Mask':'Armor','Chest':'Armor','Holster':'Armor','Backpack':'Skill Tier','Gloves':'Skill Tier','Kneepads':'Skill Tier'} and 'Aegis' not in c['gearSets'], 'cores saved from the catalog text')
    pg.locator('nav.tabs button[data-go="log"]').click()
    btn('Gear Set').click(); btn('Gloves').click(); pick('Refactor')
    ok(step(3).locator('.fixed').inner_text().startswith('Skill Tier'), 'edited split set: Refactor gloves Skill Tier')
    btn('Brand Set').click(); btn('Mask').click(); pick('Airaldi Holdings'); btn('High End').click()
    ok(pg.locator(L).get_by_role('button', name='Armor', exact=True).count()==1, 'core removed in the catalog: picked by hand again')
    ctx.close()
    b.close()
print('ERRORS', errors)
print('DIALOGS', dialogs)
