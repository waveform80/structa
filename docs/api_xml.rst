==============
structa.xml
==============

.. module:: structa.xml

The :mod:`structa.xml` module provides methods for generating and manipulating
XML, primarily in the form of :mod:`xml.etree.ElementTree` objects. The main
class of interest is :class:`ElementFactory`, which can be used to generate
entire element-tree documents in a functional manner.

The :func:`xml` function can be used in a similar manner to :class:`str` or
:func:`repr` to generate XML representations of supported objects (most
classes within :mod:`structa.types` support this). Finally,
:func:`get_transform` can be used to obtain XSLT trees defined by structa
(largely for display purposes).

.. autoclass:: ElementFactory

.. autofunction:: xml

.. autofunction:: get_transform

.. autofunction:: merge_siblings
