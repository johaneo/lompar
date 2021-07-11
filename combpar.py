#!/usr/bin/python

import functools
import re

""" 
Parser combinators.
"""

prefix = ""
debuglevel = 0

best = []
maxbest = 20

def noteresult(parser, res, toks):
    global best
    best.append( (toks.pos, toks.toks[toks.pos:] , parser, res) )
    best.sort(reverse=True)
    best = best[:maxbest]

def debug(func):
    """Print the function signature and return value"""
    @functools.wraps(func)
    def wrapper_debug(*args, **kwargs):
        global prefix
        try:
            prefix = prefix + "  "
            args_repr = [repr(a) for a in args]
            args_0 = args_repr[0] if len(args_repr) > 0 else ""
            kwargs_repr = ["{%s}={%s}" % (k, v) for k, v in kwargs.items()] 
            signature = ", ".join(args_repr + kwargs_repr)           
            dbgout("%sCalling %s(%s)" %(prefix, func.__name__, signature), 1)
            value = func(*args, **kwargs)
            dbgout("%s%s %s returned %s" %(prefix, func.__name__, args_0, value), 1)
            for res, toks in value:
                noteresult(args_0, res, toks)
            return value
        finally:
            prefix = prefix[:-2]
    return wrapper_debug


def dbg(v, doc="XXX", lvl=2):
    dbgout("%s:%s" %(doc, v), lvl)
    return v

def dbgout(msg, level):
    if debuglevel >= level:
        print msg

class tokenpos:
    def __init__(self, toks, pos):
        self.toks = toks 
        self.pos = pos
    def __repr__(self):
        mp = min(len(self.toks), self.pos + 3)
        return "<%d/%d toks: %s>" %  \
            (self.pos, len(self.toks), self.toks[self.pos:mp])
        
    @classmethod
    def of_string(cls, str):
        toks = [x for x in re.split("([=()[\], ])", str) if x and not x.isspace()]
        return cls(toks, 0)
        
    def eof(self):
        return self.pos >= len(self.toks)
    def get(self):
        t = self.toks[self.pos]
        return t, tokenpos(self.toks, self.pos + 1)

def asserttokens(t):
    assert isinstance(t, tokenpos), ("wanted tokenpos, got %s ::  %s"%(type(t), t))

dbgtypval = True

# the type of parsed values: a pair of parser name and input value class typval:
class typval:
    def __init__(self, typ, val):
        self.val = val
        self.typ = typ
    
    @classmethod
    def mk(cls, typ, val):
        assert isinstance(typ, str), ("%s :: %s" %(typ, type(typ)))
        assertvalue(val)
        return cls(typ,val)
    def __repr__(self):
        if dbgtypval and self.typ:
            return "%s::%s" % (`self.typ`.upper(), self.val)
        return `self.val`
    def comb(self, combine, then):
        return typval((self.typ, combine, then.typ), (self, then))
    def map(self, fn, fnname="??"):
        dbgout("mapping %s %s to this: %s" %(fn, fnname, self.val), 2)
        return typval(self.typ, fn(self.val))

    def reduce(self, fn):
        v = self.val
        if (isinstance(v, list) or isinstance(v, tuple)):
            assert len(v) == 2, ("require length 2. was %d: %s" % (len(v), v))
            return fn(v[0].reducevals(fn), v[1].reducevals(fn))
        return v

def assertvalue(v):
    # can be anything but typval or iterable thereof
    assert not isinstance(v, typval), "cannot be typval" + `v`
    if isinstance(v, list) or isinstance(v, tuple):
        for vv in v:
            assertvalue(vv)

def asserttypval(v):
    assert isinstance(v, typval), "must be typval" + `v`

class parser:
    def __init__(self, fn, nm = None):
        self.fn = fn
        self.nm = nm
    def __repr__(self):
        return "<parser %s>" % (self.nm,)
    @debug
    def parse(self, tokens):
        asserttokens(tokens)
        vts = self.fn(tokens)
        return checkparseresult(vts)
    def topparse(self, str):
        toks = tokenpos.of_string(str)
        asserttokens(toks)
        vts = self.parse(toks)
        res = [v.val for v, t in vts if t.eof()]
        print "found %d valid results among %d partial parses" %(len(res), len(vts))
        return res

    def andthen(self, p2):
        assertparser(p2)
        def andthenfn(toks):
            asserttokens(toks)
            vts = []
            for (v1, toks1) in self.parse(toks):
                asserttokens(toks1)
                vts += [ (v1.comb("&", v2), toks2) for (v2, toks2) in p2.parse(toks1)]
            return vts
        return parser(andthenfn, "(%s & %s)" % (self, p2))
    def __and__(self, p2):
        return self.andthen(p2)
    # don't try p2 unless no results from p1
    def orelse(self, p2):
        assertparser(p2)
        def orelsefn(tokens):
            vts1 = self.parse(tokens)
            if vts1:
                return vts1
            return p2.parse(tokens)
        return parser(orelsefn, "(%s | %s)" % (self, p2))
    def __or__(self, p2):
        return self.orelse(p2)
    # combine results
    def both(self, p2):
        assertparser(p2)
        def bothfn(tokens):
            vts1 = self.parse(tokens)
            vts2 = p2.parse(tokens)
            return vts1 + vts2
        return parser(bothfn, "(%s + %s)" % (self, p2))
    def __add__(self, p2):
        return self.both(p2)
    def map(self, fn, fnname="??"):
        assert callable(fn)
        def mapfn(tokens):
            return [ (v.map(fn, fnname), t) for (v, t) in self.parse(tokens)]
        return parser(mapfn, "map(%s)" %(fnname))
    def __rshift__(self, fn):
        return self.map(fn)

    def named(self, nm):
        def nmfn(tokens):
            out = []
            for (v, t) in self.parse(tokens):
                newv = typval(nm, v.val)
                if v.typ == "array" or nm == "array":
                    print "XXX renaming %s -> %s for value %s" %(v.typ, nm, newv)
                out.append( (newv, t) )
            return out
        # def nmfn(tokens): return [ (typval(nm, v.val), t) for (v, t) in self.parse(tokens)]
        return parser(nmfn, nm)
    def __lshift__(self, nm):
        return self.named(nm)

def assertparser(p):
    assert isinstance(p, parser), p

def checkparseresult(vts):
    assert isinstance(vts, list), vts
    for v, toks in vts:
        assert isinstance(v, typval), "%s should be value. was %s" %(v, type(v))
        asserttokens(toks)
    return vts

def refP(pfn, *args):
    assert callable(pfn)
    def reffn(tokens):
        rts = pfn(*args).parse(tokens)
        return checkparseresult(rts)
    return parser(reffn, "ref")

# greedy will not backtrack or return partial parses.
def greedyP(p, minlen = 0, desc=None):
    assertparser(p)
    nm = desc or (p.nm+"*")
    def greedyfn(tokens):
        rts = [([], tokens)]
        iter = 0
        while True:
            rtsnext = []
            for (rs, toks1) in rts:
                for (r, toks2) in p.parse(toks1):
                    rtsnext.append( (rs + [r.val], toks2) )
            if not rtsnext:
                break
            rts = rtsnext
            iter += 1
            pass
        if iter < minlen: 
            return []
        return [(typval(nm, rs), toks) for (rs, toks) in rts]
    return parser(greedyfn, nm) 

# many will return parses of length 1, 2, 3 .. n, but fail if not minlen 
def manyP(p, end = [], minlen = 0, desc = None):
    assertparser(p)
    def mfn(tup):
        if not tup:
            return tup
        x, xs = tup
        return [dbg(x.val, "x.val")]+dbg(xs.val, "xs.val")
    def loopP(n):
        if n > 0:
            return (p & refP(loopP, n-1)) >> mfn
        return ((p & refP(loopP, n)) + constP(end)) >> mfn
    return loopP(minlen) << ("many(%s)"%(p.nm,))

def failP():
    def failfn(tokens):
        return []
    return parser(failfn, "fail")

def constP(r):
    def constfn(tokens):
        return [(typval.mk("const:"+`r`, r), tokens)]
    return parser(constfn, "const")

def predP(fn, desc = "pred"):
    def predfn(tokens):
        if tokens.eof():
            return []
        tk, tks = tokens.get()
        r = fn(tk)
        if r:
            return [(typval.mk(desc, r), tks)]
        return []
    return parser(predfn, desc)

def litP(lit):
    return predP(lambda x : (x == lit) and lit, "lit("+lit+")")

def rexP(rex, desc=None):
    return predP(lambda x: re.match("^"+rex+"$", x) and x, "rex("+(desc or rex)+")")

def sepListP(p, sep, minlen = 0, desc=None):
    assertparser(p)
    assertparser(sep)
    def resfn(rs):
        pr, mr = rs
        return [pr]+[x for _, x in mr.val]
    return ((p & manyP(sep & p, desc=desc or ("<%s&%s>*"% (sep.nm, p.nm)))) >> resfn) | constP([])
