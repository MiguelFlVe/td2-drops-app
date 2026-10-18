(() => {
  const LS = window.localStorage;
  const get = k => LS.getItem('mock:' + k);
  const set = (k, v) => (v === null || v === undefined) ? LS.removeItem('mock:' + k) : LS.setItem('mock:' + k, v);
  window.__mockLog = [];
  window.AndroidDB = {
    status(){ const u = get('uri'); return JSON.stringify({hasFile: !!u, name: u || ''}); },
    load(){ const u = get('uri'); if (!u) return JSON.stringify({ok:false, error:'no file'});
      const f = get('file:' + u); if (f === null) return JSON.stringify({ok:false, error:'FileNotFoundException'});
      return JSON.stringify({ok:true, text:f}); },
    save(t){ set('cache', t); const u = get('uri'); if (!u) return 'no file';
      if (get('file:' + u) === null) return 'FileNotFoundException'; set('file:' + u, t); return 'ok'; },
    loadCache(){ return get('cache') || ''; },
    saveCache(t){ set('cache', t); },
    createDb(){ setTimeout(() => { const u = window.__mockNextName || 'td2-drops.json'; set('prev', get('uri')); set('uri', u); set('file:' + u, ''); window.__dbReady('created'); }, 10); },
    openDb(){ setTimeout(() => { const u = window.__mockNextName; set('prev', get('uri')); set('uri', u); window.__dbReady('opened'); }, 10); },
    revert(){ const p = get('prev'); set('uri', p); set('prev', null); },
    exportFile(name, mime, content){ window.__mockLog.push({name, mime, len: content.length}); setTimeout(() => window.__nativeSaved(true, 'Archivo guardado: ' + name), 10); },
    importFile(){ setTimeout(() => window.__nativeImport(window.__mockImportText), 10); },
    copy(t){ window.__mockCopied = t; return 'ok'; }
  };
})();
