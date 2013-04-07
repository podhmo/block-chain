# -*- coding:utf-8 -*-
from zope.interface import (
    Interface,
    implementer
    )
import operator as op
import functools
import itertools

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
 
class BoundAccess(object): #Not deleayed.
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

assert VirtualObject()["x"]["y"].value({"x": {"y": 10}}) == 10
assert VirtualObject(IdentityAccess)["x"]["y"].value({"x": {"y": 10}}) == 10
assert VirtualObject().f(10).value(type("",(),{"f": lambda self,x: x*x})()) == 100

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

## main (sample code)
def string_append(prefix, x):
    return prefix + x

class A:
    class x:
        class y:
            z = 10

class Wrapper(object):
    def __init__(self, v):
        self.v = v
    def wrap(self, x):
        return [x, self.v, x]

cc = OnContextChainFactory(functools.partial(VirtualObject, WrappedAccess))
assert cc.chain.do(cc.x.y.z)(StopContext(),  A) == 10
assert cc.chain.do(cc["x"]["y"]["z"])(StopContext(),  {"x": {"y": {"z": 10}}}) == 10
assert cc.chain.do(cc.x.x.y.z)(StopContext(),  A) == NIL
assert cc.chain.do(cc["x"]["y"]).do(cc(string_append,  "!"))(StopContext(),  {"x": {"y": "foo"}}) == "foo!"
assert cc.chain.do(cc.wrap("a"))(StopWithErrorMessageContext(), Wrapper("value")) == ["a", "value", "a"]
assert repr(cc.chain.do(cc.x.x.y.z)(StopWithErrorMessageContext(),  A)) == u"""'Failure':AttributeError("class x has no attribute 'x'",)"""

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

ctx = StateContext()
assert cc.chain(ctx, ctx.unit(10))(0) == (0, 10)
assert cc.chain.do(inc).do(inc)(ctx, ctx.unit(10))(0) == (2, 10)
assert cc.chain.do(inc).do(inc).do(put(100)).do(inc).do(inc)(ctx, ctx.unit(10))(0) == (102, 10)
assert cc.chain.do(inc).map(lambda x : x + 10)(ctx, ctx.unit(10))(0) == (1, 20)


# ## Stateful

def twice(ctx, _):
    return lambda s: (s, s*s)
assert cc.chain.do(cc["x"])(ctx, ctx.unit({"x": 100}))(10) == (10, 100)
assert cc.chain.do(inc).do(cc["x"])(ctx, ctx.unit({"x": 100}))(10) == (11, 100)
assert cc.chain.do(cc["x"]).do(inc)(ctx, ctx.unit({"x": 100}))(10) == (11, 100)
assert cc.chain.do(put(10)).do(inc).do(twice).do(twice).do(inc).do(twice)(ctx, ctx.unit(-1))(0) == (12, 144)
assert cc.chain.do(cc(lambda x: x+1))(ctx, ctx.unit(10))(0) == (0, 11)
class X:
    def sq(self, x):
        return x * x
assert  cc.chain.do(cc.sq(10))(ctx, ctx.unit(X()))(10) == (10, 100)
# this is not good. for python.

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


M = MultipleCandidatesContext()
assert cc.chain(M, M.unit(10)) == [10]
def tri(ctx, x):
    return [x, x+1, x]

assert cc.chain.do(tri).do(tri)(M, M.unit(10)) == [10, 11, 10, 11, 12, 11, 10, 11, 10]
assert cc.chain.do(tri).do(cc(lambda x: x*2))(M, M.unit(10)) == [20,22,20]
assert cc.chain.do(tri).do(cc.__add__(10))(M, M.unit(10)) == [20,21,20]



## map
assert cc.chain.map(lambda x : x+1)(StopContext(),NIL) == NIL
assert cc.chain.map(lambda x : x+1)(StopContext(), 10) == 11
assert cc.chain.map(lambda x,y : x+y ,12)(StopContext(), 10) == 22
assert cc.chain.map(lambda x,y : x+y ,NIL)(StopContext(), 10) == NIL
assert cc.chain.map(lambda x,y,z : [x,y,z] ,12, 13)(StopContext(), 11) == [11,12,13]
assert cc.chain.map(lambda x,y,z : [x,y,z] ,NIL, 12)(StopContext(), 11) == NIL

assert repr(cc.chain.map(lambda x : x+1)(StopWithErrorMessageContext(), Failure(10))) == "'Failure':10"
assert cc.chain.map(lambda x : x+1)(StopWithErrorMessageContext(), 10) == 11
assert cc.chain.map(lambda x,y : x+y ,12)(StopWithErrorMessageContext(), 10) == 22
assert repr(cc.chain.map(lambda x,y : x+y ,Failure(11))(StopWithErrorMessageContext(), 10)) == "'Failure':11"
assert cc.chain.map(lambda x,y,z : [x,y,z] ,12, 13)(StopWithErrorMessageContext(), 11) == [11,12,13]
assert repr(cc.chain.map(lambda x,y,z : [x,y,z] ,Failure(11), 12)(StopWithErrorMessageContext(), 11)) ==  "'Failure':11"
ctx = StateContext()
assert cc.chain.map(lambda x : x+1)(ctx, ctx.unit(10))(0) == (0,11)
assert cc.chain.map(lambda x,y : x+y ,ctx.unit(12))(ctx, ctx.unit(10))(0) == (0, 22)
assert cc.chain.map(lambda x,y : x+y, ctx.put(ctx.unit(12), 20))(ctx, ctx.unit(10))(0) == (20, 22)
assert cc.chain.map(lambda x,y : x+y, ctx.chain(ctx.unit(12)).put(20).value())(ctx, ctx.unit(10))(0) == (20, 22)
assert cc.chain.map(lambda x,y,z : [x,y,z], ctx.unit(12), ctx.chain(ctx.unit(13)).put(20).value())(ctx, ctx.unit(11))(0) == (20,  [11, 12, 13])

ctx = MultipleCandidatesContext()
assert cc.chain.map(lambda x : x+1)(ctx, [10,20,30]) == [11,21,31]
assert cc.chain.map(lambda x,y : x+y, [7,8,9])(ctx, [10,20,30]) == [17, 18, 19, 27, 28, 29, 37, 38, 39]
assert cc.chain.map(lambda x,y,z : [x,y,z], [7,8,9], ["a", "b"])(ctx, [10,20,30]) == [[10, 7, 'a'], [10, 7, 'b'], [10, 8, 'a'], [10, 8, 'b'], [10, 9, 'a'], [10, 9, 'b'], [20, 7, 'a'], [20, 7, 'b'], [20, 8, 'a'], [20, 8, 'b'], [20, 9, 'a'], [20, 9, 'b'], [30, 7, 'a'], [30, 7, 'b'], [30, 8, 'a'], [30, 8, 'b'], [30, 9, 'a'], [30, 9, 'b']]

# ## todo: guard function
# ## todo: interface change
# ## todo: alternative support
