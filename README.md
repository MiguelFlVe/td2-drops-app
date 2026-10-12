# Drops TD2 (Android)

App Android sin conexión para registrar drops de The Division 2 y calcular probabilidades.
Los datos se guardan en un archivo `.json` que eliges en tu teléfono (por ejemplo en Documentos).

- Sin permiso de Internet.
- La interfaz es `app/src/main/assets/index.html` (la misma página funciona también en un navegador).
- `MainActivity.java` muestra la página en un WebView y lee/escribe el archivo `.json` con el selector de archivos de Android.
- Además guarda una copia interna, por si el archivo se mueve o se borra.

## Compilar con GitHub Actions

Cada `push` a `main` ejecuta `.github/workflows/build.yml` y publica `drops-td2.apk` como artefacto.
Cada compilación también publica el APK en **Releases** (descárgalo desde el teléfono en
`https://github.com/MiguelFlVe/td2-drops-app/releases/latest`).

La clave de firma va cifrada en `app/release.jks.enc`. Para activar una firma estable (actualizaciones
que se instalan encima sin desinstalar), crea el secreto de Actions `SIGNING_PASSWORD`.
Sin ese secreto, el APK se firma con una clave de depuración distinta en cada compilación.

## Compilar en Android Studio

1. Abre esta carpeta con **File → Open**.
2. Espera a que termine la sincronización de Gradle.
3. **Build → Build App Bundle(s) / APK(s) → Build APK(s)**.
4. El APK queda en `app/build/outputs/apk/`.

## Instalar en el teléfono

1. Copia el APK al teléfono y ábrelo.
2. Si Android lo pide, permite "Instalar apps desconocidas" para la app desde la que lo abres (Archivos, Chrome…).
3. Al abrir Drops TD2 por primera vez, elige **Crear archivo nuevo** o **Abrir archivo existente**.

## Datos base

`app/src/main/assets/base-data.js` trae drops incluidos en la app (por ejemplo, los de una temporada completa).

- No aparecen en Historial, pero cuentan en las probabilidades mientras **Incluir datos base** esté activo (en Probabilidad).
- Los drops que el usuario ya tiene en su archivo (mismo `id`) no se cuentan dos veces.
- "Veces que ya lo conseguiste" y "Conseguido" cuentan solo los drops propios.

Para actualizarlos, exporta desde la app (**Historial → Guardar copia**) y ejecuta:

```
python3 tools/actualizar_datos_base.py respaldo.json --label "Temporada Red Horizon"
```

El script quita las notas y las fechas de cada drop, porque este repositorio es público.

## Aviso

Herramienta de fans, gratuita y sin ánimo de lucro. No está afiliada a Ubisoft ni a Massive Entertainment.
The Division es una marca registrada de Ubisoft.
