# -*- coding: utf-8 -*-
from . import util
from .xml_base import XML_base
from .lookup import get_def_alias, DefQuery
from .def_filter_map import get_name_tag_by_def_tag


class BaseDef(XML_base):
    def __init__(self, name, *tag_vals, **kwargs):
        self.name = name
        self.tag_vals = tag_vals
        self.kwargs = kwargs

    def get_name(self):
        return self.name

    def get_def_tag_name(self):
        return '%sdef' % self.__class__.__name__.lower()

    def get_name_tag_name(self):
        return get_name_tag_by_def_tag(self.get_def_tag_name())

    def get_tag_val_pair(self, val):
        raise Exception("Need override")

    def get_tag_val_pairs(self, tag_vals):
        return map(self.get_tag_val_pair, tag_vals)

    def split_name_and_attrs(self, tag_name):
        name_parts = tag_name.split()

        if len(name_parts) > 1:
            # transform `key="value"` to `(key, value)`
            to_pair = lambda a: a.translate(None, '"\'').split('=')
            tag_attrs = dict(map(to_pair, name_parts[1:]))
        else:
            tag_attrs = {}

        name = name_parts[0]
        return (name, tag_attrs)

    def to_xml(self):
        xml_tree = self.create_tag(self.get_def_tag_name())
        name_tag = self.create_tag(self.get_name_tag_name(), self.name)
        xml_tree.append(name_tag)

        tag_val_pairs = self.get_tag_val_pairs(self.tag_vals)

        for tag_name, tag_val in tag_val_pairs:
            if len(tag_name) > 0 and len(tag_val) > 0:
                tag_name, tag_attrs = self.split_name_and_attrs(tag_name)
                tag = self.create_tag(tag_name, tag_val, attrib=tag_attrs)
                xml_tree.append(tag)

        return xml_tree


class App(BaseDef):
    def get_tag_val_pair(self, val):
        if len(val) == 0:
            return ()
        if val[0] == '.':
            return ('suffix', val)
        elif val[-1] == '.':
            return ('prefix', val)
        else:
            return ('equal', val)


class WindowName(BaseDef):
    def get_tag_val_pair(self, val):
        return ('regex', val)


class DeviceVendor(BaseDef):
    def get_tag_val_pair(self, val):
        return ('vendorid', val)


class DeviceProduct(BaseDef):
    def get_tag_val_pair(self, val):
        return ('productid', val)


class InputSource(BaseDef):
    def is_host(self, val):
        parts = val.split('.')
        return len(parts) > 3 and all(map(len, parts))

    def get_tag_val_pair(self, val):
        if len(val) == 0:
            return ()
        if val[-1] == '.':
            return ('inputsourceid_prefix', val[:-1])
        elif self.is_host(val):
            return ('inputsourceid_equal', val)
        else:
            return ('languagecode', val)


class VKChangeInputSource(InputSource):
    pass


class VKOpenURL(BaseDef):
    SCRIPT_FMT = '<![CDATA[\n{script}\n]]>'

    def get_tag_val_pair(self, val):
        if len(val) == 0:
            return ()
        elif val[0] == '/':
            return ('url type="file"', val)
        elif val.startswith('#!'):
            if val.startswith('#! '):
                val = val[3:]
            script = self.SCRIPT_FMT.format(script=val)
            return ('url type="shell"', script)
        else:
            return ('url', val)

    def to_xml(self):
        xml_tree = super(VKOpenURL, self).to_xml()
        if self.kwargs.get('background', False):
            background_tag = self.create_tag('background')
            xml_tree.append(background_tag)
        return xml_tree


class Replacement(BaseDef):
    def get_tag_val_pair(self, val):
        return ('replacementvalue', val)

    def get_tag_val_pairs(self, tag_vals):
        return [self.get_tag_val_pair(', '.join(tag_vals))]


class UIElementRole(BaseDef):
    def to_xml(self):
        xml_tree = self.create_tag(self.get_def_tag_name(), self.name)
        return xml_tree


_CLASSES = util.find_all_subclass_of(BaseDef, globals())

def split_clsname_defname(name):
    parts = name.split(':', 2)

    if name.startswith('KeyCode::VK_OPEN_URL_'):
        clsname = 'VKOpenURL'
        defname = name
    # clsname::defname
    elif len(parts) > 2:
        clsname = get_def_alias(parts[0], parts[0])
        defname = parts[-1]
    # {{defname}}
    elif name.startswith('{{') and name.endswith('}}'):
        clsname = 'Replacement'
        defname = name[2:-2]
    # defname
    else:
        clsname = 'App'
        defname = name

    return (clsname.strip(), defname.strip())

def parse_definition(name, vals):
    definition = None
    clsname, defname = split_clsname_defname(name)

    for cls in _CLASSES:
        if clsname == cls.__name__:
            definition = cls(defname, *vals)
            break

    if definition is None:
        raise Exception('Unsupport definition type')

    DefQuery.add_def(definition)
    return definition


if __name__ == "__main__":
    import doctest
    doctest.testmod()