package app.td2drops;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.Configuration;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.webkit.JavascriptInterface;
import android.webkit.JsResult;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/**
 * Drops TD2: la interfaz es la página web incluida en assets/index.html.
 * Los datos viven en un archivo .json que el usuario elige (Storage Access Framework).
 * Además se guarda una copia interna (cache.json) por si el archivo se mueve o se borra.
 */
public class MainActivity extends Activity {

    private static final int REQ_CREATE_DB = 1;
    private static final int REQ_OPEN_DB = 2;
    private static final int REQ_EXPORT = 3;
    private static final int REQ_IMPORT = 4;

    private static final String PREFS = "td2drops";
    private static final String KEY_URI = "dbUri";
    private static final String KEY_PREV_URI = "prevDbUri";
    private static final String CACHE = "cache.json";

    private WebView web;
    private SharedPreferences prefs;
    private volatile String pendingExport;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        web = new WebView(this);
        boolean night = (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK)
                == Configuration.UI_MODE_NIGHT_YES;
        web.setBackgroundColor(night ? Color.parseColor("#0E1013") : Color.parseColor("#F3F4F6"));

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return true; // la app no navega a ningún otro sitio
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onJsAlert(WebView view, String url, String message, JsResult result) {
                new AlertDialog.Builder(MainActivity.this)
                        .setMessage(message)
                        .setPositiveButton("Aceptar", (d, w) -> result.confirm())
                        .setOnCancelListener(d -> result.cancel())
                        .show();
                return true;
            }

            @Override
            public boolean onJsConfirm(WebView view, String url, String message, JsResult result) {
                new AlertDialog.Builder(MainActivity.this)
                        .setMessage(message)
                        .setPositiveButton("Aceptar", (d, w) -> result.confirm())
                        .setNegativeButton("Cancelar", (d, w) -> result.cancel())
                        .setOnCancelListener(d -> result.cancel())
                        .show();
                return true;
            }
        });

        web.addJavascriptInterface(new Bridge(), "AndroidDB");
        setContentView(web);
        web.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) js("window.__onResume && window.__onResume()");
    }

    @Override
    public void onBackPressed() {
        web.evaluateJavascript("(window.__onBack && window.__onBack()) ? 1 : 0", value -> {
            if (!"1".equals(value)) finish();
        });
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }

    // ---------------------------------------------------------------- utilidades

    private void js(String code) {
        if (web != null) web.evaluateJavascript(code, null);
    }

    private static String q(String s) {
        return JSONObject.quote(s == null ? "" : s);
    }

    private static String errorText(Exception e) {
        String m = e.getMessage();
        return (m == null || m.isEmpty()) ? e.getClass().getSimpleName() : m;
    }

    private Uri dbUri() {
        String s = prefs.getString(KEY_URI, null);
        return s == null ? null : Uri.parse(s);
    }

    private String displayName(Uri uri) {
        try (Cursor c = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                String n = c.getString(0);
                if (n != null) return n;
            }
        } catch (Exception ignored) {
        }
        String last = uri.getLastPathSegment();
        if (last == null) return "archivo .json";
        int i = last.lastIndexOf('/');
        return i >= 0 ? last.substring(i + 1) : last;
    }

    private static String readAll(InputStream in) throws Exception {
        if (in == null) throw new Exception("no se pudo abrir el archivo");
        try (InputStream is = in; ByteArrayOutputStream bos = new ByteArrayOutputStream()) {
            byte[] buf = new byte[16384];
            int n;
            while ((n = is.read(buf)) > 0) bos.write(buf, 0, n);
            String s = new String(bos.toByteArray(), StandardCharsets.UTF_8);
            if (s.startsWith("﻿")) s = s.substring(1);
            return s;
        }
    }

    private String readUri(Uri uri) throws Exception {
        return readAll(getContentResolver().openInputStream(uri));
    }

    private void writeUri(Uri uri, String text) throws Exception {
        byte[] bytes = (text == null ? "" : text).getBytes(StandardCharsets.UTF_8);
        OutputStream os = null;
        try {
            os = getContentResolver().openOutputStream(uri, "wt"); // "wt" = escribir y truncar
        } catch (Exception first) {
            os = getContentResolver().openOutputStream(uri, "rwt");
        }
        if (os == null) throw new Exception("no se pudo escribir el archivo");
        try (OutputStream o = os) {
            o.write(bytes);
            o.flush();
        }
    }

    private synchronized void writeCache(String text) {
        try {
            File tmp = new File(getFilesDir(), CACHE + ".tmp");
            try (FileOutputStream fos = new FileOutputStream(tmp)) {
                fos.write((text == null ? "" : text).getBytes(StandardCharsets.UTF_8));
                fos.getFD().sync();
            }
            File dst = new File(getFilesDir(), CACHE);
            if (!tmp.renameTo(dst)) {
                try (FileOutputStream fos = new FileOutputStream(dst)) {
                    fos.write((text == null ? "" : text).getBytes(StandardCharsets.UTF_8));
                }
                //noinspection ResultOfMethodCallIgnored
                tmp.delete();
            }
        } catch (Exception ignored) {
        }
    }

    private void takePermission(Uri uri, Intent data) {
        int rw = Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION;
        try {
            getContentResolver().takePersistableUriPermission(uri, rw);
        } catch (Exception e) {
            try {
                int granted = data.getFlags() & rw;
                if (granted != 0) getContentResolver().takePersistableUriPermission(uri, granted);
            } catch (Exception ignored) {
            }
        }
    }

    private void launch(Intent intent, int request) {
        runOnUiThread(() -> {
            try {
                startActivityForResult(intent, request);
            } catch (Exception e) {
                js("window.__nativeSaved && window.__nativeSaved(false, " + q("No se pudo abrir el selector de archivos: " + errorText(e)) + ")");
            }
        });
    }

    // ---------------------------------------------------------------- resultados del selector

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        Uri uri = (resultCode == RESULT_OK && data != null) ? data.getData() : null;

        if (uri == null) {
            if (requestCode == REQ_EXPORT) pendingExport = null;
            return;
        }

        switch (requestCode) {
            case REQ_CREATE_DB:
            case REQ_OPEN_DB: {
                takePermission(uri, data);
                String prev = prefs.getString(KEY_URI, null);
                SharedPreferences.Editor ed = prefs.edit().putString(KEY_URI, uri.toString());
                if (prev != null && !prev.equals(uri.toString())) ed.putString(KEY_PREV_URI, prev);
                else ed.remove(KEY_PREV_URI);
                ed.apply();
                String mode = requestCode == REQ_CREATE_DB ? "created" : "opened";
                js("window.__dbReady && window.__dbReady(" + q(mode) + ")");
                break;
            }
            case REQ_EXPORT: {
                try {
                    writeUri(uri, pendingExport);
                    js("window.__nativeSaved && window.__nativeSaved(true, " + q("Archivo guardado: " + displayName(uri)) + ")");
                } catch (Exception e) {
                    js("window.__nativeSaved && window.__nativeSaved(false, " + q("No se pudo guardar: " + errorText(e)) + ")");
                }
                pendingExport = null;
                break;
            }
            case REQ_IMPORT: {
                try {
                    String text = readUri(uri);
                    js("window.__nativeImport && window.__nativeImport(" + q(text) + ")");
                } catch (Exception e) {
                    js("window.__nativeSaved && window.__nativeSaved(false, " + q("No se pudo leer el archivo: " + errorText(e)) + ")");
                }
                break;
            }
            default:
                break;
        }
    }

    // ---------------------------------------------------------------- puente JavaScript

    private class Bridge {

        @JavascriptInterface
        public String status() {
            JSONObject o = new JSONObject();
            try {
                Uri u = dbUri();
                o.put("hasFile", u != null);
                o.put("name", u != null ? displayName(u) : "");
            } catch (Exception ignored) {
            }
            return o.toString();
        }

        @JavascriptInterface
        public synchronized String load() {
            JSONObject o = new JSONObject();
            try {
                Uri u = dbUri();
                if (u == null) {
                    o.put("ok", false);
                    o.put("error", "no hay archivo elegido");
                } else {
                    o.put("ok", true);
                    o.put("text", readUri(u));
                }
            } catch (Exception e) {
                try {
                    o.put("ok", false);
                    o.put("error", errorText(e));
                } catch (Exception ignored) {
                }
            }
            return o.toString();
        }

        @JavascriptInterface
        public synchronized String save(String text) {
            writeCache(text);
            Uri u = dbUri();
            if (u == null) return "no hay archivo elegido";
            try {
                writeUri(u, text);
                return "ok";
            } catch (Exception e) {
                return errorText(e);
            }
        }

        @JavascriptInterface
        public String loadCache() {
            try {
                File f = new File(getFilesDir(), CACHE);
                if (!f.exists()) return "";
                return readAll(new FileInputStream(f));
            } catch (Exception e) {
                return "";
            }
        }

        @JavascriptInterface
        public void saveCache(String text) {
            writeCache(text);
        }

        @JavascriptInterface
        public void createDb() {
            Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            i.addCategory(Intent.CATEGORY_OPENABLE);
            i.setType("application/json");
            i.putExtra(Intent.EXTRA_TITLE, "td2-drops.json");
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                    | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            launch(i, REQ_CREATE_DB);
        }

        @JavascriptInterface
        public void openDb() {
            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            i.addCategory(Intent.CATEGORY_OPENABLE);
            i.setType("*/*");
            i.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"application/json", "text/plain", "application/octet-stream"});
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                    | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            launch(i, REQ_OPEN_DB);
        }

        /** Vuelve al archivo anterior si el recién elegido no era válido. */
        @JavascriptInterface
        public void revert() {
            String prev = prefs.getString(KEY_PREV_URI, null);
            SharedPreferences.Editor ed = prefs.edit().remove(KEY_PREV_URI);
            if (prev != null) ed.putString(KEY_URI, prev);
            else ed.remove(KEY_URI);
            ed.apply();
        }

        @JavascriptInterface
        public void exportFile(String name, String mime, String content) {
            pendingExport = content;
            Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            i.addCategory(Intent.CATEGORY_OPENABLE);
            i.setType(mime == null || mime.isEmpty() ? "application/octet-stream" : mime);
            i.putExtra(Intent.EXTRA_TITLE, name);
            launch(i, REQ_EXPORT);
        }

        @JavascriptInterface
        public void importFile() {
            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            i.addCategory(Intent.CATEGORY_OPENABLE);
            i.setType("*/*");
            i.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"application/json", "text/plain", "application/octet-stream"});
            launch(i, REQ_IMPORT);
        }

        @JavascriptInterface
        public String copy(String text) {
            try {
                ClipboardManager cm = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                cm.setPrimaryClip(ClipData.newPlainText("Drops TD2", text));
                return "ok";
            } catch (Exception e) {
                return errorText(e);
            }
        }
    }
}
