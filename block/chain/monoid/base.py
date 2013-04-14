from block.chain.interfaces import (
    IMonoid,
    IFalsyValue
)

__all__ = ["IMonoid", "MonoidBase", 
           "IFalsyValue", "FailureBase"]


class MonoidBase(object):
    default = None
    def __init__(self, value=None):
        self._value = value or self.default

    @classmethod
    def empty(cls, mutable=False):
        return cls(mutable)

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.value == other.value)

    @property
    def value(self):
        return self._value

class FailureBase(object):
    __slots__ = ["values", "delimiter"]
    def __init__(self, value=None, values=None, delimiter=u""):
        self.values = values or [value]
        self.delimiter = delimiter

    @property
    def empty(self):
        return self.__class__("", delimiter=self.delimiter)

    @property
    def value(self):
        return self.delimiter.join([unicode(v) for v in self.values])

    def __nonzero__(self):
        return False
    __bool__ = __nonzero__

    def __repr__(self):
        return u"{0}:{1}".format(repr(self.__class__.__name__), repr(self.values))

