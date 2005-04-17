#
# Test queryCatalog and plone search forms
#

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
from Products.CMFPlone.tests import PloneTestCase

from Acquisition import aq_base
from Products.ZCTextIndex.ParseTree import ParseError
from Products.ZCatalog.Lazy import LazyCat

import types

try:
    import Products.TextIndexNG2
    txng_version = 2
except:
    txng_version = 0


class TestQueryCatalog(PloneTestCase.PloneTestCase):
    """Test queryCatalog script.

    Test function of queryCatalog script, **not** the
    functionality of the catalog itself. Therefore, we'll replace
    the actual call to the catalog to a dummy routine that just
    returns the catalog search dictionary so we can examine what
    would be searched.
    """

    def dummyCatalog(self, query_dict):
        return query_dict

    def stripTypes(self, query_dict):
        # strip portal_types parameter which is auto-set with
        # types blacklisting. Useful to simplify test assertions
        # when we don't care
        if type(query_dict) == types.DictType and query_dict.has_key('portal_type'):
            del query_dict['portal_type']
        return query_dict

    def afterSetUp(self):
        self.portal.portal_catalog.__call__ = self.dummyCatalog

    def testEmptyRequest(self):
        request = {}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), [])
        #self.failUnless(hasattr(aq_base(self.catalog), 'plone_lexicon'))
        #self.assertEqual(self.catalog.plone_lexicon.meta_type, 'ZCTextIndex Lexicon')

    def testNonexistantIndex(self):
        request = {'foo':'bar'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), [])

    def testNonexistantIndex(self):
        request = {'foo':'bar'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), [])

    def testRealIndex(self):
        request = {'SearchableText':'bar'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), 
                            {'SearchableText':'bar'})

    def testTwoIndexes(self):
        request = {'SearchableText':'bar','foo':'bar'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), 
                            {'SearchableText':'bar'})

    def testRealIndexes(self):
        request = {'SearchableText':'bar','Subject':'bar'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), 
                            request)

    def testOnlySort(self):
        # if we only sort, we shouldn't actually call the catalog
        request = {'sort_on':'foozle'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), [])
        request = {'sort_order':'foozle','sort_on':'foozle'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), [])
        request = {'sort_order':'foozle'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), [])

    def testOnlyUsage(self):
        request = {'date_usage':'range:min'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), [])

    def testRealWithUsage(self):
        request = {'modified':'2004-01-01','modified_usage':'range:min'}
        expected = {'modified': {'query': '2004-01-01', 'range': 'min'}}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), 
                            expected)

    def testSortLimit(self):
        # the script ignored 'sort_limit'; test to show it no longer does.
        request = {'SearchableText':'bar','sort_on':'foozle','sort_limit':50}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), 
                            request)

    def testBlacklistedTypes(self):
        request = {'SearchableText':'a*'}
        siteProps = self.portal.portal_properties.site_properties
        siteProps.unfriendly_types = ['Event', 'Unknown Type']
        qry = self.folder.queryCatalog(request,use_types_blacklist=True)
        self.failUnless('Document' in qry['portal_type'])
        self.failUnless('Event' not in qry['portal_type'])


class TestQueryCatalogQuoting(PloneTestCase.PloneTestCase):
    """Test logic quoting features queryCatalog script.

    Test function of queryCatalog script, **not** the
    functionality of the catalog itself. Therefore, we'll replace
    the actual call to the catalog to a dummy routine that just
    returns the catalog search dictionary so we can examine what
    would be searched.
    """

    def dummyCatalog(self, query_dict):
        return query_dict
        
    def stripTypes(self, query_dict):
        # strip portal_types parameter which is auto-set with
        # types blacklisting. Useful to simplify test assertions
        # when we don't care
        if type(query_dict) == types.DictType and query_dict.has_key('portal_type'):
            del query_dict['portal_type']
        return query_dict

    def afterSetUp(self):
        self.portal.portal_catalog.__call__ = self.dummyCatalog

    def testQuotingNone(self):
        request = {'SearchableText':'Hello Joel'}
        expected = request
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request, quote_logic=1)), expected)

    def testQuotingNotNeeded(self):
        request = {'SearchableText':'Hello or Joel'}
        expected = request
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request, quote_logic=1)), expected)

    def testQuotingNotNeededWithNot(self):
        request = {'SearchableText':'Hello or not Joel'}
        expected = request
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request, quote_logic=1)), expected)

    def testQuotingRequiredToEscape(self):
        request = {'SearchableText':'Hello Joel Or'}
        expected = {'SearchableText':'Hello Joel "Or"'}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request, quote_logic=1)), expected)

    def testQuotingRequiredToEscapeOptionOff(self):
        request = {'SearchableText':'Hello Joel Or'}
        expected = request
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), expected)

    def testQuotingWithLeadingNot(self):
        request = {'SearchableText':'Not Hello Joel'}
        expected = request
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), expected)

    def testEmptyItem(self):
        request = {'SearchableText':''}
        # queryCatalog will return empty result without calling the catalog tool
        expected = []
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request)), expected)

    def testEmptyItemShowAll(self):
        request = {'SearchableText':''}
        # Catalog gets a blank search, and returns the empty dict
        expected = {}
        self.assertEqual(self.stripTypes(self.folder.queryCatalog(request, show_all=1)), expected)


class TestQueryCatalogParseError(PloneTestCase.PloneTestCase):
    """Checks that the queryCatalog script returns an empty result set
       in case of ZCTextIndex ParseErrors.

       This testcase uses the real catalog, not a stub.
    """

    def afterSetUp(self):
        self.folder.invokeFactory('Document', id='doc', text='foo bar baz')

    def testSearchableText(self):
        request = {'SearchableText':'foo'}
        # We expect a non-empty result set
        self.failUnless(self.portal.queryCatalog(request))

    def testParseError(self):
        # ZCTextIndex raises ParseError
        self.assertRaises(ParseError, self.portal.portal_catalog, 
                          SearchableText='-foo')

    def testQueryCatalogParseError(self):
        request = {'SearchableText':'-foo'}
        # ZCTextIndex raises ParseError which translates to empty result
        expected = []
        self.assertEqual(self.portal.queryCatalog(request), expected)

    def testQueryCatalogParseError3050(self):
        # http://plone.org/collector/3050
        request = {'SearchableText':'AND'}
        # ZCTextIndex raises ParseError which translates to empty result
        expected = []
        self.assertEqual(self.portal.queryCatalog(request), expected)


# FIXME: This does currently not actually test for TXNG parse errors.
class TestTextIndexNGParseError(PloneTestCase.PloneTestCase):
    """Checks that the queryCatalog script returns an empty result set
       in case of TextIndexNG ParseErrors.

       This testcase uses the real catalog, not a stub.
    """

    def afterSetUp(self):
        self.folder.invokeFactory('Document', id='doc', text='foo bar baz')

    def testSearchableText(self):
        request = {'SearchableText':'foo'}
        # We expect a non-empty result set
        self.failUnless(self.portal.queryCatalog(request))

    def testParseError(self):
        # ZCTextIndex raises ParseError
        res = self.portal.portal_catalog(SearchableText='-foo')
        # -foo means NOT foo in TXNG2 which returns one object (the members 
        # folder + home folder of test user 1 + the news folder
        self.failUnlessEqual(len(res), 3, [b.getPath() for b in res])

    def testQueryCatalogParseError(self):
        request = {'SearchableText':'-foo'}
        # ZCTextIndex raises ParseError which translates to empty result
        res = self.portal.portal_catalog(SearchableText='-foo')
        # -foo means NOT foo in TXNG2 which returns one object (the members 
        # folder + home folder of test user 1 + the news folder
        self.failUnlessEqual(len(res), 3, [b.getPath() for b in res])

    def testQueryCatalogParseError3050(self):
        # http://plone.org/collector/3050
        request = {'SearchableText':'AND'}
        # ZCTextIndex raises ParseError which translates to empty result
        res = self.portal.queryCatalog(request)
        self.failUnless(isinstance(res, LazyCat))
        self.failUnlessEqual(len(res), 0)


AddPortalTopics = 'Add portal topics'

class TestSearchForms(PloneTestCase.PloneTestCase):
    """Render all forms related to queryCatalog"""

    def testRenderSearchForm(self):
        self.portal.search_form()

    def testRenderSearchResults(self):
        self.portal.search()

    def testRenderSearchRSS(self):
        self.portal.search_rss(self.portal, self.app.REQUEST)

    def testRenderTopicView(self):
        self.setPermissions([AddPortalTopics])
        self.folder.invokeFactory('Topic', id='topic')
        self.folder.topic.topic_view()
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestQueryCatalog))
    suite.addTest(makeSuite(TestQueryCatalogQuoting))

    if not txng_version:
        suite.addTest(makeSuite(TestQueryCatalogParseError))
    else:
        suite.addTest(makeSuite(TestTextIndexNGParseError))

    suite.addTest(makeSuite(TestSearchForms))
    return suite

if __name__ == '__main__':
    framework()
