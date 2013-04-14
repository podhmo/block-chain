def string_append(prefix, x):
    return prefix + x

from block.chain import chain

def test_failure():
    from block.chain.monoid.immutable import Failure
    assert Failure("fooo").value == "fooo"
    assert Failure("fooo").append(Failure("-bar")).value == "fooo-bar"
    
    from block.chain.monoid.mutable import Failure as MFailure
    f = MFailure("fooo")
    f.append(Failure("-bar"))
    assert f.values == ["fooo", "-bar"]

    f = Failure("fooo")
    f.append(Failure("-bar"))
    assert f.values == ["fooo"]

def test_listmonoid():
    from block.chain.monoid.immutable import ListMonoid
    assert ListMonoid([1,2,3]).value == [1,2,3]
    assert ListMonoid([1,2,3]).append(ListMonoid([4,5,6])).value == [1,2,3,4,5,6]

    from block.chain.monoid.mutable import ListMonoid as MListMonoid
    m = MListMonoid([1,2,3])
    m.append(ListMonoid([4]))
    assert m.value == [1,2,3,4]

    m = ListMonoid([1,2,3])
    m.append(ListMonoid([4]))
    assert m.value == [1,2,3]

def test_stringmonoid():
    from block.chain.monoid.immutable import StringMonoid
    assert StringMonoid("foo").value == "foo"
    assert StringMonoid("foo").append(StringMonoid("bar")).value == "foobar"

    from block.chain.monoid.mutable import StringMonoid as MStringMonoid
    m = MStringMonoid("foo")
    m.append(StringMonoid("bar"))
    assert m.value == "foobar"

    m = StringMonoid("foo")
    m.append(StringMonoid("bar"))
    assert m.value == "foo"
    
def test_summonoid():
    from block.chain.monoid.immutable import SumMonoid
    assert SumMonoid(3).value == 3
    assert SumMonoid(3).append(SumMonoid(4)).value == 7

    from block.chain.monoid.mutable import SumMonoid as MSumMonoid
    m = MSumMonoid(3)
    m.append(SumMonoid(4))
    assert m.value == 7

    m = SumMonoid(3)
    m.append(SumMonoid(4))
    assert m.value == 3

def test_choice_from():
    from block.chain import MaybeF, Nothing
    assert reduce(MaybeF().choice_from, [Nothing, Nothing, Nothing]) == Nothing
    assert reduce(MaybeF().choice_from, [Nothing, 10, Nothing]) == 10

    from block.chain import ErrorF, Failure
    assert reduce(ErrorF().choice_from, [Failure("x"), Failure("y"), Failure("z")]).value == "xyz"
    assert reduce(ErrorF().choice_from, [Failure("x"), 10, Failure("z")]) == 10
    assert reduce(ErrorF().choice_from, [Failure("x"), 10, Failure("z"), 20]) == 10


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
    from block.chain import MaybeF, Nothing
    from block.chain import ErrorF

    class A:
        class x:
            class y:
                z = 10

    class Wrapper(object):
        def __init__(self, v):
            self.v = v
        def wrap(self, x):
            return [x, self.v, x]
        
    assert chain.chain.do(chain.x.y.z).value(MaybeF(),  A) == 10
    assert chain.chain.do(chain["x"]["y"]["z"]).value(MaybeF(),  {"x": {"y": {"z": 10}}}) == 10
    assert chain.chain.do(chain.x.x.y.z).value(MaybeF(),  A) == Nothing
    assert chain.chain.do(chain["x"]["y"]).do(chain(string_append,  "!")).value(MaybeF(),  {"x": {"y": "foo"}}) == "foo!"
    assert chain.chain.do(chain.wrap("a")).value(ErrorF(), Wrapper("value")) == ["a", "value", "a"]
    assert repr(chain.chain.do(chain.x.x.y.z).value(ErrorF(),  A)) == u"""'Failure':[AttributeError("class x has no attribute 'x'",)]"""

def test_state_context():
    from block.chain import StateF
    from block.chain import inc, put

    ctx = StateF()
    assert chain.chain.value(ctx, ctx.unit(10))(0) == (0, 10)
    assert chain.chain.do(inc).do(inc).value(ctx, ctx.unit(10))(0) == (2, 10)
    assert chain.chain.do(inc).do(inc).do(put(100)).do(inc).do(inc).value(ctx, ctx.unit(10))(0) == (102, 10)
    assert chain.chain.do(inc).map(lambda x : x + 10).value(ctx, ctx.unit(10))(0) == (1, 20)


    def twice(ctx, _):
        return lambda s: (s, s*s)
    assert chain.chain.do(chain["x"]).value(ctx, ctx.unit({"x": 100}))(10) == (10, 100)
    assert chain.chain.do(inc).do(chain["x"]).value(ctx, ctx.unit({"x": 100}))(10) == (11, 100)
    assert chain.chain.do(chain["x"]).do(inc).value(ctx, ctx.unit({"x": 100}))(10) == (11, 100)
    assert chain.chain.do(put(10)).do(inc).do(twice).do(twice).do(inc).do(twice).value(ctx, ctx.unit(-1))(0) == (12, 144)
    assert chain.chain.do(chain(lambda x: x+1)).value(ctx, ctx.unit(10))(0) == (0, 11)
    class X:
        def sq(self, x):
            return x * x
    assert  chain.chain.do(chain.sq(10)).value(ctx, ctx.unit(X()))(10) == (10, 100)

def test_multiple_context():
    from block.chain import ListF

    M = ListF()
    assert chain.chain.value(M, M.unit(10)) == [10]
    def tri(ctx, x):
        return [x, x+1, x]

    assert chain.chain.do(tri).do(tri).value(M, M.unit(10)) == [10, 11, 10, 11, 12, 11, 10, 11, 10]
    assert chain.chain.do(tri).do(chain(lambda x: x*2)).value(M, M.unit(10)) == [20,22,20]
    assert chain.chain.do(tri).do(chain.__add__(10)).value(M, M.unit(10)) == [20,21,20]

def test_writer_context():
    from block.chain import WriterF
    from block.chain.monoid.mutable import ListMonoid, StringMonoid
    
    M = WriterF(ListMonoid)
    def inc(ctx, v):
        return ctx.unit(v+1)

    assert chain.chain.value(M, M.unit("heh")) == (ListMonoid(), "heh")
    assert chain.chain.do(inc).do(inc).value(M, M.unit(10)) == (ListMonoid(), 12)
    assert chain.chain.map(lambda x : x*x).value(M, M.unit(10)) == (ListMonoid(), 100)
    assert chain.chain.do(M.tell(["hey."])).do(inc).do(M.tell(["this is message"])).value(M, M.unit(10)) == (ListMonoid(value=["hey.", "this is message"]), 11)

    M2 = WriterF(StringMonoid)
    assert chain.chain.do(M.tell("hey ")).direct(M.listen).do(lambda ctx, (m, x): ctx.unit(m.value+x)).value(M2, M2.unit("foo")) == (StringMonoid("hey "), "hey foo")

    def double(m, v):
        return m.append(m)
    assert chain.chain.do(M.tell("hey")).direct(M2.passing(double)).do(M.tell(" yah!")).value(M2, M2.unit(10)) == (StringMonoid("heyhey yah!"), 10)

def test_map():
    from block.chain import (
        ListF,
        ErrorF,
        MaybeF,
        StateF,
        Nothing,
        Failure
        )
    assert chain.chain.map(lambda x : x+1).value(MaybeF(),Nothing) == Nothing
    assert chain.chain.map(lambda x : x+1).value(MaybeF(), 10) == 11
    assert chain.chain.map(lambda x,y : x+y ,12).value(MaybeF(), 10) == 22
    assert chain.chain.map(lambda x,y : x+y ,Nothing).value(MaybeF(), 10) == Nothing
    assert chain.chain.map(lambda x,y,z : [x,y,z] ,12, 13).value(MaybeF(), 11) == [11,12,13]
    assert chain.chain.map(lambda x,y,z : [x,y,z] ,Nothing, 12).value(MaybeF(), 11) == Nothing

    assert repr(chain.chain.map(lambda x : x+1).value(ErrorF(), Failure(10))) == "'Failure':[10]"
    assert chain.chain.map(lambda x : x+1).value(ErrorF(), 10) == 11
    assert chain.chain.map(lambda x,y : x+y ,12).value(ErrorF(), 10) == 22
    assert repr(chain.chain.map(lambda x,y : x+y ,Failure(11)).value(ErrorF(), 10)) == "'Failure':[11]"
    assert chain.chain.map(lambda x,y,z : [x,y,z] ,12, 13).value(ErrorF(), 11) == [11,12,13]
    assert repr(chain.chain.map(lambda x,y,z : [x,y,z] ,Failure(11), 12).value(ErrorF(), 11)) ==  "'Failure':[11]"
    ctx = StateF()
    assert chain.chain.map(lambda x : x+1).value(ctx, ctx.unit(10))(0) == (0,11)
    assert chain.chain.map(lambda x,y : x+y ,ctx.unit(12)).value(ctx, ctx.unit(10))(0) == (0, 22)
    assert chain.chain.map(lambda x,y : x+y, ctx.put(ctx.unit(12), 20)).value(ctx, ctx.unit(10))(0) == (20, 22)
    assert chain.chain.map(lambda x,y : x+y, ctx.chain(ctx.unit(12)).put(20).value()).value(ctx, ctx.unit(10))(0) == (20, 22)
    assert chain.chain.map(lambda x,y,z : [x,y,z], ctx.unit(12), ctx.chain(ctx.unit(13)).put(20).value()).value(ctx, ctx.unit(11))(0) == (20,  [11, 12, 13])

    ctx = ListF()
    assert chain.chain.map(lambda x : x+1).value(ctx, [10,20,30]) == [11,21,31]
    assert chain.chain.map(lambda x,y : x+y, [7,8,9]).value(ctx, [10,20,30]) == [17, 18, 19, 27, 28, 29, 37, 38, 39]
    assert chain.chain.map(lambda x,y,z : [x,y,z], [7,8,9], ["a", "b"]).value(ctx, [10,20,30]) == [[10, 7, 'a'], [10, 7, 'b'], [10, 8, 'a'], [10, 8, 'b'], [10, 9, 'a'], [10, 9, 'b'], [20, 7, 'a'], [20, 7, 'b'], [20, 8, 'a'], [20, 8, 'b'], [20, 9, 'a'], [20, 9, 'b'], [30, 7, 'a'], [30, 7, 'b'], [30, 8, 'a'], [30, 8, 'b'], [30, 9, 'a'], [30, 9, 'b']]


def test_any():
    from block.chain import (
        MaybeF,
        Nothing,
        Any,

        ErrorF,
        Failure
        )
    assert chain.chain.map(lambda x : x+1).value(MaybeF(),Nothing) == Nothing
    assert chain.chain.map(lambda x, y: x+y, Any(Nothing, 20)).value(MaybeF(), 10) == 30
    assert chain.chain.map(lambda x, y: x+y, Any(Nothing, 20)).value(MaybeF(), Any(Nothing, 10)) == 30
    assert chain.chain.map(lambda x, y: x+y, Any(Nothing, 20)).value(MaybeF(), Any(20, Nothing, 10)) == 40

    assert Any(Failure("foo"), Failure("bar")).choice(ErrorF()).value == "foobar"
    assert Any(Failure("foo"), 20).choice(ErrorF()) == 20
    assert chain.chain.map(lambda x, y: x+y, Failure("y not found.")).value(ErrorF(), Failure("x not found.")).value == "x not found.y not found."
    assert chain.chain.map(lambda _, x, y: x+y, Failure("x not found."), Failure("y not found.")).value(ErrorF(), 10).value == "x not found.y not found."
