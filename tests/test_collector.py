import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from collect_jobs import matched, board_candidates, rss_candidates, combine

class CollectorTest(unittest.TestCase):
    def test_filter_trainee_not_office_staff(self):
        self.assertTrue(matched('2026년 수습감정평가사 추가 모집'))
        self.assertTrue(matched('제36기 수습평가사 채용 공고'))
        self.assertFalse(matched('평가지원팀 신규직원 채용'))
        self.assertFalse(matched('감정평가사 소속 모집'))
    def test_official_board_only(self):
        html = '''<table><tr><td>수습평가사</td><td><a href="/sub/recruit/view.html?idx=42">2026년도 추가 모집 공고</a></td></tr>
          <tr><td><a href="https://other.example/hiring">수습감정평가사 모집</a></td></tr></table>'''
        rows=board_candidates('gaon', html, 'https://www.igaon.co.kr/sub/recruit/list.html')
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]['url'].startswith('https://www.igaon.co.kr/'))
        self.assertEqual(rows[0]['status'],'unknown')
    def test_rss_candidates_labeled(self):
        xml = '<rss><channel><item><title>태평양감정평가법인 수습감정평가사 채용</title><link>https://news.google.com/articles/abc</link></item></channel></rss>'
        rows = rss_candidates(xml)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['discovery'],'news-search')
    def test_history_preserved(self):
        rec = {'id':'gaon-a','firmId':'gaon','title':'old','url':'https://www.igaon.co.kr/foo','formUrl':'https://www.igaon.co.kr/form.docx','status':'closed'}
        new = {**rec,'formUrl':'','status':'unknown'}
        self.assertEqual(combine([rec],[new])[0]['formUrl'],rec['formUrl'])
        self.assertEqual(combine([rec],[new])[0]['status'],'closed')

if __name__ == '__main__': unittest.main()

# Additional regression tests for the expanded 13-company monitoring scope.
class ScopeConsistencyTest(unittest.TestCase):
    EXPECTED = ['samchang','kyungil','mirae','daehwa','hana','jeil','pacific','daeil','nara','joongang','daehan','gaon','garam']

    def test_exact_13_companies(self):
        from collect_jobs import FIRMS
        self.assertEqual(list(FIRMS), self.EXPECTED)
        self.assertEqual(len(FIRMS),13)
        self.assertEqual(len({x['host'] for x in FIRMS.values()}), 13)

    def test_html_scope_matches_collector(self):
        import re
        from collect_jobs import FIRMS
        html=(Path(__file__).resolve().parents[1]/'index.html').read_text('utf8')
        chunk=html.split('const FIRMS=[',1)[1].split('];\nconst STATIC_JOBS',1)[0]
        ids=re.findall(r'''(?:\bid|[\"']id[\"'])\s*:\s*[\"'](\w+)[\"']''', chunk)
        self.assertEqual(ids, self.EXPECTED)
        for fid, firm in FIRMS.items():
            self.assertIn(firm['name'], chunk)

    def test_rss_does_not_confuse_generic_hana_with_company(self):
        from collect_jobs import rss_candidates
        xml='''<rss><channel>
        <item><title>하나금융 수습평가사 채용 공고</title><link>https://news.google.com/generic</link></item>
        <item><title>하나감정평가법인 수습감정평가사 채용 공고</title><link>https://news.google.com/hana</link></item>
        <item><title>감정평가법인 대일감정원 수습감정평가사 모집</title><link>https://news.google.com/daeil</link></item>
        </channel></rss>'''
        items=rss_candidates(xml)
        self.assertEqual(len(items), 2)
        self.assertEqual({i['firmId'] for i in items}, {'hana','daeil'})

    def test_unknown_format_must_stay_unknown(self):
        from collect_jobs import make_record
        rec=make_record('daehan','대한감정평가법인 수습평가사 모집', 'https://kosal.co.kr/foo', 'official-board')
        self.assertEqual(rec['status'],'unknown')
        self.assertEqual(rec['formUrl'],'')
