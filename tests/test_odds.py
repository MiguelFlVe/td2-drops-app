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
GLOVES='Česká Výroba s.r.o.'
def dr(i,cat,st,slot,rar,core,attrs,tal=None,named=None): return dict(id='t%d'%i,ts=i,cat=cat,set=st,slot=slot,rarity=rar,named=named,core=core,attrs=attrs,talent=tal)
D=[dr(1,'brand',GLOVES,'Gloves','High End','Weapon Damage',['Critical Hit Chance','Critical Hit Damage']),
   dr(2,'brand',GLOVES,'Gloves','High End','Weapon Damage',['Critical Hit Chance','Headshot Damage']),
   dr(3,'brand',GLOVES,'Gloves','High End','Armor',['Health','Armor Regeneration']),
   dr(4,'brand',GLOVES,'Chest','High End','Weapon Damage',['Critical Hit Chance','Weapon Handling'],'Glass Cannon'),
   dr(5,'brand','Gila Guard','Gloves','High End','Armor',['Health','Hazard Protection']),
   dr(6,'gear',"Striker's Battlegear",'Mask','Gear Set','Weapon Damage',['Critical Hit Damage'])]
# ---- independent calculation (same model, written separately) ----
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
sel=dict(cat='brand',set=GLOVES,slot='Gloves',rarity='High End',named=None)
g=[d for d in D if d['cat']!='weapon']
def rings(ds,preds,f):
    out=[]
    for i,P in enumerate(preds):
        out.append(cnt([d for d in ds if P(d) and not (i and preds[i-1](d))],f))
    return out
def core_lv(): return rings(D,[lambda d:key(d)==key(sel), lambda d:d['cat']=='brand' and d['set']==GLOVES, lambda d:d['cat']=='brand', lambda d:d['cat']!='weapon'],lambda d:d['core'])
def attr_lv(core): return rings(D,[lambda d:d['core']==core and key(d)==key(sel), lambda d:d['core']==core and d['cat']=='brand', lambda d:d['core']==core and d['cat']!='weapon', lambda d:d['cat']!='weapon'],lambda d:d['attrs'])
def two_slots_one(dist,a):
    s=dist[a]
    for b,pb in dist.items():
        if b!=a: s+=pb*dist[a]/(1-pb)
    return s
def expected(core,a):
    pc=hier(core,CORES,core_lv()); dist={x:hier(x,GA,attr_lv(core)) for x in GA}
    return pc*two_slots_one(dist,a)
e_wd=expected('Weapon Damage','Critical Hit Chance'); e_ar=expected('Armor','Critical Hit Chance'); e_st=expected('Skill Tier','Critical Hit Chance')
print('expected WD %.5f%% AR %.5f%% ST %.5f%% total %.5f%%'%(e_wd*100,e_ar*100,e_st*100,(e_wd+e_ar+e_st)*100))
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(URL)
    pg.evaluate("t => localStorage.setItem('td2-drop-tracker-v1', t)", json.dumps({'v':3,'drops':D,'catalog':None,'backupTs':0}))
    pg.reload()
    pg.locator('nav.tabs button[data-go="odds"]').click()
    F='#odds-form'; btn=lambda n: pg.locator(F).get_by_role('button', name=n, exact=True).first
    ok('Pick an item in steps' in pg.locator('#odds-results').inner_text(), 'asks for an item first')
    btn('Brand Set').click(); btn('Gloves').click(); pg.locator(F+' select').first.select_option(GLOVES); btn('High End').click()
    ok('Choose the core attribute' in pg.locator('#odds-results').inner_text(), 'asks for a wanted roll')
    btn('Critical Hit Chance').click()
    big=pct(pg.locator('#odds-results .big').inner_text())
    ok(abs(big-(e_wd+e_ar+e_st)*100)/((e_wd+e_ar+e_st)*100)<0.01, 'any core total matches independent calc: %.4f'%big)
    rows=pg.evaluate("[...document.querySelectorAll('.corerow .cr-p')].map(x=>x.firstChild.textContent)")
    ok(all(abs(pct(r)-e*100)/(e*100)<0.01 for r,e in zip(rows,[e_wd,e_ar,e_st])), 'per-core rows match: %s'%rows)
    txt=pg.locator('#odds-results').inner_text()
    ok('Drops of this item\n3' in txt and 'With this roll\n2' in txt, 'your drops of this item: 3, with roll: 2')
    pg.screenshot(path=SP+'v2-03-odds-any.png', full_page=True)
    pg.locator('.corerow').first.click()
    big=pct(pg.locator('#odds-results .big').inner_text())
    ok(abs(big-e_wd*100)/(e_wd*100)<0.01, 'core Weapon Damage selected: %.4f'%big)
    tbl=pg.locator('#odds-results table').inner_text(); print(tbl)
    ok('Core\nWeapon Damage' in tbl and '2 / 3' in tbl and '2 / 2' in tbl, 'breakdown shows item-level counts')
    st=[x for x in pg.evaluate("[...document.querySelectorAll('.corerow small')].map(x=>x.textContent)")]; print(st)
    pg.screenshot(path=SP+'v2-04-odds-core.png', full_page=True)
    # theoretical check: core 1/3, one of two attrs from 12 -> 1/3 * (1/12 + 11*(1/12)*(1/12)/(11/12)) = 1/3*2/12
    th=pct(pg.locator('#odds-results .kv').first.locator('.v').inner_text())
    ok(abs(th-100/3*2/12)<0.01, 'theoretical = 1/3 x 2/12 = %.4f'%th)
    # impossible roll: gear set 1 slot with 2 attrs not possible -> choose gear set mask with 2 attrs
    btn('Gear Set').click(); btn('Mask').click(); pg.locator(F+' select').first.select_option("Striker's Battlegear")
    btn('Critical Hit Damage').click()
    ok(pg.locator('#odds-results .big').count()==1, 'gear set odds render')
    # weapons: named weapon locks talent; odds only on attribute
    btn('Weapon').click(); btn('Shotgun').click(); btn('Named').click()
    pg.locator(F+' .step').nth(2).locator('select').select_option('Lefty')
    ok(pg.locator(F+' .step').nth(3).locator('select').count()==0, 'named weapon: no talent choice in odds')
    btn('Critical Hit Chance').click()
    big=pct(pg.locator('#odds-results .big').inner_text())
    ok(abs(big-20)<0.01, 'shotgun attribute (5 options, no data): 20%% -> %.2f'%big)
    ctx.close(); b.close()
print('ERRORS', errors)
