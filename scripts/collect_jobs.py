#!/usr/bin/env python3
"""Responsible, no-login recruitment discovery for GitHub Actions.

Official-board links and Google News RSS are **candidates**, not authoritative
proof of an open trainee-appraiser position. No form URLs are guessed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
FIRMS = {
    'samchang': {'name': '삼창감정평가법인', 'terms': ['삼창감정평가', '삼창감정평가법인'], 'url': 'https://www.isamchang.com/', 'host': 'isamchang.com'},
    'kyungil': {'name': '경일감정평가법인', 'terms': ['경일감정평가', '경일감정평가법인'], 'url': 'http://www.kyungilnet.co.kr/', 'host': 'kyungilnet.co.kr'},
    'mirae': {'name': '미래새한감정평가법인', 'terms': ['미래새한감정평가', '미래새한'], 'url': 'https://www.msapp.co.kr/recruit/recruit3', 'host': 'msapp.co.kr'},
    'daehwa': {'name': '대화감정평가법인', 'terms': ['대화감정평가', '대화감정평가법인'], 'url': 'http://www.dhapp.co.kr/', 'host': 'dhapp.co.kr'},
    'hana': {'name': '하나감정평가법인', 'terms': ['하나감정평가', '하나감정평가법인'], 'url': 'https://haac.co.kr/', 'host': 'haac.co.kr'},
    'jeil': {'name': '제일감정평가법인', 'terms': ['제일감정평가', '제일감정평가법인'], 'url': 'https://www.facc.co.kr/', 'host': 'facc.co.kr'},
    'pacific': {'name': '태평양감정평가법인', 'terms': ['태평양감정평가'], 'url': 'https://www.packor.com/index.asp', 'host': 'packor.com'},
    'daeil': {'name': '감정평가법인 대일감정원', 'terms': ['대일감정원', '감정평가법인 대일감정원'], 'url': 'http://www.idab.co.kr/dab/ko/index.html', 'host': 'idab.co.kr'},
    'nara': {'name': '나라감정평가법인', 'terms': ['나라감정평가', '나라감정평가법인'], 'url': 'http://www.nara.ne.kr', 'host': 'nara.ne.kr'},
    'joongang': {'name': '중앙감정평가법인', 'terms': ['중앙감정평가', '중앙감정평가법인'], 'url': 'http://www.jaa.co.kr', 'host': 'jaa.co.kr'},
    'daehan': {'name': '대한감정평가법인', 'terms': ['대한감정평가', '대한감정평가법인'], 'url': 'https://kosal.co.kr/', 'host': 'kosal.co.kr'},
    'gaon': {'name': '가온감정평가법인', 'terms': ['가온감정평가', '가온감정평가법인'], 'url': 'https://www.igaon.co.kr/sub/recruit/list.html?curpage=1', 'host': 'igaon.co.kr'},
    'garam': {'name': '가람감정평가법인', 'terms': ['가람감정평가', '가람감정평가법인'], 'url': 'https://kaaram.com/kr/', 'host': 'kaaram.com'},
}
# Require an explicit trainee-appraiser phrase. Do not silently include office/support roles.
TRAINEE = re.compile(r'(?:수습\s*(?:감정\s*)?평가사|(?:제\s*\d+\s*기\s*)?수습\s*감정평가사)', re.I)
HIRING = re.compile(r'(채용|모집|선발|입사지원|구인|공고|신입)', re.I)
NOT_TRAINEE = re.compile(r'(평가지원팀|사무직|경리|총무직|기술직)', re.I)
DATE = re.compile(r'20\d{2}[./-]\s*\d{1,2}[./-]\s*\d{1,2}')
UA = {'User-Agent': 'PickthatRecruitMonitor/1.0 (public hiring notices; periodic low-rate checks)', 'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.7'}
TIMEOUT = (7, 17)


def matched(text: str) -> bool:
    text = ' '.join(text.split())
    return bool(TRAINEE.search(text) and HIRING.search(text) and not NOT_TRAINEE.search(text))


def normalized_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return ''
    return url.split('#', 1)[0]


def item_id(firm_id: str, url: str) -> str:
    return firm_id + '-' + hashlib.sha256(url.encode('utf-8')).hexdigest()[:20]


def iso_date(value: str) -> str:
    m = DATE.search(value)
    if not m:
        return ''
    try:
        y, mo, d = (int(x.strip()) for x in re.split('[./-]', m.group())[:3])
        return datetime(y, mo, d).date().isoformat()
    except ValueError:
        return ''


def make_record(firm_id: str, title: str, url: str, source: str, published: str = '') -> dict:
    # No inferred deadline, 'open' state or purported official application file link.
    return {'id': item_id(firm_id, url), 'firmId': firm_id, 'title': title[:195],
            'published': iso_date(published), 'deadline': '', 'url': url, 'formUrl': '',
            'status': 'unknown', 'discovery': source}


def board_candidates(firm_id: str, markup: str, base_url: str) -> list[dict]:
    """Extract actual links on *official* pages. Do not claim open status."""
    soup = BeautifulSoup(markup, 'html.parser')
    host = FIRMS[firm_id]['host']
    found = []
    for anchor in soup.select('a[href]'):
        title = ' '.join(anchor.get_text(' ', strip=True).split())
        if not matched(title):
            # Some boards put '수습평가사' in the category cell and only '모집 공고' in the link.
            parent = anchor.find_parent('tr')
            context = parent.get_text(' ', strip=True) if parent else ''
            if not matched(context):
                continue
            title = ' '.join((context[:40] + ' ' + title).split())
        url = normalized_url(urljoin(base_url, anchor.get('href', '').strip()))
        if not url:
            continue
        target_host = (urlparse(url).hostname or '').lower()
        if target_host != host and not target_host.endswith('.' + host):
            continue
        if url == normalized_url(base_url) or url.endswith('#'):
            continue
        found.append(make_record(firm_id, title, url, 'official-board', anchor.find_parent('tr').get_text(' ', strip=True) if anchor.find_parent('tr') else ''))
    # Fall back to the official board URL when the website uses JavaScript-only
    # detail links: show a board-level candidate instead of silently losing it.
    known_titles = {x['title'] for x in found}
    detail_url_count = len(found)
    for row in soup.select('tr'):
        title = ' '.join(row.get_text(' ', strip=True).split())
        if not matched(title) or title in known_titles:
            continue
        # A row with a matching *external* link is not an official-board entry.
        href_hosts = [(urlparse(urljoin(base_url, a.get('href', '').strip())).hostname or '').lower()
                      for a in row.select('a[href]') if (a.get('href') or '').strip()]
        if href_hosts and any(h != host and not h.endswith('.' + host) for h in href_hosts):
            continue
        if any((x['title'] in title or title in x['title']) and x['url'] != normalized_url(base_url) for x in found[:detail_url_count]):
            continue
        # Don't accidentally turn the entire table into one record.
        if len(title) > 300:
            continue
        board_url = normalized_url(base_url)
        if board_url:
            record = make_record(firm_id, title, board_url, 'official-board-no-detail')
            record['id'] = item_id(firm_id, board_url + '|' + title)
            found.append(record)
            known_titles.add(title)
    return found


def rss_candidates(xml_text: str) -> list[dict]:
    """Search index candidates; do not treat Google News as an official notice."""
    root = ET.fromstring(xml_text)
    found = []
    for el in root.findall('./channel/item'):
        title = (el.findtext('title') or '').strip()
        link = normalized_url((el.findtext('link') or '').strip())
        if not matched(title) or not link:
            continue
        firm_id = next((key for key, firm in FIRMS.items() if any(term in title for term in firm['terms'])), None)
        if not firm_id:
            continue
        found.append(make_record(firm_id, title, link, 'news-search'))
    return found


def request_text(session: requests.Session, url: str) -> str:
    response = session.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
    response.raise_for_status()
    ct = response.headers.get('Content-Type', '')
    if 'text/html' not in ct and 'xml' not in ct and 'text/plain' not in ct and ct:
        raise RuntimeError('Unexpected Content-Type ' + ct[:90])
    if not response.encoding or response.encoding.lower() == 'iso-8859-1':
        response.encoding = response.apparent_encoding or 'utf-8'
    return response.text[:2_500_000]


def collect(session: requests.Session, delay: float = 0.35) -> tuple[list[dict], dict]:
    out = []
    status = {'checkedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'officialBoards': {}, 'newsSearch': {},
              'note': '자동 탐색 결과는 미검증 후보이며 채용 진행 여부를 의미하지 않습니다.'}
    for fid, firm in FIRMS.items():
        try:
            html = request_text(session, firm['url'])
            items = board_candidates(fid, html, firm['url'])
            out.extend(items)
            status['officialBoards'][fid] = {'ok': True, 'newCandidates': len(items)}
        except Exception as exc:
            logging.warning('Official board %s failed: %s', fid, exc)
            status['officialBoards'][fid] = {'ok': False, 'error': str(exc)[:170]}
        if delay:
            time.sleep(delay)
    queries = [
        '"수습감정평가사" "채용"',
        '"수습평가사" "감정평가법인"',
    ]
    # Search each of the 13 firms individually to reduce reliance on two generic searches.
    queries.extend('"' + f['name'] + '" "수습"' for f in FIRMS.values())
    for q in queries:
        url = 'https://news.google.com/rss/search?q=' + quote(q, safe='') + '&hl=ko&gl=KR&ceid=KR:ko'
        try:
            items = rss_candidates(request_text(session, url))
            out.extend(items)
            status['newsSearch'][q] = {'ok': True, 'candidates': len(items)}
        except Exception as exc:
            logging.warning('News index %s failed: %s', q, exc)
            status['newsSearch'][q] = {'ok': False, 'error': str(exc)[:170]}
        if delay:
            time.sleep(delay)
    return out, status


def combine(existing: list[dict], new: list[dict], limit: int = 350) -> list[dict]:
    by_id = {}
    # Retain historical records; never overwrite user or hand-verified metadata with guesses.
    for rec in existing:
        if isinstance(rec, dict) and rec.get('id') and rec.get('firmId') in FIRMS and normalized_url(rec.get('url', '')):
            by_id[rec['id']] = rec
    for rec in new:
        if rec['id'] in by_id:
            old = by_id[rec['id']]
            # Do not flip the status or erase a verified form link.
            by_id[rec['id']] = {**rec, **old}
        else:
            by_id[rec['id']] = rec
    return sorted(by_id.values(), key=lambda x: (x.get('published',''), x.get('title',''), x.get('id','')), reverse=True)[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Do not write files')
    parser.add_argument('--delay', type=float, default=0.35)
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    output = DATA / 'jobs.json'
    try:
        previous = json.loads(output.read_text('utf-8')).get('jobs', []) if output.exists() else []
    except (ValueError, OSError):
        previous = []
    with requests.Session() as session:
        new, status = collect(session, max(0, args.delay))
    merged = combine(previous, new)
    status['uniqueCandidates'] = len({r['id'] for r in new})
    status['storedCandidates'] = len(merged)
    # Do not erase previously seen posts if external sources are temporarily unavailable.
    print(json.dumps(status, ensure_ascii=False, indent=2))
    if not args.dry_run:
        output.write_text(json.dumps({'jobs': merged}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (DATA / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Fail workflow only on truly fatal errors; per-source errors are reported in status.json.
    return 0


if __name__ == '__main__':
    sys.exit(main())
