# Drops TD2 (Android)

Offline Android app for The Division 2 players: log the gear and weapons that drop for you and see the odds of
getting the roll you want once a specific item drops.

- **Log drop** in 4 steps that unlock in order: type → slot (and, for gear, the Brand or Gear Set) → rarity
  (High End / Named) → attributes & talent. Changing an earlier choice clears the ones after it.
  Named items lock their unique attribute or perfect talent; Gear Set chests and backpacks lock the set talent.
- **Log from a video** (2.3): record a clip on the console while you go over one section of your inventory, and the
  app reads it on your phone. It finds the items that were new (they still had their “!”), reads their details panel
  and lists them for you to check, fix and save. See [Log from a video](#log-from-a-video).
- **Odds**: pick an item (steps 1–3) and the roll you want (step 4). The app estimates the chance of that roll
  *once that item drops*, from your own drops, separately for each core attribute.
- **Native cores**: brand items, Named gear and Gear Set pieces always drop with the core attribute of their brand
  or set, so Log drop fills it in and Odds doesn't treat it as chance. History flags drops logged with a core their
  item can't have.
- Your data lives in a `.json` file you choose on your phone (for example in Documents). No internet permission.
- Catalog preloaded with every Brand Set, Gear Set, attribute, talent and Named item up to Red Horizon (Y8S3),
  editable inside the app. Since 2.2 it follows the community
  [Division 2 Gear Spreadsheet](https://docs.google.com/spreadsheets/d/1nrPBmOrtpkEW1j5fbcRT7L-AXgsGOqMqxXoVtopsiGM/htmlview)
  (native cores, the 13 weapon attributes, which talents roll on each weapon type), plus Red Horizon items from
  newer sources.

## Log from a video

1. In the game, open one inventory section (Weapons, Mask, Backpack…) and sort it by **New**.
2. Record a clip on the console while you move over each item slowly. Stop on each one until its details panel shows
   everything: scroll the panel down to the talent.
3. In the app: **Log drop → Log from a video**, pick the section and the clip (the original 16:9 capture; a video of
   the TV taken with a phone won't work).
4. Check the list and tap **Save**. Each item can be unchecked or edited (with the usual steps) before saving.

How it works, all on the phone and without a connection:

- The cursor is the bright orange tile in the item grid. A new item has a small orange badge with a white “!”, which
  the game removes as soon as the item is selected; so an item was new if its tile had the badge just before the
  cursor reached it. Items that were already seen are left out.
- If the list scrolled and the tile wasn't on screen before, the app can't tell: the item is marked **New?** and
  pre-checked only if it came between new items (the list is sorted by New).
- The details panel is read with Google ML Kit's on-device text recognition (the model ships inside the APK, which is
  why the app is bigger since 2.3; nothing is uploaded and the app still has no internet permission). The text is
  matched against the Catalog: weapon type, Named item (by name, or by its perfect talent), brand or Gear Set, core,
  attributes and talent. Exotics are skipped.
- The game must be in English, like the Catalog.

## How the odds are estimated

Each part (core, attributes, talent) is estimated in layers, from the narrowest group of drops to the widest:

```
p(group) = (times seen in the group + K × p(wider group)) / (drops in the group + K)
```

`K` is the number of options, the widest group falls back to equal odds (1 / K), and each drop counts only once,
in the narrowest group it belongs to. With no data the result is the theoretical value; with many drops of the
exact item, it approaches what you actually got. Groups used:

| Part | Narrow → wide |
|---|---|
| Core (only items with a random core) | this item → same set → same type (Brand / Gear Set) → all random-core gear |
| Gear attributes | this item → same type → all gear (each with the same core) → all gear |
| Brand talent | this item → same slot (each with the same core) → same slot |
| Weapon attribute | this item → same weapon type → all weapons |
| Weapon talent | this item → all High End weapons |

Brand items roll 2 distinct attributes (drawn without repeats); Gear Set pieces, weapons and Named gear outside
the chest and backpack roll 1. Weapons roll 1 of 13 attributes, minus their type's core 2.

**Native cores:** every brand and Gear Set has a core attribute (Catalog → Sets, written `Name | Core`), and its
items always drop with it, so the core part is 100%. System Corruption splits it by slot
(`Name | Mask, Gloves, Holster: Weapon Damage; Backpack, Chest, Kneepads: Armor`). Sets with no core in the catalog
(Core Strength pieces other than the backpack, and Refactor, whose split isn't confirmed) roll a random core,
estimated only from other random-core drops. Drops logged with a core their item can't have are flagged in History
and left out of "Your drops"; they're never changed automatically.

**Named gear exceptions:** Turmoil comes with Critical Hit Damage and Critical Hit Chance already rolled (nothing to
pick); the free attribute of Punch Drunk, Eagle's Grasp and Firm Handshake can't be their unique one (Headshot Damage,
Weapon Handling, Status Effects).

**Exception:** the Core Strength backpack always has all three core attributes (Weapon Damage, Armor and Skill Tier)
and no minor attributes, so it has nothing to roll: Log drop saves it without a core or attributes, and Odds shows it
as a fixed roll. Its drops aren't used to estimate other items' cores or attributes.

**Exception:** First Sight (Named assault rifle) has no unique talent: its perk only changes the weapon's base stats
(+30% Headshot Damage, -50% Reload Speed). Nothing is locked, so it rolls an attribute and a talent like a High End
assault rifle, and its talents also count toward the High End weapon talent estimate. First Sight drops logged before
2.1.2 have no talent recorded: they still count for attributes, but not when you ask for a talent.

## Base data

`app/src/main/assets/base-data.js` can bundle drops with the app (for example, a whole season).

- They aren't listed in History, but they're used for the odds while **Include base data** is on (Odds, step 4).
- Drops a user already has in their own file (same `id`) aren't counted twice.
- "Your drops of this item" and "you: X of Y" only count the user's own drops.

To update it, export from the app (**History → Save a copy**) and run:

```
python3 tools/actualizar_datos_base.py backup.json --label "Red Horizon season"
```

The script removes each drop's note and date, because this repository is public.

## Build with GitHub Actions

Every push to `main` runs `.github/workflows/build.yml`, publishes `drops-td2.apk` as an artifact and as a
**Release** (download it on your phone from `https://github.com/MiguelFlVe/td2-drops-app/releases/latest`).

- The version name comes from the `VERSION` file (for example `2.2`). Bump it in every release commit: the build
  stops if a release with that version already exists. The version code is the run number, so it always goes up.
- The release notes start with `RELEASE_NOTES.md` (what's new in this version).
- Commits that don't change the app (docs, tests, data) add `[skip ci]` to the message.

The signing key is stored encrypted in `app/release.jks.enc`. Add the Actions secret `SIGNING_PASSWORD` for a
stable signature (updates install over the previous version). Without it, each build uses a different debug key.

## Build in Android Studio

1. Open this folder with **File → Open**.
2. Wait for the Gradle sync to finish.
3. **Build → Build App Bundle(s) / APK(s) → Build APK(s)**.
4. The APK is in `app/build/outputs/apk/`.

## Tests and checks

- `python3 tests/run_all.py` runs the browser tests (Playwright + Chromium) against `app/src/main/assets/index.html`:
  the 4-step flow, the odds (checked against an independent Python implementation), migration of old files, the
  native file bridge (mocked), catalog editing, base data, the Core Strength backpack and First Sight exceptions, and
  the spreadsheet data (native cores, Named gear rolls, catalog v3 → v4 upgrade), and the review screen of Log from a
  video, fed with the real OCR of a console clip and of gear screenshots (`tests/fixtures/video-*.json`).
- `VideoTracker.java` (cursor and “!” detection) is plain Java with no Android classes, so it can be run on a computer
  with frames of a clip (1920×1080 RGB) to check it.
- `python3 tools/apk_signature.py drops-td2.apk` and `python3 tools/apk_manifest.py drops-td2.apk` check a built
  APK's signature, certificate and version.

## Install on your phone

1. Download the APK on your phone and open it.
2. If Android asks, allow "Install unknown apps" for the app you're opening it from (Files, Chrome…).
   If Play Protect warns about an unknown app, choose **Install anyway**.
3. The first time you open Drops TD2, choose **Create new file** or **Open existing file**.

## Disclaimer

Free, non-profit fan tool. Not affiliated with Ubisoft or Massive Entertainment.
The Division is a registered trademark of Ubisoft.
