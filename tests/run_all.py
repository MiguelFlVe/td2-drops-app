#!/usr/bin/env python3
"""Runs the browser tests against app/src/main/assets/index.html.

Usage:  python3 tests/run_all.py
Needs:  pip install playwright   (plus a Chromium that Playwright can launch)

Each test is served over a local HTTP server (file:// localStorage is unreliable in headless Chromium).
test_base.py gets its own folder with tests/fixtures/base-data.js instead of the app's (empty) base data.
Screenshots go to tests/out/ (ignored by git).
"""
import functools, http.server, os, pathlib, shutil, subprocess, sys, tempfile, threading

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / 'app' / 'src' / 'main' / 'assets'
TESTS = ['test_flow.py', 'test_odds.py', 'test_misc.py', 'test_base.py', 'test_core_strength.py', 'test_first_sight.py']

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(directory):
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(directory)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return 'http://127.0.0.1:%d/index.html' % srv.server_address[1]

def main():
    app_url = serve(ASSETS)
    base_dir = pathlib.Path(tempfile.mkdtemp(prefix='td2-base-'))
    shutil.copy(ASSETS / 'index.html', base_dir / 'index.html')
    shutil.copy(HERE / 'fixtures' / 'base-data.js', base_dir / 'base-data.js')
    base_url = serve(base_dir)
    total_pass = total_fail = 0
    for t in TESTS:
        env = dict(os.environ, TD2_URL=base_url if t == 'test_base.py' else app_url)
        r = subprocess.run([sys.executable, str(HERE / t)], env=env, capture_output=True, text=True, timeout=600)
        out = r.stdout.splitlines()
        passed = sum(l.startswith('PASS') for l in out)
        failed = [l for l in out if l.startswith('FAIL')]
        page_errors = [l for l in out if l.startswith('ERRORS') and l.strip() != 'ERRORS []']
        bad = failed + page_errors + ([r.stderr.strip()] if r.returncode else [])
        total_pass += passed; total_fail += len(bad)
        print(f'{t:22s} {passed:3d} passed' + (f', {len(bad)} problem(s)' if bad else ''))
        for l in bad: print('    ' + l)
    shutil.rmtree(base_dir, ignore_errors=True)
    print(f'TOTAL: {total_pass} passed, {total_fail} problem(s)')
    return 1 if total_fail else 0

if __name__ == '__main__':
    sys.exit(main())
