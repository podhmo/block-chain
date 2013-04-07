# -*- coding:utf-8 -*-
import operator as op
import functools
import itertools

from zope.interface import implementer
from block.chain.interfaces import IExecuteFlavor

### Wrapped value

class Failure(object):
    __slots__ = ["value"]
    def __init__(self, value):
        self.value = value
    def __nonzero__(self):
        return False
    __bool__ = __nonzero__
    def __repr__(self):
        return u"{0}:{1}".format(repr(self.__class__.__name__), repr(self.value))
    def __eq__(self, x):
        return self.value == x.value

class _Nil(object):
    def __nonzero__(self):
        return False
    __bool__ = __nonzero__
NIL = _Nil()


### Chain

class Chain(object):
    def __init__(self,  fs=None):
        self.fs = fs or []

    def do(self,  *fs):
        fs_ = self.fs[:]
        for f in fs:
            if hasattr(f,  "__iter__"):
                fs_.extend(f)
            else:
                fs_.append(f)
        return self.__class__(fs_)

    def map(self, f, *args):
        fs_ = self.fs[:]
        def _map(ctx, v):
            return ctx.map(f, v, *args)
        fs_.append(_map)
        return self.__class__(fs_)

    def __call__(self,  ctx,  init,  *args,  **kwargs):
        if not self.fs:
            return init
        cont = ctx.apply(init)
        v = cont(self.fs[0], *args, **kwargs)
        for f in self.fs[1:]:
            cont = ctx.apply(v)
            v = cont(f)
        return v

IdentityAccess = op
 
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


### Access Registration
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


class OnContextChainFactory(object):
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
        return Chain()


### Executing Flavors

class Context(object):
    def chain(self, init):
        return VirtualObject(BoundAccess(self))._const(init, "*init*")

@implementer(IExecuteFlavor)
class StopContext(Context):
    def failure(self, *args):
        return NIL

    def is_failure(self, x):
        return x == NIL

    def apply(self, v):
        if self.is_failure(v):
            return lambda f,  *args,  **kwargs: v
        else:
            return lambda f,  *args,  **kwargs: f(self, v,  *args, **kwargs)

    def lifted(self, f, v, *args, **kwargs):
        try:
            return f(v, *args, **kwargs)
        except Exception as e:
            return self.failure(e)

    def map(self, f, v, *args):
        if not args:
            return f(v)
        for e in args:
            if self.is_failure(e):
                return e
        return f(v, *args)

@implementer(IExecuteFlavor)
class StopWithErrorMessageContext(StopContext):
    def failure(self,  *args):
        return Failure(*args)

    def is_failure(self, x):
        return not bool(x)

@implementer(IExecuteFlavor)
class StateContext(Context):
    def unit(self, v):
        return lambda s : (s,v)

    ## state : s -> (s, v)
    def apply(self, fk, *args, **kwargs):
        def wrapped(g):
            def _wrapped(s):
                s1,v = fk(s)
                gk = g(self, v)
                return gk(s1)
            return _wrapped
        return wrapped

    def lifted(self, f, v, *args, **kwargs):
        return self.unit(f(v, *args, **kwargs))

    def map(self, f, x, *args):
        if not args:
            def wrapped(s):
                return (s, f(x))
        def wrapped_multi(s):
            arguments = [x]
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

# # Multiple
class MultipleCandidatesContext(Context):
    def unit(self, v):
        return [v]

    def apply(self, xs, *args, **kwargs):
        def wrapped(f):
            r = []
            for x in xs:
                r.extend(f(self, x))
            return r
        return wrapped

    def lifted(self, f, v, *args, **kwargs):
        return self.unit(f(v, *args, **kwargs))

    def map(self, f, v, *args): #wa:
        if not args:
            return self.unit(f(v))
        return [f(v, *vs) for vs in itertools.product(*args)]

# ## todo: guard function
# ## todo: interface change
# ## todo: alternative support
