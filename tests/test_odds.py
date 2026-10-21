import json
from playwright.sync_api import sync_playwright
import os
HERE=os.path.dirname(os.path.abspath(__file__))+'/'
URL=os.environ.get('TD2_URL','http://127.0.0.1:8772/index.html')
SP=os.environ.get('TD2_OUT', HERE+'out/'); os.makedirs(SP, exist_ok=True)
errors=[]
def ok(c,m): print(('PASS ' if c else 'FAIL ')+m)
def pct(x): return float(x.replace('%','').replace(',',''))
CORES=['Weapon Damage','Armor','Skill Tier']
GA=['Critical Hit Chance','Critical Hit Damage','Headshot Damage','Weapon Handling','Armor Regeneration','Hazard Protection','Health','Explosive Resistance','Skill Damage','Skill Haste','Repair Skills','Status Effects']
GLOVES='Česká Výroba s.r.o.'   # native core: Weapon Damage
CS='Core Strength'              # pieces other than the backpack: random core
def dr(i,cat,st,slot,rar,core,attrs,tal=None,named=None): return dict(id='t%d'%i,ts=i,cat=cat,set=st,slot=slot,rarity=rar,named=named,core=core,attrs=attrs,talent=tal)
D=[dr(1,'brand',GLOVES,'Gloves','High End','Weapon Damage',['Critical Hit Chance','Critical Hit Damage']),
   dr(2,'brand',GLOVES,'Gloves','High End','Weapon Damage',['Critical Hit Chance','Headshot Damage']),
   dr(3,'brand',GLOVES,'Gloves','High End','Armor',['Health','Armor Regeneration']),          # logged with the wrong core
   dr(4,'brand',GLOVES,'Chest','High End','Weapon Damage',['Critical Hit Chance','Weapon Handling'],'Glass Cannon'),
   dr(5,'brand','Gila Guard','Gloves','High End','Armor',['Health','Hazard Protection']),
   dr(6,'gear',"Striker's Battlegear",'Mask','Gear Set','Weapon Damage',['Critical Hit Damage']),
   dr(7,'gear',CS,'Gloves','Gear Set','Weapon Damage',['Critical Hit Chance']),
   dr(8,'gear',CS,'Gloves','Gear Set','Weapon Damage',['Headshot Damage']),
   dr(9,'gear',CS,'Gloves','Gear Set','Armor',['Critical Hit Chance']),
   dr(10,'gear',CS,'Holster','Gear Set','Skill Tier',['Skill Haste'])]
# ---- independent calculation (same model, written separately) ----
NATIVE={GLOVES:'Weapon Damage','Gila Guard':'Armor',"Striker's Battlegear":'Weapon Damage'}
def random_core(d): return d['cat']!='weapon' and d['set'] not in NATIVE
def hier(v,pool,levels):
    K=len(pool); p=1/K
    for c in reversed(levels):
        n=sum(c.get(x,0) for x in pool); p=(c.get(v,0)+K*p)/(n+K)
    return p
def cnt(ds,f):
    m={}
    for d in ds:
        v=f(d)
        for x in (v if isinstance(v,list) else [v]):
            if x: m[x]=m.get(x,0)+1
    return m
key=lambda d:(d['cat'],d['set'] or '',d['slot'],d['rarity'],d['named'] or '')
def rings(ds,preds,f):
    return [cnt([d for d in ds if P(d) and not (i and preds[i-1](d))],f) for i,P in enumerate(preds)]
def core_lv(sel):
    R=random_core
    return rings(D,[lambda d:R(d) and key(d)==key(sel), lambda d:R(d) and d['cat']==sel['cat'] and d['set']==sel['set'],
                    lambda d:R(d) and d['cat']==sel['cat'], R],lambda d:d['core'])
def attr_lv(sel,core): return rings(D,[lambda d:d['core']==core and key(d)==key(sel), lambda d:d['core']==core and d['cat']==sel['cat'],
                                       lambda d:d['core']==core and d['cat']!='weapon', lambda d:d['cat']!='weapon'],lambda d:d['attrs'])
def two_slots_one(dist,a):
    s=dist[a]
    for b,pb in dist.items():
        if b!=a: s+=pb*dist[a]/(1-pb)
    return s
# Česká gloves: core fixed (Weapon Damage) -> P = P(attribute | Weapon Damage)
sel_g=dict(cat='brand',set=GLOVES,slot='Gloves',rarity='High End',named=None)
dist=lambda sel,core:{x:hier(x,GA,attr_lv(sel,core)) for x in GA}
e_g=two_slots_one(dist(sel_g,'Weapon Damage'),'Critical Hit Chance')
# Core Strength gloves: random core -> sum over cores of P(core) · P(attribute | core), 1 attribute slot
sel_c=dict(cat='gear',set=CS,slot='Gloves',rarity='Gear Set',named=None)
e_c={c:hier(c,CORES,core_lv(sel_c))*dist(sel_c,c)['Critical Hit Chance'] for c in CORES}
print('expected Česká %.5f%%; Core Strength %s'%(e_g*100,{k:round(v*100,5) for k,v in e_c.items()}))
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(URL)
    pg.evaluate("t => localStorage.setItem('td2-drop-tracker-v1', t)", json.dumps({'v':3,'drops':D,'catalog':None,'backupTs':0}))
    pg.reload()
    pg.locator('nav.tabs button[data-go="odds"]').click()
    F='#odds-form'; btn=lambda n: pg.locator(F).get_by_role('button', name=n, exact=True).first
    res=lambda: pg.locator('#odds-results').inner_text()
    ok('Pick an item in steps' in res(), 'asks for an item first')
    # ---- brand item: native core ----
    btn('Brand Set').click(); btn('Gloves').click(); pg.locator(F+' select').first.select_option(GLOVES); btn('High End').click()
    ok('Choose the attributes or talent you want' in res(), 'native core: asks only for attributes or talent')
    st4=pg.locator(F+' .step').nth(3)
    ok(st4.locator('.fixed').inner_text().startswith('Weapon Damage') and btn('Armor').count()==0, 'odds step 4: core shown fixed (Weapon Damage)')
    btn('Critical Hit Chance').click()
    big=pct(pg.locator('#odds-results .big').inner_text())
    ok(abs(big-e_g*100)/(e_g*100)<0.01, 'native core: matches independent calc: %.4f vs %.4f'%(big,e_g*100))
    ok(pg.locator('.corerow').count()==0 and 'By core attribute' not in res(), 'no per-core card for a native-core item')
    txt=res()
    ok('Drops of this item\n2' in txt and 'With this roll\n2' in txt, 'your drops of this item: 2 (the off-core one left out), with roll: 2')
    ok('1 other drop of this item was logged with a core other than Weapon Damage' in txt, 'note about the off-core drop')
    tbl=pg.locator('#odds-results table').inner_text(); print(tbl)
    ok('Core' not in tbl.split('Total')[0].replace('Your data','') and '2 / 2' in tbl, 'breakdown: no core row, attribute 2 / 2')
    th=pct(pg.locator('#odds-results .kv').first.locator('.v').inner_text())
    ok(abs(th-100*2/12)<0.05, 'theoretical = 2/12 (core is certain) = %.4f'%th)
    pg.screenshot(path=SP+'v2-03-odds-native.png', full_page=True)
    # ---- random core: Core Strength gloves ----
    btn('Gear Set').click(); btn('Gloves').click(); pg.locator(F+' select').first.select_option(CS)
    ok(pg.locator(F).get_by_role('button', name='Armor', exact=True).count()==1, 'Core Strength gloves: core can be picked (random)')
    btn('Critical Hit Chance').click()
    tot=sum(e_c.values())
    big=pct(pg.locator('#odds-results .big').inner_text())
    ok(abs(big-tot*100)/(tot*100)<0.01, 'random core, any core: total matches independent calc: %.4f vs %.4f'%(big,tot*100))
    rows=pg.evaluate("[...document.querySelectorAll('.corerow .cr-p')].map(x=>x.firstChild.textContent)")
    ok(len(rows)==3 and all(abs(pct(r)-e_c[c]*100)/(e_c[c]*100)<0.01 for r,c in zip(rows,CORES)), 'per-core rows match: %s'%rows)
    pg.screenshot(path=SP+'v2-04-odds-random.png', full_page=True)
    pg.locator('.corerow').first.click()
    big=pct(pg.locator('#odds-results .big').inner_text())
    ok(abs(big-e_c['Weapon Damage']*100)/(e_c['Weapon Damage']*100)<0.01, 'core Weapon Damage selected: %.4f'%big)
    tbl=pg.locator('#odds-results table').inner_text()
    ok('Core\nWeapon Damage' in tbl and '2 / 3' in tbl and '1 / 2' in tbl, 'breakdown shows item-level counts')
    # weapons: named weapon locks talent; odds only on attribute
    btn('Weapon').click(); btn('Shotgun').click(); btn('Named').click()
    pg.locator(F+' .step').nth(2).locator('select').select_option('Lefty')
    ok(pg.locator(F+' .step').nth(3).locator('select').count()==0, 'named weapon: no talent choice in odds')
    btn('Critical Hit Chance').click()
    big=pct(pg.locator('#odds-results .big').inner_text())
    ok(abs(big-100/12)<0.01, 'shotgun attribute (12 options, no data): 8.33%% -> %.2f'%big)
    ctx.close(); b.close()
print('ERRORS', errors)
