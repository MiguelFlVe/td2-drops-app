# Drops TD2 (Android)

App Android sin conexión para registrar drops de The Division 2 y calcular probabilidades.
Los datos se guardan en un archivo `.json` que eliges en tu teléfono (por ejemplo en Documentos).

- Sin permiso de Internet.
- La interfaz es `app/src/main/assets/index.html` (la misma página funciona también en un navegador).
- `MainActivity.java` muestra la página en un WebView y lee/escribe el archivo `.json` con el selector de archivos de Android.
- Además guarda una copia interna, por si el archivo se mueve o se borra.

## Compilar con GitHub Actions

Cada `push` a `main` ejecuta `.github/workflows/build.yml` y publica `drops-td2.apk` como artefacto.
La firma usa los secretos `KEYSTORE_B64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS` y `KEY_PASSWORD`
(sin ellos se firma con la clave de depuración).

## Compilar en Android Studio

1. Abre esta carpeta con **File → Open**.
2. Espera a que termine la sincronización de Gradle.
3. **Build → Build App Bundle(s) / APK(s) → Build APK(s)**.
4. El APK queda en `app/build/outputs/apk/`.

## Instalar en el teléfono

1. Copia el APK al teléfono y ábrelo.
2. Si Android lo pide, permite "Instalar apps desconocidas" para la app desde la que lo abres (Archivos, Chrome…).
3. Al abrir Drops TD2 por primera vez, elige **Crear archivo nuevo** o **Abrir archivo existente**.
