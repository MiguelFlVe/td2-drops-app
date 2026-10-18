# Drops TD2 (Android)

Offline Android app for The Division 2 players: log the gear and weapons that drop for you and see the odds of
getting the roll you want once a specific item drops.

- **Log drop** in 4 steps that unlock in order: type → slot (and, for gear, the Brand or Gear Set) → rarity
  (High End / Named) → attributes & talent. Changing an earlier choice clears the ones after it.
  Named items lock their unique attribute or perfect talent; Gear Set chests and backpacks lock the set talent.
- **Odds**: pick an item (steps 1–3) and the roll you want (step 4). The app estimates the chance of that roll
  *once that item drops*, from your own drops, separately for each core attribute.
- Your data lives in a `.json` file you choose on your phone (for example in Documents). No internet permission.
- Catalog preloaded with every Brand Set, Gear Set, attribute, talent and Named item up to Red Horizon (Y8S3),
  editable inside the app.

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
| Core | this item → same set → same type (Brand / Gear Set) → all gear |
| Gear attributes | this item → same type → all gear (each with the same core) → all gear |
| Brand talent | this item → same slot (each with the same core) → same slot |
| Weapon attribute | this item → same weapon type → all weapons |
| Weapon talent | this item → all High End weapons |

Brand items roll 2 distinct attributes (drawn without repeats); Gear Set pieces, weapons and Named gear outside
the chest and backpack roll 1.

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

The signing key is stored encrypted in `app/release.jks.enc`. Add the Actions secret `SIGNING_PASSWORD` for a
stable signature (updates install over the previous version). Without it, each build uses a different debug key.

## Build in Android Studio

1. Open this folder with **File → Open**.
2. Wait for the Gradle sync to finish.
3. **Build → Build App Bundle(s) / APK(s) → Build APK(s)**.
4. The APK is in `app/build/outputs/apk/`.

## Install on your phone

1. Download the APK on your phone and open it.
2. If Android asks, allow "Install unknown apps" for the app you're opening it from (Files, Chrome…).
   If Play Protect warns about an unknown app, choose **Install anyway**.
3. The first time you open Drops TD2, choose **Create new file** or **Open existing file**.

## Disclaimer

Free, non-profit fan tool. Not affiliated with Ubisoft or Massive Entertainment.
The Division is a registered trademark of Ubisoft.
