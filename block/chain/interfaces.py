from zope.interface import (
    Interface,
    Attribute
    )

class IQuery(Interface):
    def value(*args, **kwargs):
        """ starting executing-query"""

class IMonoid(Interface):
    empty = Attribute("empty value")
    def append(other):
        """append value"""
    
class IFalsyValue(Interface):
    def __nonzero__():
        """it's must return False"""

class IAnySupport(Interface):
    def choice_another(f, g):
        """choice correct value. (f is failured value)"""

    def is_failure(v):
        pass

class IExecuteFlavor(Interface):
    """ this object has *the Context* of application"""
    def chain(initvalue):
        """ access chain.
          me.chain(me.unit(val0)).method(val1).value()
        this is same of.
          me.method(me.unit(val0), val1)
        """
        
    def unit(value):
        """ return wrapped value on themself iff need"""

    def apply(value):
        """ generate continuation on themself"""
    
    def lifted(f, v, *args, **kwargs):
        """ generate lifted function application on themself"""

    def map(f, v, *args):
        """ generate mapping function on themself.
        most likely, (a -*> b) -> (m a -*> m b)
        """

class IVirtualAccess(Interface):
    def attrgetter(k):
        """ such as, self.k"""

    def itemgetter(k):
        """ such as, self[k]"""

    def methodcaller(method, *args, **kwargs):
        """ such as, self.method(*args, **kwargs)"""
