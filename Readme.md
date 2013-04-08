# block.chain

## what is this?

python library about computation with a parametric context.

## how to use?

### Maybe like

Maybe is a computation that might have failed. if computation is failed then return Nothing.
```
from block.chain import MaybeF, chain, Nothing

def inc(ctx, x):
    return x + 1

def stop(ctx, _):
    return ctx.failure(_)

## `do' is like a `>>=' function such as [a -> m b], but this is [ctx -> a -> m b]

chain.chain.do(inc).value(MaybeF(), 10) # => 11
chain.chain.do(inc).do(inc).value(MaybeF(), Nothing) # => Nothing
chain.chain.do(inc).do(stop).do(inc).value(MaybeF(), 10) # => Nothing


## `map' is like a `fmap' function such as [(a -> b) -> (m a -> m b)] but this is [(a -*> a) -> (m a -*> m b)]

chain.chain.do(inc).map(lambda x : x*10).value(MaybeF(), 10) # => 110
chain.chain.do(inc).map(lambda x,y: [x,y], 20).value(MaybeF(), 10) # => [11, 20] 
chain.chain.do(inc).map(lambda x,y: [x,y], Nothing).value(MaybeF(), 10) # => Nothing
chain.chain.do(inc).map(lambda x,y: [x,y], 20).value(MaybeF(), Nothing) # => Nothing
```

### Error like

Error is like a Maybe, but this feature has also error reasons.
```
from block.chain import ErrorF, chain, Failure

def inc(ctx, x):
    return x + 1

## falsy value is Failure(<messages>)

Failure("fooo").append(Failure("-bar")).value # => "fooo-bar"

## like a maybe
chain.chain.do(inc).map(lambda x : x*10).value(ErrorF(), 10) # => 110
chain.chain.do(inc).map(lambda x,y: [x,y], Failure("this-is-invalid")).value(ErrorF(), 10) # => Failure("<this is invalid>")
chain.chain.map(lambda x,y: [x,y], Any(Failure("this-is-invalid"), 20)).value(ErrorF(), 10) # => [10,20]
chain.chain.map(lambda x,y,z: [x,y,z], Failure("y"), Failure(" z")).value(ErrorF(), 10) # => Failure("y z")
chain.chain.map(lambda x,y,z: [x,y,z], Failure("y"), Failure(" z")).value(ErrorF(), Failure("x")) # => Failure("x")
```

### List like

List is amb computation.
```
from block.chain import ListF, chain, Any

def tri(ctx, x):
    return [x, x+1, x]

ctx = ListF()
chain.chain.do(tri).do(tri)(ctx, ctx.unit(10)) # => [10, 11, 10, 11, 12, 11, 10, 11, 10]
chain.chain.map(lambda x,y : x+y, [7,8,9])(ctx, [10,20,30]) # => [17, 18, 19, 27, 28, 29, 37, 38, 39]
chain.chain.map(lambda x,y,z : [x,y,z], [7,8,9], ["a", "b"])(ctx, [10,20,30]) # => [[10, 7, 'a'], [10, 7, 'b'], [10, 8, 'a'], [10, 8, 'b'], [10, 9, 'a'], [10, 9, 'b'], [20, 7, 'a'], [20, 7, 'b'], [20, 8, 'a'], [20, 8, 'b'], [20, 9, 'a'], [20, 9, 'b'], [30, 7, 'a'], [30, 7, 'b'], [30, 8, 'a'], [30, 8, 'b'], [30, 9, 'a'], [30, 9, 'b']]
```

### State like

State is a stateful computation (but, i don't know python needs this..)

```
from block.chain import StateF, chain

def inc(ctx, v):
    return lambda s: (s+1,v)

def put(n):
    def wrapped(ctx, v):
        return lambda s: (n, v)
    return wrapped

ctx = StateF()
chain.chain(ctx, ctx.unit(10))(0) # => (0, 10)
chain.chain.do(inc).do(inc)(ctx, ctx.unit(10))(0) # => (2, 10)
chain.chain.do(inc).do(inc).do(put(100)).do(inc).do(inc)(ctx, ctx.unit(10))(0) # => (102, 10)
chain.chain.do(inc).map(lambda x : x + 10)(ctx, ctx.unit(10))(0) # => (1, 20)
```

