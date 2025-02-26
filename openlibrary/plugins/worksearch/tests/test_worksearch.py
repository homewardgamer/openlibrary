import pytest
from openlibrary.plugins.worksearch.code import (
    read_facets,
    sorted_work_editions,
    parse_query_fields,
    escape_bracket,
    run_solr_query,
    get_doc,
    build_q_list,
    escape_colon,
    parse_search_response,
)
from lxml import etree
from infogami import config


def test_escape_bracket():
    assert escape_bracket('foo') == 'foo'
    assert escape_bracket('foo[') == 'foo\\['
    assert escape_bracket('[ 10 TO 1000]') == '[ 10 TO 1000]'


def test_escape_colon():
    vf = ['key', 'name', 'type', 'count']
    assert (
        escape_colon('test key:test http://test/', vf) == 'test key:test http\\://test/'
    )


def test_read_facet():
    xml = '''<response>
        <lst name="facet_counts">
            <lst name="facet_fields">
                <lst name="has_fulltext">
                    <int name="false">46</int>
                    <int name="true">2</int>
                </lst>
            </lst>
        </lst>
    </response>'''

    expect = {'has_fulltext': [('true', 'yes', '2'), ('false', 'no', '46')]}
    assert read_facets(etree.fromstring(xml)) == expect


def test_sorted_work_editions():
    json_data = '''{
"responseHeader":{
"status":0,
"QTime":1,
"params":{
"fl":"edition_key",
"indent":"on",
"wt":"json",
"q":"key:OL100000W"}},
"response":{"numFound":1,"start":0,"docs":[
{
 "edition_key":["OL7536692M","OL7825368M","OL3026366M"]}]
}}'''
    expect = ["OL7536692M", "OL7825368M", "OL3026366M"]
    assert sorted_work_editions('OL100000W', json_data=json_data) == expect


# {'Test name': ('query', fields[])}
QUERY_PARSER_TESTS = {
    'No fields': ('query here', [{'field': 'text', 'value': 'query here'}]),
    'Author field': (
        'title:food rules author:pollan',
        [
            {'field': 'title', 'value': 'food rules'},
            {'field': 'author_name', 'value': 'pollan'},
        ],
    ),
    'Field aliases': (
        'title:food rules by:pollan',
        [
            {'field': 'title', 'value': 'food rules'},
            {'field': 'author_name', 'value': 'pollan'},
        ],
    ),
    'Fields are case-insensitive aliases': (
        'title:food rules By:pollan',
        [
            {'field': 'title', 'value': 'food rules'},
            {'field': 'author_name', 'value': 'pollan'},
        ],
    ),
    'Quotes': (
        'title:"food rules" author:pollan',
        [
            {'field': 'title', 'value': '"food rules"'},
            {'field': 'author_name', 'value': 'pollan'},
        ],
    ),
    'Leading text': (
        'query here title:food rules author:pollan',
        [
            {'field': 'text', 'value': 'query here'},
            {'field': 'title', 'value': 'food rules'},
            {'field': 'author_name', 'value': 'pollan'},
        ],
    ),
    'Colons in query': (
        'flatland:a romance of many dimensions',
        [
            {'field': 'text', 'value': r'flatland\:a romance of many dimensions'},
        ],
    ),
    'Colons in field': (
        'title:flatland:a romance of many dimensions',
        [
            {'field': 'title', 'value': r'flatland\:a romance of many dimensions'},
        ],
    ),
    'Operators': (
        'authors:Kim Harrison OR authors:Lynsay Sands',
        [
            {'field': 'author_name', 'value': 'Kim Harrison'},
            {'op': 'OR'},
            {'field': 'author_name', 'value': 'Lynsay Sands'},
        ],
    ),
    # LCCs
    'LCC: quotes added if space present': (
        'lcc:NC760 .B2813 2004',
        [
            {'field': 'lcc', 'value': '"NC-0760.00000000.B2813 2004"'},
        ],
    ),
    'LCC: star added if no space': (
        'lcc:NC760 .B2813',
        [
            {'field': 'lcc', 'value': 'NC-0760.00000000.B2813*'},
        ],
    ),
    'LCC: Noise left as is': (
        'lcc:good evening',
        [
            {'field': 'lcc', 'value': 'good evening'},
        ],
    ),
    'LCC: range': (
        'lcc:[NC1 TO NC1000]',
        [
            {'field': 'lcc', 'value': '[NC-0001.00000000 TO NC-1000.00000000]'},
        ],
    ),
    'LCC: prefix': (
        'lcc:NC76.B2813*',
        [
            {'field': 'lcc', 'value': 'NC-0076.00000000.B2813*'},
        ],
    ),
    'LCC: suffix': (
        'lcc:*B2813',
        [
            {'field': 'lcc', 'value': '*B2813'},
        ],
    ),
    'LCC: multi-star without prefix': (
        'lcc:*B2813*',
        [
            {'field': 'lcc', 'value': '*B2813*'},
        ],
    ),
    'LCC: multi-star with prefix': (
        'lcc:NC76*B2813*',
        [
            {'field': 'lcc', 'value': 'NC-0076*B2813*'},
        ],
    ),
    'LCC: quotes preserved': (
        'lcc:"NC760 .B2813"',
        [
            {'field': 'lcc', 'value': '"NC-0760.00000000.B2813"'},
        ],
    ),
    # TODO Add tests for DDC
}


@pytest.mark.parametrize(
    "query,parsed_query", QUERY_PARSER_TESTS.values(), ids=QUERY_PARSER_TESTS.keys()
)
def test_query_parser_fields(query, parsed_query):
    assert list(parse_query_fields(query)) == parsed_query


#     def test_public_scan(lf):
#         param = {'subject_facet': ['Lending library']}
#         (reply, solr_select, q_list) = run_solr_query(param, rows = 10, spellcheck_count = 3)
#         print solr_select
#         print q_list
#         print reply
#         root = etree.XML(reply)
#         docs = root.find('result')
#         for doc in docs:
#             assert get_doc(doc).public_scan == False


def test_get_doc():
    sample_doc = etree.fromstring(
        '''<doc>
<arr name="author_key"><str>OL218224A</str></arr>
<arr name="author_name"><str>Alan Freedman</str></arr>
<str name="cover_edition_key">OL1111795M</str>
<int name="edition_count">14</int>
<int name="first_publish_year">1981</int>
<bool name="has_fulltext">true</bool>
<arr name="ia"><str>computerglossary00free</str></arr>
<str name="key">OL1820355W</str>
<str name="lending_edition_s">OL1111795M</str>
<bool name="public_scan_b">false</bool>
<str name="title">The computer glossary</str>
</doc>'''
    )

    doc = get_doc(sample_doc)
    assert doc.public_scan == False


def test_build_q_list():
    param = {'q': 'test'}
    expect = (['test'], True)
    assert build_q_list(param) == expect

    param = {
        'q': 'title:(Holidays are Hell) authors:(Kim Harrison) OR authors:(Lynsay Sands)'
    }
    expect = (
        [
            'title:((Holidays are Hell))',
            'author_name:((Kim Harrison))',
            'OR',
            'author_name:((Lynsay Sands))',
        ],
        False,
    )
    query_fields = [
        {'field': 'title', 'value': '(Holidays are Hell)'},
        {'field': 'author_name', 'value': '(Kim Harrison)'},
        {'op': 'OR'},
        {'field': 'author_name', 'value': '(Lynsay Sands)'},
    ]
    assert list(parse_query_fields(param['q'])) == query_fields
    assert build_q_list(param) == expect


def test_parse_search_response():
    test_input = (
        '<pre>org.apache.lucene.queryParser.ParseException: This is an error</pre>'
    )
    expect = {'error': 'This is an error'}
    assert parse_search_response(test_input) == expect
    assert parse_search_response('{"aaa": "bbb"}') == {'aaa': 'bbb'}
