#!/usr/bin/python

from combpar import *

def number(): return predP(lambda x : x.isdigit() and x, desc="num")
def null(): return litP("null")
def name(): return predP(lambda x : x.isalnum() and x, desc="name")
def fqn(): return rexP("([a-zA-Z][a-zA-Z0-9_]*)([.][a-zA-Z][a-zA-Z0-9_]*)*", desc="fqn")
def word(): return rexP("[^=[]*")
#def word(): return name() # more restrictive -> faster, but fewer input accepted
def unquotedstring(): return manyP(refP(word), desc="manyWord") \
    >> (lambda x : "_".join(x))
def array():  return (litP("[") & sepListP(refP(value), litP(","), desc="arraySepList") & litP("]")) >> (lambda x: x[0].val[1]) << "array" 
def kv(): return (refP(name) & litP("=") & refP(value)) << "kv" >> (lambda x : (dbg(x[0].val[0], doc="kv0", lvl=0), dbg(x[1], doc="kv1", lvl=0)))
def kvs(): return (sepListP(refP(kv), litP(","), "kvSepList")) << "kvs" # >> (lambda x : dbg(x, doc="kvs", lvl=0))
def value(): return (refP(null) | refP(number) | refP(array) | refP(obj) | refP(unquotedstring)) >> (lambda x : dbg(x, doc="value", lvl=0))
def obj(): return (refP(fqn) & litP("(") & refP(kvs) & litP(")")) << "obj" >> (lambda x : (x[0].val[0].val[0], x[0].val[1]))

# Lombok's toString is not intended to be parsable, but sometimes... you gotta.

test_1 = """SomeDTO(orderId=1)"""
test_nest = """SomeDTO(orderId=1, b=OtherDTO(c=d))"""
test_long = """SomeDTO(orderId=1, b=very long string, c=hello)"""
test_hard = """SomeDTO(orderId=1, b=very, (long) string, c=hello)"""
test_easy = """SomeDTO(orderId=1, logonId=test@test.com, currency=USD, items=[SomeDTO.SomeItem(orderItemId=1001, quantity=1, somebool=true, enumReason=NO), SomeDTO.SomeItem(orderItemId=1002, quantity=100.03, somebool=false, enumReason=OTHER)], extras=[], name=Heartgard, description=null)"""

test_harder = """SomeDTO(orderId=1, logonId=test@test.com, currency=USD, items=[SomeDTO.SomeItem(orderItemId=1001, quantity=1, somebool=true, enumReason=NO)], extras=[], name=Heartgard Plus Soft Chew for Dogs, up to 25 lbs, (Blue Box), 6 Soft Chews (6-mos. supply), description=null)"""

## ---------------------------

if __name__ == "__main__":
    import sys
    print sys.argv
