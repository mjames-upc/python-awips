##
##

import unittest
import urllib2

from HTMLParser import HTMLParser
from xml.etree.ElementTree import parse as parseXml
from json import load as loadjson
from urlparse import urljoin
from base64 import b64encode

#
# Test the localizaiton REST service.
#
# SOFTWARE HISTORY
#
# Date      Ticket#  Engineer  Description
# --------- -------- --------- --------------------------
# 08/07/17  5731     bsteffen  Initial Creation.

baseURL = "http://localhost:9581/services/localization/"
testSite = "OAX"
testDir = "menus"
testFile = "test.xml"
username = "test"
password =  username

base64string = b64encode('%s:%s' % (username, password))
authString = "Basic %s" % base64string

class ValidHTMLParser(HTMLParser):
    """Simple HTML parser that performs very minimal validation.

    This ensures that all start and end tags match, and also that there are
    some tags. It also accumulates the text of all links in the html file
    in the link_texts attribute, which can be used for further validation.
    """

    def __init__(self, testcase):
        HTMLParser.__init__(self)
        self._testcase = testcase
        self._tags = []
        self._any = False
        self.link_texts = []

    def handle_starttag(self, tag, attrs):
        self._tags.append(tag)
        self._any = True

    def handle_endtag(self, tag):
        self._testcase.assertNotEquals([], self._tags, "Unstarted end tag " + tag)
        self._testcase.assertEquals(tag, self._tags.pop())

    def handle_data(self, data):
        if self._tags[-1] == "a":
            self.link_texts.append(data)

    def close(self):
        HTMLParser.close(self)
        self._testcase.assertTrue(self._any)
        self._testcase.assertEquals([], self._tags)



class AbstractListingTestCase():
    """Base test case for testing listings, retrieves data as html, xml, and json.

    Sub classes should implement assertValidHtml, assertValidXml, and
    assertValidJson to ensure that the content returned matches what was
    expected.
    """

    def assertRequestGetsHtml(self, request):
        response = urllib2.urlopen(request)
        self.assertEquals(response.headers["Content-Type"], "text/html")
        body = response.read()
        parser = ValidHTMLParser(self)
        parser.feed(body)
        parser.close()
        self.assertValidHtml(parser)

    def assertValidHtml(self, parser):
        """Intended to be overriden by subclasses to validate HTML content.

        The argument is a populated instance of ValidHTMLParser.
        """
        pass

    def test_default(self):
        request = urllib2.Request(self.url)
        self.assertRequestGetsHtml(request)

    def test_last_slash(self):
        if self.url.endswith("/"):
            request = urllib2.Request(self.url[:-1])
        else:
            request = urllib2.Request(self.url + "/")
        self.assertRequestGetsHtml(request)

    def test_wild_mime(self):
        request = urllib2.Request(self.url)
        request.add_header("Accept", "*/*")
        self.assertRequestGetsHtml(request)
        request.add_header("Accept", "text/*")
        self.assertRequestGetsHtml(request)

    def test_html(self):
        request = urllib2.Request(self.url)
        request.add_header("Accept", "text/html")
        self.assertRequestGetsHtml(request)

    def test_json(self):
        request = urllib2.Request(self.url)
        request.add_header("Accept", "application/json")
        response = urllib2.urlopen(request)
        self.assertEquals(response.headers["Content-Type"], "application/json")
        jsonData = loadjson(response)
        self.assertValidJson(jsonData)


    def assertValidJson(self, jsonData):
        """Intended to be overriden by subclasses to validate JSON content.

        The argument is a python object as returned from json.load
        """
        pass

    def test_xml(self):
        request = urllib2.Request(self.url)
        request.add_header("Accept", "application/xml")
        response = urllib2.urlopen(request)
        self.assertEquals(response.headers["Content-Type"], "application/xml")
        xmlData = parseXml(response)
        self.assertValidXml(xmlData)

    def assertValidXml(self, xmlData):
        """Intended to be overriden by subclasses to validate XML content.

        The argument is an ElementTree
        """
        pass

    def test_delete(self):
        request = urllib2.Request(self.url)
        request.get_method = lambda: "DELETE"
        with self.assertRaises(urllib2.HTTPError) as cm:
            response = urllib2.urlopen(request)
        self.assertEqual(405, cm.exception.code)

    def test_put(self):
        request = urllib2.Request(self.url)
        request.get_method = lambda: "PUT"
        request.add_data("Test Data")
        with self.assertRaises(urllib2.HTTPError) as cm:
            response = urllib2.urlopen(request)
        self.assertEqual(405, cm.exception.code)

    def test_unacceptable(self):
        request = urllib2.Request(self.url)
        request.add_header("Accept", "application/fakemimetype")
        with self.assertRaises(urllib2.HTTPError) as cm:
            response = urllib2.urlopen(request)
        self.assertEqual(406, cm.exception.code)
        request.add_header("Accept", "fakemimetype/*")
        with self.assertRaises(urllib2.HTTPError) as cm:
            response = urllib2.urlopen(request)
        self.assertEqual(406, cm.exception.code)

    def test_accept_quality_factor(self):
        request = urllib2.Request(self.url)
        request.add_header("Accept", "application/xml; q=0.8, application/json; q=0.2")
        response = urllib2.urlopen(request)
        self.assertEquals(response.headers["Content-Type"], "application/xml")
        xmlData = parseXml(response)
        self.assertValidXml(xmlData)

        request.add_header("Accept", "application/xml; q=0.2, application/json; q=0.8")
        response = urllib2.urlopen(request)
        self.assertEquals(response.headers["Content-Type"], "application/json")
        jsonData = loadjson(response)
        self.assertValidJson(jsonData)

        request.add_header("Accept", "application/xml, application/json; q=0.8")
        response = urllib2.urlopen(request)
        self.assertEquals(response.headers["Content-Type"], "application/xml")
        xmlData = parseXml(response)
        self.assertValidXml(xmlData)

        request.add_header("Accept", "application/fakemimetype, application/json; q=0.8")
        response = urllib2.urlopen(request)
        self.assertEquals(response.headers["Content-Type"], "application/json")
        jsonData = loadjson(response)
        self.assertValidJson(jsonData)

class RootTestCase(AbstractListingTestCase, unittest.TestCase):
    """Test that the root of the localization service returns listing of localization types."""
    def setUp(self):
        self.url = baseURL
    def assertValidHtml(self, parser):
        self.assertIn("common_static/", parser.link_texts)
    def assertValidJson(self, jsonData):
        self.assertIn("common_static/", jsonData)
    def assertValidXml(self, xmlData):
        root = xmlData.getroot()
        self.assertEquals(root.tag, "entries")
        names = [e.text for e in root.findall("entry")]
        self.assertIn("common_static/", names)

class TypeTestCase(AbstractListingTestCase, unittest.TestCase):
    """Test that common_static will list context levels."""
    def setUp(self):
        self.url = urljoin(baseURL, "common_static/")
    def assertValidHtml(self, parser):
        self.assertIn("base/", parser.link_texts)
        self.assertIn("site/", parser.link_texts)
    def assertValidJson(self, jsonData):
        self.assertIn("base/", jsonData)
        self.assertIn("site/", jsonData)
    def assertValidXml(self, xmlData):
        root = xmlData.getroot()
        self.assertEquals(root.tag, "entries")
        names = [e.text for e in root.findall("entry")]
        self.assertIn("base/", names)
        self.assertIn("site/", names)

class LevelTestCase(AbstractListingTestCase, unittest.TestCase):
    """Test that common_static/site will list sites."""
    def setUp(self):
        self.url = urljoin(baseURL, "common_static/site/")
    def assertValidHtml(self, parser):
        self.assertIn(testSite +"/", parser.link_texts)
    def assertValidJson(self, jsonData):
        self.assertIn(testSite +"/", jsonData)
    def assertValidXml(self, xmlData):
        root = xmlData.getroot()
        self.assertEquals(root.tag, "entries")
        names = [e.text for e in root.findall("entry")]
        self.assertIn(testSite +"/", names)

class AbstractFileListingTestCase(AbstractListingTestCase):
    """Base test case for a file listing"""

    def assertValidHtml(self, parser):
        self.assertIn(testDir +"/", parser.link_texts)
        self.assertEquals(parser.link_texts, sorted(parser.link_texts))
    def assertValidJson(self, jsonData):
        self.assertIn(testDir +"/", jsonData)
    def assertValidXml(self, xmlData):
        root = xmlData.getroot()
        self.assertEquals(root.tag, "files")
        names = [e.get("name") for e in root.findall("file")]
        self.assertIn(testDir +"/", names)
        self.assertEquals(names, sorted(names))

class BaseFileListingTestCase(AbstractFileListingTestCase, unittest.TestCase):
    """Test that common_static/base lists files"""
    def setUp(self):
        self.url = urljoin(baseURL, "common_static/base/")

class SiteFileListingTestCase(AbstractFileListingTestCase, unittest.TestCase):
    """Test that common_static/site/<testSite>/ lists files"""
    def setUp(self):
        self.url = urljoin(baseURL, "common_static/site/" + testSite + "/")

class FileTestCase(unittest.TestCase):
    """Test retrieval, modification and deletion of an individual."""
    def setUp(self):
        self.url = urljoin(baseURL, "common_static/user/" + username + "/" + testFile)
        # The file should not exist before the test, but if it does then delete it
        # This is some of the same functionality we are testing so if setup fails
        # then the test would probably fail anyway
        try:
            request = urllib2.Request(self.url)
            response = urllib2.urlopen(request)
            request = urllib2.Request(self.url)
            request.get_method = lambda: "DELETE"
            request.add_header("Authorization", authString)
            request.add_header("If-Match", response.headers["Content-MD5"])
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            if e.code != 404:
                raise e
    def test_file_operations(self):
        """Run through a typical set of file interactions and verify everything works correctly."""
        request = urllib2.Request(self.url)
        request.get_method = lambda: "PUT"
        request.add_data("Test Data")
        with self.assertRaises(urllib2.HTTPError) as cm:
            response = urllib2.urlopen(request)
        self.assertEqual(401, cm.exception.code)

        request.add_header("Authorization", authString)
        with self.assertRaises(urllib2.HTTPError) as cm:
            response = urllib2.urlopen(request)
        self.assertEqual(409, cm.exception.code)

        request.add_header("If-Match", "NON_EXISTENT_CHECKSUM")
        response = urllib2.urlopen(request)


        request = urllib2.Request(self.url)
        response = urllib2.urlopen(request)
        self.assertEquals(response.read(), "Test Data")

        request = urllib2.Request(self.url + "/")
        response = urllib2.urlopen(request)
        self.assertEquals(response.read(), "Test Data")

        request = urllib2.Request(self.url)
        request.get_method = lambda: "PUT"
        request.add_data("Test Data2")
        request.add_header("If-Match", response.headers["Content-MD5"])
        request.add_header("Authorization", authString)
        response = urllib2.urlopen(request)
        checksum = response.headers["Content-MD5"]

        request = urllib2.Request(self.url)
        response = urllib2.urlopen(request)
        self.assertEquals(response.read(), "Test Data2")

        request = urllib2.Request(self.url)
        request.get_method = lambda: "DELETE"
        with self.assertRaises(urllib2.HTTPError) as cm:
            response = urllib2.urlopen(request)
        self.assertEqual(401, cm.exception.code)

        request.add_header("Authorization", authString)
        with self.assertRaises(urllib2.HTTPError) as cm:
            response = urllib2.urlopen(request)
        self.assertEqual(409, cm.exception.code)

        request.add_header("If-Match", checksum)
        response = urllib2.urlopen(request)

        request = urllib2.Request(self.url)
        with self.assertRaises(urllib2.HTTPError) as cm:
            response = urllib2.urlopen(request)
        self.assertEqual(404, cm.exception.code)

if __name__ == '__main__':
    unittest.main()
