# -*- coding:utf-8 -*-
import operator as op
import functools
import itertools

from zope.interface import implementer, provider
from block.chain.interfaces import (
    IQuery,
    IFalsyValue,
    IMonoid,
    IAnySupport,
    IExecuteFlavor,
    IVirtualAccess,
    ) 

### Wrapped value

@implementer(IFalsyValue, IMonoid)
class Failure(object):
    __slots__ = ["values", "delimiter", "mutable"]
    def __init__(self, value=None, values=None, delimiter=u"", mutable=False):
        self.values = values or [value]
        self.delimiter = delimiter
        self.mutable = mutable

    @property
    def empty(self):
        return self.__class__("", delimiter=self.delimiter)

    def append(self, other):
        if self.mutable:
            self.values.extend(other.values)
            return self
        else:
            vs = self.values[:]
            vs.extend(other.values)
            return self.__class__(values=vs, delimiter=self.delimiter, mutable=self.mutable)

    @property
    def value(self):
        return self.delimiter.join([unicode(v) for v in self.values])

    def __nonzero__(self):
        return False
    __bool__ = __nonzero__

    def __repr__(self):
        return u"{0}:{1}".format(repr(self.__class__.__name__), repr(self.values))


@implementer(IFalsyValue)
class _Nothing(object):
    def __nonzero__(self):
        return False
    __bool__ = __nonzero__
Nothing = _Nothing()


class MonoidBase(object):
    default = None
    def __init__(self, value=None, mutable=False):
        self._value = value or self.default
        self.mutable = mutable

    @classmethod
    def empty(cls, mutable=False):
        return cls(mutable)

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.value == other.value)

    @property
    def value(self):
        return self._value

@implementer(IMonoid)
class SumMonoid(MonoidBase):
    default = 0
    def append(self, other):
        if self.mutable:
            self._value += other._value
            return self
        else:
            value = self._value + other._value
            return self.__class__(value=value, mutable=False)
            
@implementer(IMonoid)
class ProductMonoid(MonoidBase):
    default = 1
    def append(self, other):
        if self.mutable:
            self._value *= other._value
            return self
        else:
            value = self._value * other._value
            return self.__class__(value=value, mutable=False)
            

@implementer(IMonoid)
class ListMonoid(MonoidBase):
    def __init__(self, value=None, mutable=False):
        self._value = value or []
        self.mutable = mutable

    def append(self, other):
        if self.mutable:
            self._value.extend(other._value)
            return self
        else:
            value = self._value[:]
            value.extend(other._value)
            return self.__class__(value=value, mutable=False)

@implementer(IMonoid)
class StringMonoid(ListMonoid):
    def __init__(self, value=None, mutable=False):
        if isinstance(value,(str,unicode)):
            self._value = [value]
        else:
            self._value = value or []
        self.mutable = mutable

    @property
    def value(self):
        return u"".join(self._value)

### Access registration

IdentityAccess = provider(IVirtualAccess)(op)
 
@implementer(IVirtualAccess)
class BoundAccess(object):
    def __init__(self,o):
        self.o = o

    def attrgetter(self, k):
        return getattr(self.o, k)

    def itemgetter(self, k):
        return self.o[k]

    def methodcaller(self, k, *args, **kwargs):
        def wrapped(v):
            return getattr(self.o, k)(v, *args, **kwargs)
        return wrapped

@provider(IVirtualAccess)
class WrappedAccess(object):
    @staticmethod
    def attrgetter(k):
        def wrapped(ctx, v):
            return ctx.lifted(getattr, v, k)
        return wrapped

    @staticmethod
    def itemgetter(k):
        def wrapped(ctx, v):
            return ctx.lifted(op.getitem, v, k)
        return wrapped

    @staticmethod
    def methodcaller(k, *args, **kwargs):
        def wrapped(ctx, o):
            return ctx.lifted(lambda o,k: getattr(o,k)(*args,**kwargs), o, k)
        return wrapped


@implementer(IQuery)
class VirtualObject(object):
    def __init__(self, access=IdentityAccess):
        self.access = access
        self.q = []
        self.names = []

    def __getattr__(self, k):
        self.q.append(self.access.attrgetter(k))
        self.names.append(k)
        return self

    def __getitem__(self, k):
        self.q.append(self.access.itemgetter(k))
        self.names.append(k)
        return self

    def __iter__(self):
        return iter(self.q)

    def __call__(self, *args, **kwargs):
        self.q.pop()
        k = self.names[-1]
        self.q.append(self.access.methodcaller(k,*args,**kwargs))
        return self

    def _const(self, v, name="*const*"):
        self.q.append(lambda _, : v)
        self.names.append(name)
        return self
    
    def value(self, o=None):
        return functools.reduce(lambda v, f:f(v), self, o)


### Chain
@implementer(IQuery)
class ChainedQuery(object):
    def __init__(self,  fs=None):
        self.fs = fs or []

    def do(self,  *fs):
        fs_ = self.fs[:]
        for f in fs:
            if hasattr(f, "__iter__"):
                def _do(ctx, v, *args, **kwargs):
                    for subf in f:
                        v = ctx.bind(v, subf, *args, **kwargs)
                    return v
                fs_.append(_do)
            else:
                def _do(ctx, v, *args, **kwargs):
                    return ctx.bind(v, f, *args, **kwargs)
                fs_.append(_do)
        return self.__class__(fs_)

    def map(self, f, *args):
        fs_ = self.fs[:]
        def _map(ctx, v):
            return ctx.map(f, v, *args)
        fs_.append(_map)
        return self.__class__(fs_)

    def value(self,  ctx,  init,  *args,  **kwargs):
        if not self.fs:
            return init
        v = self.fs[0](ctx, init, *args, **kwargs)
        for f in self.fs[1:]:
            v = f(ctx, v)
        return v

    def direct(self, f):
        fs_ = self.fs[:]
        fs_.append(f)
        return self.__class__(fs_)

class OnContextChainedQueryFactory(object):
    def __init__(self, vo_factory):
        self.vo_factory = vo_factory

    def __getattr__(self, k):
        vo = self.vo_factory()
        return getattr(vo, k)

    def __getitem__(self, k):
        vo = self.vo_factory()
        return vo[k]

    def __call__(self,  f,  *args,  **kwargs):
        def wrapped(ctx,v):
            return ctx.lifted(f, v, *args, **kwargs)
        return wrapped

    @property
    def chain(self):
        return ChainedQuery()

chain = OnContextChainedQueryFactory(functools.partial(VirtualObject, WrappedAccess))


### Any
class Any(object):
    def __init__(self, *fs):
        self.fs = fs

    def empty(self, ctx):
        return ctx.failure(None) #xxx:

    def choice(self, ctx):
        f = self.fs[0]
        if not ctx.is_failure(f):
            return f
        for g in self.fs[1:]:
            f = ctx.choice_another(f, g)
            if not ctx.is_failure(f):
                return f
        return f

### Executing Flavors
class Context(object):
    def chain(self, init):
        return VirtualObject(BoundAccess(self))._const(init, "*init*")

    def choice(self, v):
        if hasattr(v, "choice"):
            return v.choice(self)
        return v

    def choice_from(self, f, g):
        if self.is_failure(f):
            return self.choice_another(f, g)
        return f

@implementer(IExecuteFlavor, IAnySupport)
class MaybeF(Context):
    def failure(self, *args):
        return Nothing

    def is_failure(self, x):
        return x == Nothing

    def choice_another(self, f, g):
        return g

    def bind(self, v, f, *args, **kwargs):
        v = self.choice(v)
        if self.is_failure(v):
            return v
        else:
            return f(self, v, *args, **kwargs)

    def lifted(self, f, v, *args, **kwargs):
        try:
            return f(v, *args, **kwargs)
        except Exception as e:
            return self.failure(e)

    def map(self, f, v, *args):
        v = self.choice(v)

        if self.is_failure(v):
            return v
        if not args:
            return f(v)

        args_ = []
        for e in args:
            args_.append(self.choice(e))
            if self.is_failure(e):
                return e
        return f(v, *args_)

@implementer(IExecuteFlavor, IAnySupport)
class ErrorF(MaybeF):
    def failure(self,  v):
        return Failure(v)

    def choice_another(self, f, g):
        if self.is_failure(g):
            return f.append(g)
        return g           

    def is_failure(self, x):
        return not bool(x) and isinstance(x, Failure)

    def map(self, f, v, *args):
        v = self.choice(v)

        args_ = []
        failures = []

        if not args:
            if self.is_failure(v):
                return v
            return f(v)

        if self.is_failure(v):
            failures.append(v)

        for e in args:
            e = self.choice(e)
            args_.append(e)
            if self.is_failure(e):
                failures.append(e)
        if failures:
            return functools.reduce(self.choice_another, failures)
        return f(v, *args_)

@implementer(IExecuteFlavor)
class StateF(Context):
    def unit(self, v):
        return lambda s : (s,v)

    ## state : s -> (s, v)
    ## a -> ma -> ma -> mb
    def bind(self, ma, f, *args, **kwargs):
        def wrapped(s):
            s1, v = ma(s)
            fk = f(self, v, *args, **kwargs)
            return fk(s1)
        return wrapped

    def lifted(self, f, v, *args, **kwargs):
        return self.unit(f(v, *args, **kwargs))

    def map(self, f, ma, *args):
        if not args:
            def wrapped(s):
                s, x = ma(s)
                return (s, f(x))
        def wrapped_multi(s):
            s, v = ma(s)
            arguments = [v]
            for mx in args:
                s, v = mx(s)
                arguments.append(v)
            return s, f(*arguments)
        return wrapped_multi

    def put(self, mx, n):
        return lambda _: mx(n)

def inc(ctx, v):
    return lambda s: (s+1,v)

def put(n):
    def wrapped(ctx, v):
        return lambda s: (n, v)
    return wrapped

def get(ctx, v):
    return lambda s: (s, s)

class ListF(Context):
    def unit(self, v):
        return [v]

    def bind(self, xs, f, *args, **kwargs):
        r = []
        for x in xs:
            r.extend(f(self, x))
        return r

    def lifted(self, f, v, *args, **kwargs):
        return self.unit(f(v, *args, **kwargs))

    def map(self, f, vs, *args): #wa:
        if not args:
            return [f(v) for v in vs]
        return [f(*es) for es in itertools.product(vs, *args)]

class WriterF(Context):
    def __init__(self, monoid_class):
        self.monoid = monoid_class

    def unit(self, v):
        return (self.monoid.empty(), v)

    def bind(self, (m0,v0), f, *args, **kwargs):
        m1, v = f(self, v0, *args, **kwargs)
        return (m0.append(m1),v)
        
    def lifted(self, f, v, *args, **kwargs):
        return self.unit(f(v, *args, **kwargs))

    def map(self, f, (m,v), *args, **kwargs):
        return (m, f(v, *args, **kwargs))

    ## utility
    def tell(self, w):
        return lambda ctx, v: (ctx.monoid(value=w), v)

    def listen(self, ctx, (m, v)):
        return (m, (m, v))
    
    def passing(self, update):
        def wrapped(ctx, (m, v)):
            return (update(m, v), v)
        return wrapped
        
"""

"""
# ## todo: guard function
# ## todo: interface change
# ## todo: alternative support
