#!/usr/bin/env python3
"""Convierte un respaldo de Drops TD2 (Historial → Guardar copia) en los datos base de la app.

Uso:
    python3 tools/actualizar_datos_base.py respaldo.json --label "Temporada Red Horizon"

Escribe app/src/main/assets/base-data.js. Por privacidad, quita las notas y las fechas de cada drop
(el repositorio es público); conserva el id para no contar dos veces los drops que el usuario ya tiene.
"""
import argparse, json, pathlib, sys

CAMPOS = ('id', 'cat', 'clase', 'sub', 'core', 'core1', 'core2', 'minors', 'talent')
DESTINO = pathlib.Path(__file__).resolve().parent.parent / 'app' / 'src' / 'main' / 'assets' / 'base-data.js'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('respaldo', nargs='?', help='archivo .json exportado desde la app (vacío = sin datos base)')
    ap.add_argument('--label', default='Datos base', help='nombre que se muestra en la app')
    ap.add_argument('--salida', default=str(DESTINO), help='ruta del base-data.js a escribir')
    a = ap.parse_args()
    drops = []
    if a.respaldo:
        data = json.loads(pathlib.Path(a.respaldo).read_text(encoding='utf-8-sig'))
        lista = data if isinstance(data, list) else data.get('drops', [])
        vistos = set()
        for d in lista:
            if not isinstance(d, dict) or d.get('cat') not in ('Equipo', 'Arma') or not d.get('sub'):
                continue
            if d.get('id') in vistos:
                continue
            vistos.add(d.get('id'))
            drops.append({k: d[k] for k in CAMPOS if k in d and d[k] is not None})
    contenido = {'label': a.label, 'drops': drops}
    salida = pathlib.Path(a.salida)
    salida.write_text(
        '/* Datos base de Drops TD2. Generado por tools/actualizar_datos_base.py — no editar a mano. */\n'
        'window.TD2_BASE = ' + json.dumps(contenido, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')
    eq = sum(1 for d in drops if d['cat'] == 'Equipo')
    print(f'{salida.name}: {len(drops)} drops ({eq} equipo, {len(drops) - eq} armas) · "{a.label}"')

if __name__ == '__main__':
    sys.exit(main())
