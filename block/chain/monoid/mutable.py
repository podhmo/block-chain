from zope.interface import implementer
from .base import MonoidBase
from .base import IMonoid, IFalsyValue
from .base import FailureBase

@implementer(IFalsyValue, IMonoid)
class Failure(FailureBase):
    __slots__ = ["values", "delimiter"]
    def append(self, other):
        self.values.extend(other.values)
        return self

@implementer(IMonoid)
class SumMonoid(MonoidBase):
    default = 0
    __slots__ = ["_value"]
    def append(self, other):
        self._value += other._value
        return self
            
@implementer(IMonoid)
class ProductMonoid(MonoidBase):
    default = 1
    __slots__ = ["_value"]
    def append(self, other):
        self._value *= other._value
        return self

@implementer(IMonoid)
class ListMonoid(MonoidBase):
    __slots__ = ["_value"]
    def __init__(self, value=None):
        self._value = value or []

    def append(self, other):
        self._value.extend(other._value)
        return self

@implementer(IMonoid)
class StringMonoid(ListMonoid):
    __slots__ = ["_value"]
    def __init__(self, value=None):
        if isinstance(value,(str,unicode)):
            self._value = [value]
        else:
            self._value = value or []

    @property
    def value(self):
        return u"".join(self._value)

