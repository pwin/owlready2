# Mon atelier "base de données en ligne"
# Copyright (C) 2017-2018 Jean-Baptiste LAMY
#
# This is a striped-down and dependence-less version of RPLY, from Alex Gaynor

# Copyright (c) Alex Gaynor and individual contributors.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
# 
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
# 
#     3. Neither the name of rply nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.




class ParserGeneratorError(Exception): pass


class LexingError(Exception):
  def __init__(self, message, source_pos):
    self.message = message
    self.source_pos = source_pos


class ParsingError(Exception):
  def __init__(self, message, source_pos):
    self.message = message
    self.source_pos = source_pos


class IdentityDict(object):
  def __init__(self):
    self._contents = {}
    self._keepalive = []
    
  def get(self, key, default = None):
    r = self._contents.get(id(key))
    if not r is None: return r[1]
    return default
    
  def __getitem__(self, key): return self._contents[id(key)][1]
  
  def __setitem__(self, key, value):
    idx = len(self._keepalive)
    self._keepalive.append(key)
    self._contents[id(key)] = key, value, idx
    
  def __delitem__(self, key):
    del self._contents[id(key)]
    for idx, obj in enumerate(self._keepalive):
      if obj is key:
        del self._keepalive[idx]
        break
      
  def __len__(self): return len(self._contents)

  def __iter__(self):
    for key, _, _ in self._contents.values(): yield key



class Counter(object):
  def __init__(self): self.value = 0
  def incr(self): self.value += 1


class Token(object):
  alias = None
  def __init__(self, name, value, source_pos = None):
    self.name = name
    self.value = value
    self.source_pos = source_pos
    
  def __repr__(self):
    if self.name == self.value: return self.name
    return "%s:%s" % (self.name, repr(self.value))
    
  def __eq__(self, other):
    if not isinstance(other, Token): return NotImplemented
    return (self.alias == other.alias) and (self.name == other.name) and (self.value == other.value)
  
  def __hash__(self):
    return hash((self.alias, self.name, self.value))
  
  
def rightmost_terminal(symbols, terminals):
  for sym in reversed(symbols):
    if sym in terminals: return sym
  return None


class Grammar(object):
  def __init__(self, terminals):
    # A list of all the productions
    self.productions = [None]
    # A dictionary mapping the names of non-terminals to a list of all
    # productions of that nonterminal
    self.prod_names = {}
    # A dictionary mapping the names of terminals to a list of the rules
    # where they are used
    self.terminals = dict((t, []) for t in terminals)
    self.terminals["error"] = []
    # A dictionary mapping names of nonterminals to a list of rule numbers
    # where they are used
    self.nonterminals = {}
    self.first = {}
    self.follow = {}
    self.precedence = {}
    self.start = None

  def add_production(self, prod_name, syms, func, precedence):
    if prod_name in self.terminals: raise ParserGeneratorError("Illegal rule name %r" % prod_name)

    if precedence is None:
      precname = rightmost_terminal(syms, self.terminals)
      prod_prec = self.precedence.get(precname, ("right", 0))
    else:
      try:
        prod_prec = self.precedence[precedence]
      except KeyError:
        raise ParserGeneratorError("Precedence %r doesn't exist" % precedence)

    pnumber = len(self.productions)
    self.nonterminals.setdefault(prod_name, [])

    for t in syms:
      if t in self.terminals: self.terminals[t].append(pnumber)
      else:                   self.nonterminals.setdefault(t, []).append(pnumber)

    p = Production(pnumber, prod_name, syms, prod_prec, func)
    self.productions.append(p)

    self.prod_names.setdefault(prod_name, []).append(p)

  def set_precedence(self, term, assoc, level):
    if term in self.precedence:
      raise ParserGeneratorError("Precedence already specified for %s" % term)
    if assoc not in ["left", "right", "nonassoc"]:
      raise ParserGeneratorError("Precedence must be one of left, right, nonassoc; not %s" % (assoc))
    self.precedence[term] = (assoc, level)

  def set_start(self):
    start = self.productions[1].name
    self.productions[0] = Production(0, "S'", [start], ("right", 0), None)
    self.nonterminals[start].append(0)
    self.start = start

  def unused_terminals(self):
    return [
      t
      for t, prods in self.terminals.items()
      if not prods and t != "error"
    ]

  def unused_productions(self):
    return [p for p, prods in self.nonterminals.items() if not prods]

  def build_lritems(self):
    for p in self.productions:
      lastlri = p
      i = 0
      lr_items = []
      while True:
        if i > p.getlength():
          lri = None
        else:
          try:
            before = p.prod[i - 1]
          except IndexError:
            before = None
          try:
            after = self.prod_names[p.prod[i]]
          except (IndexError, KeyError):
            after = []
          lri = LRItem(p, i, before, after)
        lastlri.lr_next = lri
        if lri is None:
          break
        lr_items.append(lri)
        lastlri = lri
        i += 1
      p.lr_items = lr_items

  def _first(self, beta):
    result = []
    for x in beta:
      x_produces_empty = False
      for f in self.first[x]:
        if f == "<empty>":
          x_produces_empty = True
        else:
          if f not in result:
            result.append(f)
      if not x_produces_empty:
        break
    else:
      result.append("<empty>")
    return result

  def compute_first(self):
    for t in self.terminals:
      self.first[t] = [t]

    self.first["$end"] = ["$end"]

    for n in self.nonterminals:
      self.first[n] = []

    changed = True
    while changed:
      changed = False
      for n in self.nonterminals:
        for p in self.prod_names[n]:
          for f in self._first(p.prod):
            if f not in self.first[n]:
              self.first[n].append(f)
              changed = True

  def compute_follow(self):
    for k in self.nonterminals:
      self.follow[k] = []

    start = self.start
    self.follow[start] = ["$end"]

    added = True
    while added:
      added = False
      for p in self.productions[1:]:
        for i, B in enumerate(p.prod):
          if B in self.nonterminals:
            fst = self._first(p.prod[i + 1:])
            has_empty = False
            for f in fst:
              if f != "<empty>" and f not in self.follow[B]:
                self.follow[B].append(f)
                added = True
              if f == "<empty>":
                has_empty = True
            if has_empty or i == (len(p.prod) - 1):
              for f in self.follow[p.name]:
                if f not in self.follow[B]:
                  self.follow[B].append(f)
                  added = True


class Production(object):
  def __init__(self, num, name, prod, precedence, func):
    self.name = name
    self.prod = prod
    self.number = num
    self.func = func
    self.prec = precedence

    self.unique_syms = []
    for s in self.prod:
      if s not in self.unique_syms:
        self.unique_syms.append(s)

    self.lr_items = []
    self.lr_next = None
    self.lr0_added = 0
    self.reduced = 0

  def __repr__(self):
    return "Production(%s -> %s)" % (self.name, " ".join(self.prod))

  def getlength(self):
    return len(self.prod)


class LRItem(object):
  def __init__(self, p, n, before, after):
    self.name = p.name
    self.prod = p.prod[:]
    self.prod.insert(n, ".")
    self.number = p.number
    self.lr_index = n
    self.lookaheads = {}
    self.unique_syms = p.unique_syms
    self.lr_before = before
    self.lr_after = after

  def __repr__(self):
    return "LRItem(%s -> %s)" % (self.name, " ".join(self.prod))

  def getlength(self):
    return len(self.prod)


class Lexer(object):
  def __init__(self, rules, ignore_rules):
    self.rules = rules
    self.ignore_rules = ignore_rules

  def lex(self, s):
    return LexerStream(self, s)


class LexerStream(object):
  def __init__(self, lexer, s):
    self.lexer = lexer
    self.s = s
    self.idx = 0
    
  def __iter__(self): return self
  
  def next(self):
    while True:
      if self.idx >= len(self.s): raise StopIteration
      for rule in self.lexer.ignore_rules:
        match = rule.matches(self.s, self.idx)
        if match:
          self.idx = match[1]
          break
      else:
        break
      
    for rule in self.lexer.rules:
      match = rule.matches(self.s, self.idx)
      if match:
        self.idx = match[1]
        source_pos = match[0]
        token = Token(rule.name, self.s[match[0]:match[1]], source_pos)
        return token
    else:
      raise LexingError(None, self.idx)

  __next__ = next


try: # Brython
  from browser import window, load
  load("rply_re.js")
  exec_regexp = window.exec_regexp
  
  class Rule(object):
    def __init__(self, name, pattern, flags = 0):
      self.name = name
      if not pattern.startswith("^"): pattern = "^" + pattern
      self.re = window.RegExp.new(pattern) #, flags)
      
    def matches(self, s, pos):
      m = exec_regexp(self.re, s[pos:])
      if m: return pos + m[0], pos + m[0] + m[1]
      return None
    
except:
  import re
  
  class Rule(object):
    def __init__(self, name, pattern, flags = 0):
      self.name = name
      self.re = re.compile(pattern, flags)
      
    def matches(self, s, pos):
      m = self.re.match(s[pos:])
      if m:
        start, end = m.span(0)
        return start + pos, end + pos


  
class LexerGenerator(object):
  def __init__(self):
    self.rules = []
    self.ignore_rules = []

  def add(self, name, pattern, flags = 0): self.rules.append(Rule(name, pattern, flags))

  def ignore(self, pattern, flags = 0): self.ignore_rules.append(Rule("", pattern, flags))
  
  def build(self): return Lexer(self.rules, self.ignore_rules)




class LRParser(object):
  def __init__(self, lr_table, error_handler):
    self.lr_table = lr_table
    self.error_handler = error_handler

  def parse(self, tokenizer, state=None):
    lookahead = None
    lookaheadstack = []

    statestack = [0]
    symstack = [Token("$end", "$end")]

    current_state = 0
    while True:
      if self.lr_table.default_reductions[current_state]:
        t = self.lr_table.default_reductions[current_state]
        current_state = self._reduce_production(
          t, symstack, statestack, state
        )
        continue
      
      if lookahead is None:
        if lookaheadstack:      lookahead = lookaheadstack.pop()
        else:
          try:                  lookahead = next(tokenizer)
          except StopIteration: lookahead = None
          
        if lookahead is None:
          lookahead = Token("$end", "$end")
          
      ltype = lookahead.name
      if ltype in self.lr_table.lr_action[current_state]:
        t = self.lr_table.lr_action[current_state][ltype]
        if t > 0:
          statestack.append(t)
          current_state = t
          symstack.append(lookahead)
          lookahead = None
          continue
        elif t < 0:
          current_state = self._reduce_production(
            t, symstack, statestack, state
          )
          continue
        else:
          n = symstack[-1]
          return n
      else:
        # TODO: actual error handling here
        if self.error_handler is not None:
          if state is None: self.error_handler(lookahead)
          else:             self.error_handler(state, lookahead)
          raise AssertionError("For now, error_handler must raise.")
        else:
          #print(self.lr_table.default_reductions)
          #print()
          #print(self.lr_table.lr_action)
          #print()
          #print(self.lr_table.lr_action[current_state])
          #print()
          #print(statestack, current_state)
          #print()
          #print(ltype)
          #print()
          #print("Error:", lookahead)
          raise ParsingError(None, lookahead.source_pos)
        
  def _reduce_production(self, t, symstack, statestack, state):
    # reduce a symbol on the stack and emit a production
    p = self.lr_table.grammar.productions[-t]
    pname = p.name
    plen = p.getlength()
    start = len(symstack) + (-plen - 1)
    assert start >= 0
    targ = symstack[start + 1:]
    start = len(symstack) + (-plen)
    assert start >= 0
    del symstack[start:]
    del statestack[start:]
    if state is None: value = p.func(targ)
    else:             value = p.func(state, targ)
    symstack.append(value)
    current_state = self.lr_table.lr_goto[statestack[-1]][pname]
    statestack.append(current_state)
    return current_state


LARGE_VALUE = 9223372036854775807


class ParserGenerator(object):
  def __init__(self, tokens, precedence=[], cache_id=None):
    self.tokens = tokens
    self.productions = []
    self.precedence = precedence
    self.cache_id = cache_id
    self.error_handler = None

  def production(self, rule, precedence=None):
    parts = rule.split()
    production_name = parts[0]
    if parts[1] != ":": raise ParserGeneratorError("Expecting :")
    syms = parts[2:]

    def inner(func):
      self.productions.append((production_name, syms, func, precedence))
      return func
    return inner

  def error(self, func):
    self.error_handler = func
    return func

  def data_is_valid(self, g, data):
    if g.start != data["start"]: return False
    if sorted(g.terminals) != data["terminals"]: return False
    if sorted(g.precedence) != sorted(data["precedence"]): return False
    for key, (assoc, level) in g.precedence.items():
      if data["precedence"][key] != [assoc, level]: return False
    if len(g.productions) != len(data["productions"]): return False
    for p, (name, prod, (assoc, level)) in zip(g.productions, data["productions"]):
      if p.name != name: return False
      if p.prod != prod: return False
      if p.prec != (assoc, level): return False
    return True

  def build(self):
    g = Grammar(self.tokens)

    for level, (assoc, terms) in enumerate(self.precedence, 1):
      for term in terms: g.set_precedence(term, assoc, level)

    for prod_name, syms, func, precedence in self.productions:
      g.add_production(prod_name, syms, func, precedence)

    g.set_start()

    for unused_term in g.unused_terminals():   print("Token %r is unused" % unused_term)
    for unused_prod in g.unused_productions(): print("Production %r is not reachable" % unused_prod)

    g.build_lritems()
    g.compute_first()
    g.compute_follow()

    table = LRTable.from_grammar(g)

    #if table.sr_conflicts: print("%d shift/reduce conflict%s" % (len(table.sr_conflicts), "s" if len(table.sr_conflicts) > 1 else ""))
    #if table.rr_conflicts: print("%d reduce/reduce conflict%s" % (len(table.rr_conflicts), "s" if len(table.rr_conflicts) > 1 else ""))
    return LRParser(table, self.error_handler)


def digraph(X, R, FP):
  N = dict.fromkeys(X, 0)
  stack = []
  F = {}
  for x in X:
    if N[x] == 0: traverse(x, N, stack, F, X, R, FP)
  return F


def traverse(x, N, stack, F, X, R, FP):
  stack.append(x)
  d = len(stack)
  N[x] = d
  F[x] = FP(x)

  rel = R(x)
  for y in rel:
    if N[y] == 0: traverse(y, N, stack, F, X, R, FP)
    N[x] = min(N[x], N[y])
    for a in F.get(y, []):
      if a not in F[x]: F[x].append(a)
  if N[x] == d:
    N[stack[-1]] = LARGE_VALUE
    F[stack[-1]] = F[x]
    element = stack.pop()
    while element != x:
      N[stack[-1]] = LARGE_VALUE
      F[stack[-1]] = F[x]
      element = stack.pop()


class LRTable(object):
  def __init__(self, grammar, lr_action, lr_goto, default_reductions, sr_conflicts, rr_conflicts):
    self.grammar = grammar
    self.lr_action = lr_action
    self.lr_goto = lr_goto
    self.default_reductions = default_reductions
    self.sr_conflicts = sr_conflicts
    self.rr_conflicts = rr_conflicts
    
  @classmethod
  def from_cache(cls, grammar, data):
    lr_action = [
      dict([(str(k), v) for k, v in action.items()])
      for action in data["lr_action"]
    ]
    lr_goto = [
      dict([(str(k), v) for k, v in goto.items()])
      for goto in data["lr_goto"]
    ]
    return LRTable(
      grammar,
      lr_action,
      lr_goto,
      data["default_reductions"],
      data["sr_conflicts"],
      data["rr_conflicts"]
    )

  @classmethod
  def from_grammar(cls, grammar):
    cidhash = IdentityDict()
    goto_cache = {}
    add_count = Counter()
    C = cls.lr0_items(grammar, add_count, cidhash, goto_cache)

    cls.add_lalr_lookaheads(grammar, C, add_count, cidhash, goto_cache)

    lr_action = [None] * len(C)
    lr_goto = [None] * len(C)
    sr_conflicts = []
    rr_conflicts = []
    for st, I in enumerate(C):
      st_action = {}
      st_actionp = {}
      st_goto = {}
      for p in I:
        if p.getlength() == p.lr_index + 1:
          if p.name == "S'":
            # Start symbol. Accept!
            st_action["$end"] = 0
            st_actionp["$end"] = p
          else:
            laheads = p.lookaheads[st]
            for a in laheads:
              if a in st_action:
                r = st_action[a]
                if r > 0:
                  sprec, slevel = grammar.productions[st_actionp[a].number].prec
                  rprec, rlevel = grammar.precedence.get(a, ("right", 0))
                  if (slevel < rlevel) or (slevel == rlevel and rprec == "left"):
                    st_action[a] = -p.number
                    st_actionp[a] = p
                    if not slevel and not rlevel:
                      sr_conflicts.append((st, repr(a), "reduce"))
                    grammar.productions[p.number].reduced += 1
                  elif not (slevel == rlevel and rprec == "nonassoc"):
                    if not rlevel:
                      sr_conflicts.append((st, repr(a), "shift"))
                elif r < 0:
                  oldp = grammar.productions[-r]
                  pp = grammar.productions[p.number]
                  if oldp.number > pp.number:
                    st_action[a] = -p.number
                    st_actionp[a] = p
                    chosenp, rejectp = pp, oldp
                    grammar.productions[p.number].reduced += 1
                    grammar.productions[oldp.number].reduced -= 1
                  else:
                    chosenp, rejectp = oldp, pp
                  rr_conflicts.append((st, repr(chosenp), repr(rejectp)))
                else:
                  raise ParserGeneratorError("Unknown conflict in state %d" % st)
              else:
                st_action[a] = -p.number
                st_actionp[a] = p
                grammar.productions[p.number].reduced += 1
        else:
          i = p.lr_index
          a = p.prod[i + 1]
          if a in grammar.terminals:
            g = cls.lr0_goto(I, a, add_count, goto_cache)
            j = cidhash.get(g, -1)
            if j >= 0:
              if a in st_action:
                r = st_action[a]
                if r > 0:
                  if r != j:
                    raise ParserGeneratorError("Shift/shift conflict in state %d" % st)
                elif r < 0:
                  rprec, rlevel = grammar.productions[st_actionp[a].number].prec
                  sprec, slevel = grammar.precedence.get(a, ("right", 0))
                  if (slevel > rlevel) or (slevel == rlevel and rprec == "right"):
                    grammar.productions[st_actionp[a].number].reduced -= 1
                    st_action[a] = j
                    st_actionp[a] = p
                    if not rlevel:
                      sr_conflicts.append((st, repr(a), "shift"))
                  elif not (slevel == rlevel and rprec == "nonassoc"):
                    if not slevel and not rlevel:
                      sr_conflicts.append((st, repr(a), "reduce"))
                else:
                  raise ParserGeneratorError("Unknown conflict in state %d" % st)
              else:
                st_action[a] = j
                st_actionp[a] = p
      nkeys = set()
      for ii in I:
        for s in ii.unique_syms:
          if s in grammar.nonterminals:
            nkeys.add(s)
      for n in nkeys:
        g = cls.lr0_goto(I, n, add_count, goto_cache)
        j = cidhash.get(g, -1)
        if j >= 0: st_goto[n] = j

      lr_action[st] = st_action
      lr_goto[st] = st_goto

    default_reductions = [0] * len(lr_action)
    for state, actions in enumerate(lr_action):
      actions = set(actions.values())
      if len(actions) == 1 and next(iter(actions)) < 0:
        default_reductions[state] = next(iter(actions))
    return LRTable(grammar, lr_action, lr_goto, default_reductions, sr_conflicts, rr_conflicts)

  @classmethod
  def lr0_items(cls, grammar, add_count, cidhash, goto_cache):
    C = [cls.lr0_closure([grammar.productions[0].lr_next], add_count)]
    for i, I in enumerate(C): cidhash[I] = i

    i = 0
    while i < len(C):
      I = C[i]
      i += 1

      asyms = set()
      for ii in I:
        asyms.update(ii.unique_syms)
      for x in asyms:
        g = cls.lr0_goto(I, x, add_count, goto_cache)
        if not g: continue
        if g in cidhash: continue
        cidhash[g] = len(C)
        C.append(g)
    return C

  @classmethod
  def lr0_closure(cls, I, add_count):
    add_count.incr()

    J = I[:]
    added = True
    while added:
      added = False
      for j in J:
        for x in j.lr_after:
          if x.lr0_added == add_count.value: continue
          J.append(x.lr_next)
          x.lr0_added = add_count.value
          added = True
    return J

  @classmethod
  def lr0_goto(cls, I, x, add_count, goto_cache):
    s = goto_cache.setdefault(x, IdentityDict())

    gs = []
    for p in I:
      n = p.lr_next
      if n and n.lr_before == x:
        s1 = s.get(n)
        if not s1:
          s1 = {}
          s[n] = s1
        gs.append(n)
        s = s1
    g = s.get("$end")
    if not g:
      if gs:
        g = cls.lr0_closure(gs, add_count)
        s["$end"] = g
      else:
        s["$end"] = gs
    return g

  @classmethod
  def add_lalr_lookaheads(cls, grammar, C, add_count, cidhash, goto_cache):
    nullable = cls.compute_nullable_nonterminals(grammar)
    trans = cls.find_nonterminal_transitions(grammar, C)
    readsets = cls.compute_read_sets(grammar, C, trans, nullable, add_count, cidhash, goto_cache)
    lookd, included = cls.compute_lookback_includes(grammar, C, trans, nullable, add_count, cidhash, goto_cache)
    followsets = cls.compute_follow_sets(trans, readsets, included)
    cls.add_lookaheads(lookd, followsets)

  @classmethod
  def compute_nullable_nonterminals(cls, grammar):
    nullable = set()
    num_nullable = 0
    while True:
      for p in grammar.productions[1:]:
        if p.getlength() == 0:
          nullable.add(p.name)
          continue
        for t in p.prod:
          if t not in nullable: break
        else:
          nullable.add(p.name)
      if len(nullable) == num_nullable: break
      num_nullable = len(nullable)
    return nullable

  @classmethod
  def find_nonterminal_transitions(cls, grammar, C):
    trans = []
    for idx, state in enumerate(C):
      for p in state:
        if p.lr_index < p.getlength() - 1:
          t = (idx, p.prod[p.lr_index + 1])
          if t[1] in grammar.nonterminals and t not in trans:
            trans.append(t)
    return trans

  @classmethod
  def compute_read_sets(cls, grammar, C, ntrans, nullable, add_count, cidhash, goto_cache):
    return digraph(
      ntrans,
      R=lambda x: cls.reads_relation(C, x, nullable, add_count, cidhash, goto_cache),
      FP=lambda x: cls.dr_relation(grammar, C, x, nullable, add_count, goto_cache)
    )

  @classmethod
  def compute_follow_sets(cls, ntrans, readsets, includesets):
    return digraph(
      ntrans,
      R=lambda x: includesets.get(x, []),
      FP=lambda x: readsets[x],
    )

  @classmethod
  def dr_relation(cls, grammar, C, trans, nullable, add_count, goto_cache):
    state, N = trans
    terms = []

    g = cls.lr0_goto(C[state], N, add_count, goto_cache)
    for p in g:
      if p.lr_index < p.getlength() - 1:
        a = p.prod[p.lr_index + 1]
        if a in grammar.terminals and a not in terms:
          terms.append(a)
    if state == 0 and N == grammar.productions[0].prod[0]:
      terms.append("$end")
    return terms

  @classmethod
  def reads_relation(cls, C, trans, empty, add_count, cidhash, goto_cache):
    rel = []
    state, N = trans

    g = cls.lr0_goto(C[state], N, add_count, goto_cache)
    j = cidhash.get(g, -1)
    for p in g:
      if p.lr_index < p.getlength() - 1:
        a = p.prod[p.lr_index + 1]
        if a in empty: rel.append((j, a))
    return rel

  @classmethod
  def compute_lookback_includes(cls, grammar, C, trans, nullable, add_count, cidhash, goto_cache):
    lookdict = {}
    includedict = {}

    dtrans = dict.fromkeys(trans, 1)

    for state, N in trans:
      lookb = []
      includes = []
      for p in C[state]:
        if p.name != N: continue

        lr_index = p.lr_index
        j = state
        while lr_index < p.getlength() - 1:
          lr_index += 1
          t = p.prod[lr_index]

          if (j, t) in dtrans:
            li = lr_index + 1
            while li < p.getlength():
              if p.prod[li] in grammar.terminals:
                break
              if p.prod[li] not in nullable:
                break
              li += 1
            else:
              includes.append((j, t))

          g = cls.lr0_goto(C[j], t, add_count, goto_cache)
          j = cidhash.get(g, -1)

        for r in C[j]:
          if r.name != p.name: continue
          if r.getlength() != p.getlength(): continue
          i = 0
          while i < r.lr_index:
            if r.prod[i] != p.prod[i + 1]: break
            i += 1
          else:
            lookb.append((j, r))

      for i in includes: includedict.setdefault(i, []).append((state, N))
      lookdict[state, N] = lookb
    return lookdict, includedict

  @classmethod
  def add_lookaheads(cls, lookbacks, followset):
    for trans, lb in lookbacks.items():
      for state, p in lb:
        f = followset.get(trans, [])
        laheads = p.lookaheads.setdefault(state, [])
        for a in f:
          if a not in laheads:
            laheads.append(a)
    
