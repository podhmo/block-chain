import functools
def string_append(prefix, x):
    return prefix + x

from block.chain import OnContextChainFactory
from block.chain import WrappedAccess
from block.chain import VirtualObject
cc = OnContextChainFactory(functools.partial(VirtualObject, WrappedAccess))

def test_virtualobject():
    from block.chain import VirtualObject
    from block.chain import IdentityAccess
    from block.chain import BoundAccess

    assert VirtualObject()["x"]["y"].value({"x": {"y": 10}}) == 10
    assert VirtualObject(IdentityAccess)["x"]["y"].value({"x": {"y": 10}}) == 10
    assert VirtualObject().f(10).value(type("",(),{"f": lambda self,x: x*x})()) == 100

    class Dummy(object):
        def __init__(self):
            self.q = []

        def unit(self, v):
            self.q.append(("unit",v))
            return "unit"

        def put(self, unit, v):
            self.q.append(("put","unit",v))
            return self.q

        def vobject(self, v):
            return VirtualObject(BoundAccess(self))._const(v,"*init*")

    ctx = Dummy()
    assert ctx.vobject(ctx.unit(12)).put(20).value() == [('unit', 12), ('put', 'unit', 20)]

def test_stop_context():
    from block.chain import StopContext, Nothing
    from block.chain import StopWithErrorMessageContext

    class A:
        class x:
            class y:
                z = 10

    class Wrapper(object):
        def __init__(self, v):
            self.v = v
        def wrap(self, x):
            return [x, self.v, x]

    assert cc.chain.do(cc.x.y.z)(StopContext(),  A) == 10
    assert cc.chain.do(cc["x"]["y"]["z"])(StopContext(),  {"x": {"y": {"z": 10}}}) == 10
    assert cc.chain.do(cc.x.x.y.z)(StopContext(),  A) == Nothing
    assert cc.chain.do(cc["x"]["y"]).do(cc(string_append,  "!"))(StopContext(),  {"x": {"y": "foo"}}) == "foo!"
    assert cc.chain.do(cc.wrap("a"))(StopWithErrorMessageContext(), Wrapper("value")) == ["a", "value", "a"]
    assert repr(cc.chain.do(cc.x.x.y.z)(StopWithErrorMessageContext(),  A)) == u"""'Failure':AttributeError("class x has no attribute 'x'",)"""

def test_state_context():
    from block.chain import StateContext
    from block.chain import inc, put

    ctx = StateContext()
    assert cc.chain(ctx, ctx.unit(10))(0) == (0, 10)
    assert cc.chain.do(inc).do(inc)(ctx, ctx.unit(10))(0) == (2, 10)
    assert cc.chain.do(inc).do(inc).do(put(100)).do(inc).do(inc)(ctx, ctx.unit(10))(0) == (102, 10)
    assert cc.chain.do(inc).map(lambda x : x + 10)(ctx, ctx.unit(10))(0) == (1, 20)


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

def test_multiple_context():
    from block.chain import MultipleCandidatesContext

    M = MultipleCandidatesContext()
    assert cc.chain(M, M.unit(10)) == [10]
    def tri(ctx, x):
        return [x, x+1, x]

    assert cc.chain.do(tri).do(tri)(M, M.unit(10)) == [10, 11, 10, 11, 12, 11, 10, 11, 10]
    assert cc.chain.do(tri).do(cc(lambda x: x*2))(M, M.unit(10)) == [20,22,20]
    assert cc.chain.do(tri).do(cc.__add__(10))(M, M.unit(10)) == [20,21,20]


def test_map():
    from block.chain import (
        MultipleCandidatesContext,
        StopWithErrorMessageContext,
        StopContext,
        StateContext,
        Nothing,
        Failure
        )
    assert cc.chain.map(lambda x : x+1)(StopContext(),Nothing) == Nothing
    assert cc.chain.map(lambda x : x+1)(StopContext(), 10) == 11
    assert cc.chain.map(lambda x,y : x+y ,12)(StopContext(), 10) == 22
    assert cc.chain.map(lambda x,y : x+y ,Nothing)(StopContext(), 10) == Nothing
    assert cc.chain.map(lambda x,y,z : [x,y,z] ,12, 13)(StopContext(), 11) == [11,12,13]
    assert cc.chain.map(lambda x,y,z : [x,y,z] ,Nothing, 12)(StopContext(), 11) == Nothing

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

