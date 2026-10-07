#!/usr/bin/env python3
"""Cycle jour/nuit du profil : choisit l'ambiance d'après l'heure de Paris (fuseau du compte), bascule les liens d'image du README
et met à jour la ligne de statut (dernier push, dernières releases, nombre de dépôts) dans le fichier de l'ambiance en cours.
Les images des 4 ambiances sont commitées une seule fois ; seul le README (et au plus un SVG de statut) change."""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

USER, TZ = 'fmatsos', os.environ.get('PROFILE_TZ', 'Europe/Paris')
REPOS = ['gekko', 'shellkit', 'dot']
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def state(hour):                       # nuit 21-6, aube 6-9, jour 9-19, crépuscule 19-21
    return 'night' if hour >= 21 or hour < 6 else 'dawn' if hour < 9 else 'day' if hour < 19 else 'dusk'


def api(path):
    req = urllib.request.Request('https://api.github.com' + path, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'day-cycle'})
    if os.environ.get('GITHUB_TOKEN'): req.add_header('Authorization', 'Bearer ' + os.environ['GITHUB_TOKEN'])
    with urllib.request.urlopen(req, timeout=20) as r: return json.load(r)


def ago(dt, now):
    d = (now - dt).days
    return 'today' if d < 1 else 'yesterday' if d < 2 else f'{d} days ago'


def status_facts(now):
    ev = next(e for e in api(f'/users/{USER}/events/public?per_page=50') if e['type'] == 'PushEvent')
    pushed = datetime.fromisoformat(ev['created_at'].replace('Z', '+00:00'))
    rel = {}
    for r in REPOS:
        try: rel[r] = api(f'/repos/{USER}/{r}/releases/latest')['tag_name']
        except Exception: rel[r] = None
    return ev['repo']['name'], ago(pushed, now), rel, api(f'/users/{USER}')['public_repos']


def update_status(path, repo, when, rel, count, day):
    s = open(path, encoding='utf-8').read(); o = s
    s = re.sub(r'(last push </tspan><tspan fill="#FFF4E0"> )[^<]*(</tspan><tspan fill="#7F89B3"> · )[^<]*(</tspan>)', rf'\g<1>{repo}\g<2>{when}\g<3>', s)
    for r, tag in rel.items():
        if tag: s = re.sub(rf'({r} <tspan fill="#FFC857">)[^<]*(</tspan>)', rf'\g<1>{tag}\g<2>', s)
    s = re.sub(r'▸ \d+ public repos', f'▸ {count} public repos', s)
    s = re.sub(r'(updated by a scheduled GitHub Action · )[^<]*(<)', rf'\g<1>{day}\g<2>', s)
    s = re.sub(r'(aria-label="Live status: )[^"]*"', rf'\g<1>last push on {repo.split("/")[-1]} {when}; latest releases ' +
               ', '.join(f'{r} {t}' for r, t in rel.items() if t) + f'; {count} public repositories."', s)
    if s != o: open(path, 'w', encoding='utf-8').write(s)
    return s != o


def main():
    now = datetime.now(timezone.utc); paris = now.astimezone(ZoneInfo(TZ)); st = state(paris.hour)
    readme = os.path.join(ROOT, 'README.md'); txt = open(readme, encoding='utf-8').read()
    new = re.sub(r'(assets/(?:hero-mobile-static|hero-mobile|hero-static|hero|cert|stack|status|divider|gekko|shellkit|dot)-)(?:night|dawn|day|dusk)(\.(?:svg|webp))', rf'\g<1>{st}\g<2>', txt)
    if os.environ.get('SKIP_STATUS') != '1':
        try:
            repo, when, rel, count = status_facts(now)
            update_status(os.path.join(ROOT, 'assets', f'status-{st}.svg'), repo, when, rel, count, paris.strftime('%d %b %Y'))
        except Exception as e:
            print('statut non mis à jour :', e, file=sys.stderr)
    if new != txt: open(readme, 'w', encoding='utf-8').write(new)
    print(f'{paris:%Y-%m-%d %H:%M} {TZ} -> {st}' + (' (README mis à jour)' if new != txt else ''))


if __name__ == '__main__':
    assert state(5) == 'night' and state(6) == 'dawn' and state(9) == 'day' and state(19) == 'dusk' and state(21) == 'night' and state(0) == 'night'
    main()
