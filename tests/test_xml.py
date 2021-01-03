from unittest import mock

import pytest
from lxml.etree import tostring, XML

from structa.xml import *


tag = ElementFactory()


def test_xml():
    class MyObj:
        def __xml__(self):
            return tag.foo()
    assert tostring(xml(MyObj())) == b'<foo/>'


def test_get_transform():
    assert isinstance(get_transform('cli.xsl'), et.XSLT)


def test_merge_siblings():
    x = XML('<doc><a>a</a><a>b</a><a>c</a><b>d</b><a>e</a></doc>')
    assert tostring(merge_siblings(x)) == b'<doc><a>abc</a><b>d</b><a>e</a></doc>'
    x = XML('<doc><a>a<a>b</a></a><a>c</a><b>d</b><a>e</a></doc>')
    assert tostring(merge_siblings(x)) == b'<doc><a>a<a>b</a>c</a><b>d</b><a>e</a></doc>'
    x = XML('<doc><a>a</a><a>b<a>c</a></a><b>d</b><a>e</a></doc>')
    assert tostring(merge_siblings(x)) == b'<doc><a>ab<a>c</a></a><b>d</b><a>e</a></doc>'


def test_element_factory_appends():
    assert tostring(tag.foo()) == b'<foo/>'
    assert tostring(tag.foo('')) == b'<foo/>'
    assert tostring(tag.foo('a')) == b'<foo>a</foo>'
    assert tostring(tag.foo('a', 'b')) == b'<foo>ab</foo>'
    assert tostring(tag.foo(tag.bar(), 'a')) == b'<foo><bar/>a</foo>'
    assert tostring(tag.foo(tag.bar(), 'a', 'b')) == b'<foo><bar/>ab</foo>'


def test_element_factory_formats():
    assert tostring(tag.foo(1, 2, 3)) == b'<foo>123</foo>'
    assert tostring(tag.foo([1, 2, 3])) == b'<foo>123</foo>'
    assert tostring(tag.foo([1, '2', 3])) == b'<foo>123</foo>'


def test_element_factory_namespace():
    ns_tag = ElementFactory(namespace='http://example.com/X')
    assert tostring(ns_tag.foo(bar=1)) == b'<ns0:foo xmlns:ns0="http://example.com/X" ns0:bar="1"/>'
