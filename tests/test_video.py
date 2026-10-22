"""Log from a video (2.3): the review screen built from what the Android side read in an inventory clip.
The fixtures are real: OCR of the details panel in a 57 s console clip of the Weapons section (7 new items, cursor
tracking done by VideoTracker.java) and of the gear screenshots Miguel sent. The native scanner is mocked."""
import json, os
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__))+'/'
URL=os.environ.get('TD2_URL','http://127.0.0.1:8772/index.html')
SP=os.environ.get('TD2_OUT', HERE+'out/'); os.makedirs(SP, exist_ok=True)
errors=[]; dialogs=[]
def ok(c,m): print(('PASS ' if c else 'FAIL ')+m)
WEAPONS=json.load(open(HERE+'fixtures/video-weapons.json'))
SHOTS=json.load(open(HERE+'fixtures/video-shots.json'))
VIDEO_MOCK = """
window.AndroidDB.pickVideo = function(){ window.__picks = (window.__picks || 0) + 1;
  setTimeout(() => { window.__videoProgress(0, 'Opening the video…'); window.__videoProgress(42, 'Reading the video… 24 of 57 s'); }, 10); };
window.AndroidDB.videoResult = function(){ return window.__videoResultText || ''; };
window.AndroidDB.cancelVideo = function(){ window.__videoResultText = JSON.stringify({ok:false, error:'cancelled'}); setTimeout(() => window.__videoDone(), 10); };
"""
def result(segments, **kw):
    r={'ok':True,'segments':segments,'duration':57.2,'elapsed':41.3,'frames':172,'ocr':66,'size':'1920x1080'}; r.update(kw); return r

with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    ctx.add_init_script(open(HERE+'mock_bridge.js').read())
    ctx.add_init_script(VIDEO_MOCK)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    def on_d(d): dialogs.append(d.message); d.accept()
    pg.on('dialog', on_d)
    pg.goto(URL)
    pg.get_by_role('button', name='Create new file').click(); pg.wait_for_timeout(100)
    L='#log'
    btn=lambda name, scope=L: pg.locator(scope).get_by_role('button', name=name, exact=True).first
    def finish(res):
        pg.evaluate("t => { window.__videoResultText = t; window.__videoDone(); }", json.dumps(res)); pg.wait_for_timeout(50)
    def scan(section, res):
        if pg.locator('.video-entry').count(): pg.locator('.video-entry').click()
        btn(section).click(); btn('Choose video').click(); pg.wait_for_timeout(60)
        finish(res)
    cards=lambda: [pg.locator('.vitem').nth(i).inner_text() for i in range(pg.locator('.vitem').count())]
    stored=lambda: json.loads(pg.evaluate("localStorage.getItem('mock:file:td2-drops.json')"))['drops']

    # ---------- entry and section picker ----------
    ok(pg.locator('.video-entry').count()==1 and 'Log from a video' in pg.locator('.video-entry').inner_text(), 'Log shows "Log from a video" (native app)')
    pg.locator('.video-entry').click()
    ok(pg.locator(L+' .step').count()==0 and 'which inventory section' in pg.locator(L).inner_text().lower(), 'video screen replaces the manual steps')
    ok(pg.locator(L+' .chip').all_inner_texts()==['Weapons','Mask','Backpack','Chest','Gloves','Holster','Kneepads'], 'sections: Weapons + 6 gear slots')
    ok(btn('Choose video').is_disabled(), 'needs a section before choosing the video')
    pg.screenshot(path=SP+'video-01-pick.png', full_page=True)
    btn('Weapons').click(); btn('Choose video').click(); pg.wait_for_timeout(60)
    ok(pg.locator('.progress').count()==1 and '24 of 57 s' in pg.locator('#vmsg').inner_text(), 'progress while the phone reads the video')
    pg.screenshot(path=SP+'video-02-progress.png', full_page=True)
    btn('Cancel').click(); pg.wait_for_timeout(60)
    ok(btn('Choose video').count()==1 and pg.locator('.verr').count()==0, 'cancel: back to the picker, no error shown')

    # ---------- weapons clip ----------
    btn('Choose video').click(); pg.wait_for_timeout(60)
    finish(WEAPONS)
    c=cards(); print(*c, sep='\n---\n')
    ok(len(c)==7, '7 new items found in the clip (%d)'%len(c))
    ok(all(not __import__('re').search(r' [a-z]{1,4}\n', x.split('\n')[1]+'\n') for x in c), 'names without trailing icon noise')
    head=pg.locator(L+' .card').first.inner_text()
    ok('7 items to review' in head and 'already seen' in head and 'Read 57 s of video in 41 s' in head, 'summary: %r'%head)
    exp=[('High End Submachine Gun','AUG A3 Para XS','Rate of Fire · Ranger'),
         ('High End Submachine Gun','Black Market T821','Damage to Targets Out of Cover · Back and Forth'),
         ('Cabaret','Named Submachine Gun','Magazine Size · Perfect Thunder Strike'),
         ('High End Submachine Gun','P','Headshot Damage · Sledgehammer'),
         ('High End Submachine Gun','Vector SBR .45 ACP','Headshot Damage · Steady Handed'),
         ('Like Glue','Named Shotgun','Accuracy · Perfect Brazen'),
         ('High End Rifle','SOCOM','Critical Hit Chance · Preservation')]
    for i,(t,sub,summ) in enumerate(exp):
        ok(t in c[i] and sub.lower() in c[i].lower() and summ in c[i] and 'New' in c[i], 'item %d: %s / %s'%(i+1,t,summ))
    ok(pg.locator('.vitem input[type=checkbox]:checked').count()==7, 'all new items checked')
    ok(btn('Save 7 drops').is_enabled() and pg.locator('#vbar .missing').inner_text()=='Ready to save', 'ready to save 7 drops')
    pg.screenshot(path=SP+'video-03-review.png', full_page=True)

    # edit one: change the AUG's talent
    pg.locator('.vitem').nth(0).get_by_role('button', name='Edit').click()
    ed=pg.locator('.vitem').nth(0)
    ok(ed.locator('.step').count()==3 and ed.locator('select').count()==1, 'edit shows the usual steps and roll fields')
    ed.locator('select').select_option('Killer')
    ok('Rate of Fire · Killer' in pg.locator('.vitem').nth(0).inner_text(), 'edited talent shows in the summary')
    pg.screenshot(path=SP+'video-04-edit.png', full_page=True)
    pg.locator('.vitem').nth(0).get_by_role('button', name='Done').click()
    # uncheck the rifle
    pg.locator('.vitem').nth(6).locator('input[type=checkbox]').uncheck()
    ok(btn('Save 6 drops').count()==1, 'unchecking leaves 6 to save')
    before=len(stored())
    btn('Save 6 drops').click(); pg.wait_for_timeout(50)
    d=stored()[before:]
    ok(len(d)==6 and pg.locator('.video-entry').count()==1, 'saved 6 drops and went back to Log')
    ok(d[0]=={**d[0],'cat':'weapon','set':None,'slot':'Submachine Gun','rarity':'High End','named':None,'core':None,'attrs':['Rate of Fire'],'talent':'Killer'}, 'AUG stored with the edited talent: %s'%d[0])
    ok(d[1]['attrs']==['Damage to Targets Out of Cover'] and d[1]['talent']=='Back and Forth', 'T821 stored: %s'%d[1])
    ok(d[2]=={**d[2],'slot':'Submachine Gun','rarity':'Named','named':'Cabaret','attrs':['Magazine Size'],'talent':None}, 'Cabaret stored as Named, talent locked: %s'%d[2])
    ok(d[5]=={**d[5],'slot':'Shotgun','rarity':'Named','named':'Like Glue','attrs':['Accuracy'],'talent':None}, 'Like Glue stored: %s'%d[5])
    ok(all(x['id'] and x['ts'] for x in d) and len(set(x['id'] for x in d))==6, 'each drop has its own id')
    ok('6 drops saved' in pg.locator('#toast').inner_text(), 'toast with Undo')
    pg.locator('#toast button').click(); pg.wait_for_timeout(50)
    ok(len(stored())==before, 'Undo removes all 6')

    # ---------- gear screenshots ----------
    def shots(section):
        scan(section, result(SHOTS[section])); return cards()
    c=shots('Mask'); print(*c, sep='\n---\n')
    ok(len(c)==2 and 'China Light Industries Corporation Mask' in c[0] and 'Skill Tier · Skill Haste · Explosive Resistance' in c[0], 'mask: CLIC brand, native core, 2 attributes')
    ok('Unknown Mask' in c[1] and 'brand or Gear Set' in c[1] and 'Check: brand' in c[1] and pg.locator('.vitem.bad').count()==1, 'mask scrolled past its brand: flagged to complete')
    # fixing the brand fills in what was read (Repair Skills)
    pg.locator('.vitem').nth(1).get_by_role('button', name='Edit').click()
    pg.locator('.vitem').nth(1).locator('select').select_option('Alps Summit Armament')
    t=pg.locator('.vitem').nth(1).inner_text()
    ok('Alps Summit Armament Mask' in t and 'Repair Skills' in t and 'Check: 2 attributes' in t, 'brand picked: the attribute read from the video is filled in')
    pg.locator('.vitem').nth(1).get_by_role('button', name='Done').click()
    ok(btn('Save 2 drops').is_disabled() and '#2' in pg.locator('#vbar .missing').inner_text(), 'can’t save until it’s completed or unchecked')
    pg.screenshot(path=SP+'video-05-mask.png', full_page=True)
    pg.locator('.vitem').nth(1).locator('input[type=checkbox]').uncheck()
    ok(btn('Save 1 drop').is_enabled(), 'unchecked: 1 drop can be saved')
    btn('← Back').click()
    c=shots('Backpack'); print(*c, sep='\n---\n')
    ok('Habsburg Guard Backpack' in c[0] and 'Armor · Explosive Resistance · Critical Hit Damage · Opportunistic' in c[0], 'backpack: Habsburg, 2 attributes, talent')
    ok('The Courier' in c[1] and 'Hazard Protection · Explosive Resistance · Perfect Creeping Death' in c[1], 'Named backpack found from its perfect talent (The Courier)')
    btn('← Back').click()
    c=shots('Chest'); print(*c, sep='\n---\n')
    ok('Alps Summit Armament Chest' in c[0] and 'Critical Hit Damage · Armor Regeneration · Focus' in c[0], 'chest: "Armor Regen" read as Armor Regeneration, talent Focus')
    ok('Cherished' in c[1] and 'Critical Hit Damage · Hazard Protection · Perfect Trauma' in c[1], 'Named chest from Perfect Trauma (Cherished)')
    btn('← Back').click()
    c=shots('Gloves'); print(*c, sep='\n---\n')
    ok("Eagle's Grasp" in c[0] and 'Headshot Damage' in c[0] and 'Check' not in c[0], "Eagle's Grasp: free attribute read, unique one left out")
    btn('← Back').click()
    c=shots('Weapons'); print(*c, sep='\n---\n')
    ok("Ekim's Long Stick" in c[0] and 'Damage to Targets Out of Cover' in c[0], 'Perfect Ranger on a Marksman Rifle → Ekim’s Long Stick')
    ok('High End Marksman Rifle' in c[1] and 'Damage to Targets Out of Cover · Perpetuation' in c[1], 'High End MMR from its core attribute')
    pg.screenshot(path=SP+'video-06-weapon-shots.png', full_page=True)
    btn('← Back').click()

    # ---------- new / unsure / old ----------
    seg=lambda st, why='', k=0: {**SHOTS['Chest'][k], 'status':st, 'why':why}
    segs=[seg('unsure','start',1), seg('new'), seg('unsure','offscreen',1), seg('old'), seg('unsure','offscreen')]
    scan('Chest', result(segs))
    c=cards()
    checks=[pg.locator('.vitem').nth(i).locator('input').is_checked() for i in range(len(c))]
    ok(len(c)==4 and checks==[False, True, True, False], 'unsure items: checked only between a new and an old one %s'%checks)
    ok(pg.locator('.pill.warn').count()==3 and 'New?' in c[0], 'unsure items marked "New?"')
    head=pg.locator(L+' .card').first.inner_text()
    ok('4 items to review (3 unsure)' in head and '1 already seen item left out' in head, 'summary counts: %r'%head)
    pg.screenshot(path=SP+'video-07-unsure.png', full_page=True)
    n=len(dialogs)
    ok(pg.evaluate('window.__onBack()') and len(dialogs)==n+1 and pg.locator('.video-entry').count()==1, 'Android back: asks, then leaves the review')

    # ---------- errors ----------
    pg.locator('.video-entry').click(); btn('Weapons').click(); btn('Choose video').click(); pg.wait_for_timeout(60)
    finish({'ok':False,'error':'The video must be a 16:9 capture from the console (this one is 1080x1920).'})
    ok('16:9' in pg.locator('.verr').inner_text() and btn('Choose video').count()==1, 'reader errors are shown on the picker')
    finish(result([{**SHOTS['Chest'][0], 'status':'old'}]))
    ok('No new items were found' in pg.locator(L).inner_text() and btn('Save 0 drops').is_disabled(), 'no new items: explained, nothing to save')
    ok(pg.evaluate('window.__onBack()') and pg.locator('.video-entry').count()==1, 'back from an empty review')

    # ---------- browser (no native app): no video option ----------
    pg2=b.new_page(); pg2.on('pageerror', lambda e: errors.append(str(e)))
    pg2.goto(URL)
    ok(pg2.locator('.video-entry').count()==0 and pg2.locator('#log .step').count()==4, 'browser version: no video option, manual log unchanged')
    print('ERRORS', errors)
    b.close()
