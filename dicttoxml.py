#!/usr/bin/env python
# coding: utf-8

"""
Converts a native Python dictionary into an XML string.
Supports numbers, strings, lists, dictionaries and arbitrary nesting.
"""

from __future__ import unicode_literals

__version__ = '1.6.6'
version = __version__

from random import randint
import collections
import numbers
import logging
import sys
from xml.dom.minidom import parseString


LOG = logging.getLogger("dicttoxml")


if sys.version_info >= (3, 0, 0):
    unicode = str
    long = int

ids = []  # initialize list of unique ids


def set_debug(debug=True, filename='dicttoxml.log'):
    if debug:
        import datetime
        print('Debug mode is on. Events are logged at: {}'.format(filename))
        logging.basicConfig(filename=filename, level=logging.INFO)
        LOG.info('\nLogging session starts: {}'.format(
            datetime.datetime.today())
        )
    else:
        logging.basicConfig(level=logging.WARNING)
        print('Debug mode is off.')


def unicode_me(something):
    """
        Converts strings with non-ASCII characters to unicode for LOG.
        Python 3 doesn't have a `unicode()` function, so `unicode()` is
        an alias for `str()`, but `str()` doesn't take a second argument,
        hence this kludge.
    """
    try:
        return unicode(something, 'utf-8')
    except:
        return unicode(something)


def make_id(element, start=100000, end=999999):
    """
        Returns a random integer
    """
    return '%s_%s' % (element, randint(start, end))


def get_unique_id(element):
    """
        Returns a unique id for a given element
    """
    this_id = make_id(element)
    dup = True

    while dup is True:
        if this_id not in ids:
            dup = False
            ids.append(this_id)
        else:
            this_id = make_id(element)
    return ids[-1]


def get_xml_type(val):
    """
        Returns the data type for the xml type attribute
    """

    type_str_mapping = {
        str: 'str',
        unicode: 'str',
        int: 'int',
        long: 'int',
        float: 'float',
        bool: 'bool',
        numbers.Number: 'number',
        type(None): 'null',
        dict: 'dict',
        collections.Iterable: 'list'
    }

    for val_type, type_str in type_str_mapping:
        if isinstance(val, val_type):
            return type_str

    return type(val).__name__


def xml_escape(s):
    if type(s) in (str, unicode):
        s = unicode_me(s)  # avoid UnicodeDecodeError
        s = s.replace('&', '&amp;')
        s = s.replace('"', '&quot;')
        s = s.replace('\'', '&apos;')
        s = s.replace('<', '&lt;')
        s = s.replace('>', '&gt;')
    return s


def make_attrstring(attr):
    """
        Returns an attribute string in the form key="val"
    """
    attrstring = ' '.join(['%s="%s"' % (k, v) for k, v in attr.items()])
    return '%s%s' % (' ' if attrstring != '' else '', attrstring)


def key_is_valid_xml(key):
    """
        Checks that a key is a valid XML name
    """
    LOG.info('Inside key_is_valid_xml(). Testing "{}"'.format(unicode_me(key)))
    test_xml = '<?xml version="1.0" encoding="UTF-8" ?><{}>foo</{}>'.format(
        key, key
    )
    try:
        parseString(test_xml)
        return True
    except Exception:
        # minidom does not implement exceptions well
        return False


def make_valid_xml_name(key, attr):
    """
        Tests an XML name and fixes it if invalid
    """
    LOG.info(
        'Inside make_valid_xml_name(). Testing key "{}" with attr "{}"'.format(
            unicode_me(key), unicode_me(attr)
        )
    )

    # pass through if key is already valid
    if key_is_valid_xml(key):
        return key, attr

    # prepend a lowercase n if the key is numeric
    if key.isdigit():
        return 'n%s' % (key), attr

    # replace spaces with underscores if that fixes the problem
    if key_is_valid_xml(key.replace(' ', '_')):
        return key.replace(' ', '_'), attr

    # key is still invalid - move it into a name attribute
    attr['name'] = key
    key = 'key'
    return key, attr


def convert(obj, ids, attr_type, parent='root'):
    """
        Routes the elements of an object to the right function to
        convert them based on their data type
    """
    LOG.info(
        'Inside convert(). obj type is: "{}", obj="{}"'.format(
            type(obj).__name__,
            unicode_me(obj)
        )
    )

    if isinstance(obj, numbers.Number) or type(obj) in (str, unicode):
        return convert_kv('item', obj, attr_type)

    if hasattr(obj, 'isoformat'):
        return convert_kv('item', obj.isoformat(), attr_type)

    if type(obj) == bool:
        return convert_bool('item', obj, attr_type)

    if obj is None:
        return convert_none('item', '', attr_type)

    if isinstance(obj, dict):
        return convert_dict(obj, ids, parent, attr_type)

    if isinstance(obj, collections.Iterable):
        return convert_list(obj, ids, parent, attr_type)

    raise TypeError(
        'Unsupported data type: {} ({})'.format(obj, type(obj).__name__)
    )


def convert_dict(obj, ids, parent, attr_type):
    """
        Converts a dict into an XML string.
    """
    LOG.info(
        'Inside convert_dict(): obj type is: "{}", obj="{}"'.format(
            type(obj).__name__, unicode_me(obj)
        )
    )
    output = []
    addline = output.append

    for key, val in obj.items():
        LOG.info(
            'Looping inside convert_dict(): key="{}", '
            'val="{}", type(val)="{}"'.format(
                unicode_me(key), unicode_me(val), type(val).__name__
            )
        )

        attr = {} if not ids else {'id': '{}'.format(get_unique_id(parent))}
        key, attr = make_valid_xml_name(key, attr)

        if isinstance(val, numbers.Number) or type(val) in (str, unicode):
            addline(convert_kv(key, val, attr_type, attr))

        elif hasattr(val, 'isoformat'):
            # datetime
            addline(convert_kv(key, val.isoformat(), attr_type, attr))

        elif type(val) == bool:
            addline(convert_bool(key, val, attr_type, attr))

        elif isinstance(val, dict):
            if attr_type:
                attr['type'] = get_xml_type(val)
            addline(
                '<{}{}>{}</{}>'.format(
                    key, make_attrstring(attr),
                    convert_dict(val, ids, key, attr_type), key
                )
            )

        elif isinstance(val, collections.Iterable):
            if attr_type:
                attr['type'] = get_xml_type(val)
            addline(
                '<{}{}>{}</{}>'.format(
                    key, make_attrstring(attr),
                    convert_list(val, ids, key, attr_type), key
                )
            )

        elif val is None:
            addline(convert_none(key, val, attr_type, attr))

        else:
            raise TypeError('Unsupported data type: {} ({})'.format(
                val, type(val).__name__
            ))
    return ''.join(output)


def convert_list(items, ids, parent, attr_type):
    """
        Converts a list into an XML string.
    """
    LOG.info('Inside convert_list()')
    output = []
    addline = output.append

    if ids:
        this_id = get_unique_id(parent)

    for i, item in enumerate(items):
        LOG.info(
            'Looping inside convert_list(): item="{}", type="{}"'.format(
                unicode_me(item), type(item).__name__
            )
        )
        attr = {} if not ids else {'id': '{}_{}'.format(this_id, i + 1)}

        if isinstance(item, numbers.Number) or type(item) in (str, unicode):
            addline(convert_kv('item', item, attr_type, attr))

        elif hasattr(item, 'isoformat'):
            # datetime
            addline(convert_kv('item', item.isoformat(), attr_type, attr))

        elif type(item) == bool:
            addline(convert_bool('item', item, attr_type, attr))

        elif isinstance(item, dict):
            if not attr_type:
                addline(
                    '{}'.format(
                        convert_dict(item, ids, parent, attr_type)
                    )
                )
            else:
                addline(
                    '<item type="dict">{}</item>'.format(
                        convert_dict(item, ids, parent, attr_type)
                    )
                )

        elif isinstance(item, collections.Iterable):
            if not attr_type:
                addline(
                    '{}'.format(
                        convert_list(
                            item, ids, 'item', attr_type
                        )
                    )
                )
            else:
                addline(
                    '<item type="list"{}>{}</item>'.format(
                        make_attrstring(attr), convert_list(
                            item, ids, 'item', attr_type
                        )
                    )
                )

        elif item is None:
            addline(convert_none('item', None, attr_type, attr))

        else:
            raise TypeError(
                'Unsupported data type: {} ({})'.format(
                    item, type(item).__name__
                )
            )

    return ''.join(output)


def convert_kv(key, val, attr_type, attr={}):
    """
        Converts a number or string into an XML element
    """
    LOG.info(
        'Inside convert_kv(): key="{}", val="{}", type(val) is: "{}"'.format(
            unicode_me(key), unicode_me(val), type(val).__name__
        )
    )

    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr['type'] = get_xml_type(val)
    attrstring = make_attrstring(attr)
    return '<{}{}>{}</{}>'.format(
        key, attrstring, xml_escape(val), key
    )


def convert_bool(key, val, attr_type, attr={}):
    """
        Converts a boolean into an XML element
    """
    LOG.info(
        'Inside convert_bool(): key="{}", val="{}", '
        'type(val) is: "{}"'.format(
            unicode_me(key), unicode_me(val), type(val).__name__
        )
    )

    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr['type'] = get_xml_type(val)
    attrstring = make_attrstring(attr)
    return '<{}{}>{}</{}>'.format(key, attrstring, unicode(val).lower(), key)


def convert_none(key, val, attr_type, attr={}):
    """
        Converts a null value into an XML element
    """
    LOG.info('Inside convert_none(): key="{}"'.format(unicode_me(key)))

    key, attr = make_valid_xml_name(key, attr)

    if attr_type:
        attr['type'] = get_xml_type(val)
    attrstring = make_attrstring(attr)
    return '<{}{}></{}>'.format(
        key, attrstring, key
    )


def dicttoxml(obj, root=True, custom_root='root', ids=False, attr_type=True):
    """
        Converts a python object into XML
        attr_type is used to specify if data type for each element
        should be included in the resulting xml.
        By default, it is set to True.
    """
    LOG.info(
        'Inside dicttoxml(): type(obj) is: "{}", obj="{}"'.format(
            type(obj).__name__, unicode_me(obj)
        )
    )
    output = []
    addline = output.append

    if root is True:
        addline('<?xml version="1.0" encoding="UTF-8" ?>')
        addline(
            '<{}>{}</{}>'.format(
                custom_root, convert(obj, ids, attr_type, parent=custom_root),
                custom_root
            )
        )
    else:
        addline(convert(obj, ids, attr_type, parent=''))

    return ''.join(output).encode('utf-8')
