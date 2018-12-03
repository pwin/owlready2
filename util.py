# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2017-2018 Jean-Baptiste LAMY
# LIMICS (Laboratoire d'informatique médicale et d'ingénierie des connaissances en santé), UMR_S 1142
# University Paris 13, Sorbonne paris-Cité, Bobigny, France

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#def _int_base_62(i):
#  if i == 0: return ""
#  return _int_base_62(i // 62) + "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"[i % 62]
  
  
class FTS(str):
  __slots__ = ["lang"]
  def __new__(Class, s, lang = ""): return str.__new__(Class, s)
  
  def __init__(self, s, lang = ""):
    str.__init__(self)
    self.lang = lang

class NumS(object):
  _OPERATORS = { "<", ">", ">=", "<=", "=", "!=" }
  def __init__(self, *operators_and_values):
    self.operators_and_values = list(zip(operators_and_values[::2], operators_and_values[1::2]))
    for (operator, value) in self.operators_and_values:
      if not operator in self._OPERATORS: raise ValueError("Supported operators are %s!" % self._OPERATORS)
    #  assert (type(value) is float) or (type(value) is int)
    
    
class normstr(str):
  __slots__ = []

class locstr(str):
  __slots__ = ["lang"]
  def __new__(Class, s, lang = ""): return str.__new__(Class, s)
  
  def __init__(self, s, lang = ""):
    str.__init__(self)
    self.lang = lang
    
  def __eq__(self, other):
    return str.__eq__(self, other) and ((not isinstance(other, locstr)) or (self.lang == other.lang))
  
  def __hash__(self): return str.__hash__(self)


class FirstList(list):
  __slots__ = []
  def first(self):
    if len(self) != 0: return self[0]
    return None
  
  
class CallbackList(FirstList):
  __slots__ = ["_obj", "_callback"]
  def __init__(self, l, obj, callback):
    super().__init__(l)
    self._obj      = obj
    self._callback = callback
  def _set  (self, l):          super().__init__(l)
  def _append(self, x):         super().append(x)
  def _remove(self, x):         super().remove(x)
  def reinit(self, l):          old = list(self); super().__init__(l)       ; self._callback(self._obj, old)
  def append(self, x):          old = list(self); super().append(x)         ; self._callback(self._obj, old)
  def insert(self, i, x):       old = list(self); super().insert(i, x)      ; self._callback(self._obj, old)
  def extend(self, l):          old = list(self); super().extend(l)         ; self._callback(self._obj, old)
  def remove(self, x):          old = list(self); super().remove(x)         ; self._callback(self._obj, old)
  def __delitem__(self, i):     old = list(self); super().__delitem__(i)    ; self._callback(self._obj, old)
  def __setitem__(self, i, x):  old = list(self); super().__setitem__(i, x) ; self._callback(self._obj, old)
  def __delslice__(self, i):    old = list(self); super().__delslice__(i)   ; self._callback(self._obj, old)
  def __setslice__(self, i, x): old = list(self); super().__setslice__(i, x); self._callback(self._obj, old)
  def __iadd__(self, x):        old = list(self); super().__iadd__(x)       ; self._callback(self._obj, old); return self
  def __imul__(self, x):        old = list(self); super().__imul__(x)       ; self._callback(self._obj, old); return self
  def pop(self, i):             old = list(self); r = super().pop(i)        ; self._callback(self._obj, old); return r
  def clear(self):              old = list(self); super().clear()           ; self._callback(self._obj, old)
  
class LanguageSublist(CallbackList):
  __slots__ = ["_l", "_lang"]
  def __init__(self, l, lang):
    list.__init__(self, (str(x) for x in l if isinstance(x, locstr) and x.lang == lang))
    self._l    = l
    self._lang = lang
    self._obj  = None
    
  def _callback(self, obj, old):
    new = set(self)
    l = [x for x in self._l if not(isinstance(x, locstr) and x.lang == self._lang)]
    l.extend(locstr(x, self._lang) for x in new)
    self._l.reinit(l)
    
  def reinit(self, l):
    if isinstance(l, str): l = [locstr(l, self._lang)]
    else:                  l = [locstr(x, self._lang) for x in l]
    CallbackList.reinit(self, l)


class CallbackListWithLanguage(CallbackList):
  __slots__ = []
  def __getattr__(self, attr):
    if len(attr) != 2: raise AttributeError("'%s' is not a language code (must be 2-char string)!" % attr)
    return LanguageSublist(self, attr)
  
  def __setattr__(self, attr, values):
    if attr.startswith("_"):
      super.__setattr__(self, attr, values)
    else:
      if len(attr) != 2: raise AttributeError("'%s' is not a language code (must be 2-char string)!" % attr)
      if isinstance(values, str): values = { locstr(values, attr) }
      else:                       values = { locstr(value , attr) for value in values }
      l = [x for x in self if not(isinstance(x, locstr) and (x.lang == attr))]
      if isinstance(values, str): l.append(locstr(values, attr))
      else:                       l.extend(locstr(x, attr) for x in values)
      self.reinit(l)
  

class LazyList(FirstList):
  __slots__ = ["_populate"]
  
  def __init__(self, populate):
    super().__init__()
    self._populate = populate
  
  def __repr__(self):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().__repr__()
  
  def __str__(self):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().__str__()
    
  def __iter__(self):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().__iter__()
    
  def __len__(self):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().__len__()
    
  def __eq__(self, o):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().__eq__(o)
    
  def __ne__(self, o):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().__ne__(o)
    
  def __getitem__(self, i):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().__getitem__(i)
    
  def __delitem__(self, i):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    super().__delitem__(i)
    
  def __setitem__(self, i, x):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    super().__setitem__(i, x)
    
  def __iadd__(self, x):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    super().__iadd__(x)
    
  def __imul__(self, x):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    super().__imul__(x)
    
  def pop(self, index):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().pop(index)
    
  def count(self, e):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().count(e)
    
  def index(self, e):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().index(e)
    
  def reverse(self):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().reverse()
  
  def sort(self, key = None, reverse = False):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().sort(key, reverse)
    
  def append(self, e):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().append(e)
    
  def insert(self, index, e):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().insert(index, e)
    
  def extend(self, l):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().extend(l)
    
  def remove(self, e):
    if self._populate: FirstList.__init__(self, self._populate()); self._populate = None
    return super().remove(e)
    
  def clear(self):
    if self._populate: self._populate = None
    return super().clear()
    
  
  
class Environment(object):
  __slots__ = ["level"]
  def __init__(self): self.level = 0
    
  def __repr__(self): return "<Environment, level %s>" % self.level
  
  def __bool__(self): return self.level != 0
  
  def __enter__(self): self.level += 1
    
  def __exit__(self, exc_type = None, exc_val = None, exc_tb = None): self.level -= 1
    
