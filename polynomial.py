# polynomial calculator

from fractions import Fraction
import math
from copy import deepcopy
from typing import Union, List, Tuple, Dict
import re


class Monomial:

    def __init__(self, s=''):
        """
        Args:
            s: a number, a monomial, or a string expression
        """
        self._coe = Fraction(1)  # leading coefficient
        self._symbols = {}  # symbols and powers

        if type(s) in [int, float, Fraction]:
            self._coe = Fraction(s)
            return
        elif type(s) == Monomial:
            self._coe = s._coe
            self._symbols = deepcopy(s._symbols)
            return
        elif type(s) != str:
            raise TypeError("unrecognized parameter type")

        s = s.replace(' ', '')
        if s == '':
            return
        s = re.sub(r"\-([A-Za-z])", "-1*\\1", s)  # -x => -1*x
        for t in s.replace('**', '^').split('*'):
            if '^' in t:
                t, p = t.split('^')
                p = int(p)
            else:
                p = 1
            if not type(p) == int:
                raise ValueError("Power must be an integer")
            if t.lstrip('-').replace('/', '').isnumeric():
                self._coe *= Fraction(t)**p
            elif self._is_valid_variable_name(t):
                if t in self._symbols:
                    self._symbols[t] += p
                else:
                    self._symbols[t] = p
                if self._symbols[t] == 0:
                    self._symbols.pop(t)
            else:
                raise ValueError(f"Invalid symbol {t}")

    @staticmethod
    def _is_valid_variable_name(s: str) -> bool:
        """Test if a string is a valid math variable name
        Additional info:
            A valid variable name has at least one letter,
            consists of ASCII letters, numbers, and underscores,
            and started with a letter.
        Args:
            s: a string, the variable name
        Returns:
            True if the name is valid, False if invalid
        """
        return bool(re.match(r"^[A-Za-z][A-Za-z0-9_]*$", s))

    def get_coe(self) -> Fraction:
        """Get the coefficient of the monomial"""
        return self._coe

    def get_power(self, symbol: str) -> int:
        """Get the power of a given variable name"""
        if symbol in self._symbols:
            return self._symbols[symbol]
        return 0

    def get_symbols(self) -> dict:
        """Get all symbols in the monomial"""
        # return self._symbols
        return deepcopy(self._symbols)

    def set_coe(self, coe: Fraction) -> None:
        """Set the coefficient of the monomial
        Args:
            coe: a rational number, the new coefficient of the monomial
        """
        try:
            coe = Fraction(coe)
        except:
            raise ValueError("Cannot convert coefficient to a valid fraction")
        self._coe = coe

    def set_power(self, symbol: str, power: int) -> None:
        """Set the power of a variable
        Args:
            symbol: the variable name
            power: the power of the variable
        """
        if not self._is_valid_variable_name(symbol):
            raise ValueError("Invalid variable name " + symbol)
        if power != 0:
            self._symbols[symbol] = power
        elif symbol in self._symbols:
            self._symbols.pop(symbol)

    def __str__(self) -> str:
        ans = []
        if self._coe != 1 or self._symbols == {}:
            ans.append(str(self._coe))
        for s in self._symbols:
            p = self._symbols[s]
            if p == 1:
                ans.append(s)
            else:
                ans.append(f"{s}**{p}")
        return '*'.join(ans)

    def __eq__(self, other):
        other = Monomial(other)
        return self._coe == other._coe and self._symbols == other._symbols

    def __mul__(a, b):
        c = Monomial()
        c._coe = a._coe * b._coe
        if c._coe == 0:
            return c
        for s in a._symbols:
            v = a._symbols[s]
            for t in b._symbols:
                if s == t:
                    v += b._symbols[t]
            if v != 0:
                c._symbols[s] = v
        for s in b._symbols:
            if s not in a._symbols:
                c._symbols[s] = b._symbols[s]
        return c

    def __pow__(self, e: int):
        r = Monomial(1)
        if e == 0:
            return r
        r._coe = pow(self._coe, e)
        for symbol in self._symbols:
            r._symbols[symbol] = self._symbols[symbol] * e
        return r

    def subs(self, maps: dict) -> "Monomial":
        """Substitute numbers into monomial
        Args:
            A map of variable names to rational numbers
        Returns:
            A monomial with corresponding variables replaced by numbers
        """
        ans = Monomial()
        ans._coe *= self._coe
        for s in self._symbols:
            if s in maps:
                ans._coe *= Fraction(maps[s])**self._symbols[s]
            else:
                ans._symbols[s] = self._symbols[s]
        if ans._coe == 0:
            ans._symbols = {}
        return ans


class Polynomial():

    def __init__(self, s=''):
        if s == 0:
            self._terms = []
            return
        if type(s) == Polynomial:
            self._terms = deepcopy(s._terms)
            return
        if type(s) == Monomial:
            self._terms = [deepcopy(s)]
            return
        if type(s) != str:
            self._terms = [Monomial(s)]
            return
        if s == '':
            self._terms = []
        else:
            s = s.replace('-', '+-').replace('++', '+')
            s = s.replace('^+-', '^-').replace('*+-', '*-')
            s = s.lstrip('+').split('+')
            self._terms = [Monomial(si) for si in s]

    def get_terms(self) -> List[Monomial]:
        """Get a list of monomial terms in the polynomial"""
        return deepcopy(self._terms)

    def get_denominator(self) -> int:
        """Return the least common multiple of the demoninators of all monomial coefficients"""
        ans = 1
        for mon in self._terms:
            den = mon._coe.denominator
            ans = math.lcm(ans, den)
        return ans

    def __str__(self):
        if len(self._terms) == 0:
            return '0'
        terms = []
        for si in self._terms:
            if si._coe != 0:
                terms.append(str(si))
        if terms == []:
            return '0'
        s = '+'.join(terms)
        s = s.replace('+-', '-')
        s = s.replace('-1*', '-')
        return s

    def __repr__(self):
        return str(self)

    def simplify(self) -> "Polynomial":
        terms = {}  # symbols, coe
        for term in self._terms:
            coe = term._coe
            # https://stackoverflow.com/a/13264725
            symbols = frozenset(sorted(term._symbols.items()))
            if symbols in terms:
                terms[symbols] += coe
            else:
                terms[symbols] = coe
        result = Polynomial()
        for (symbols, coe) in terms.items():
            if coe == 0:
                continue
            term = Monomial()
            term._coe = coe
            term._symbols = dict(symbols)
            result._terms.append(term)
        return result

    def collect(self, symbol: str) -> Dict[int, "Polynomial"]:
        """Collect like terms
        Args:
            symbol: a variable name, the variable to be collected
        Returns:
            a dict that maps an integer to a Polynomial,
            the power and the coefficient
        """
        result = {}
        for term in self._terms:
            term = deepcopy(term)
            power = term.get_power(symbol)
            term.set_power(symbol, 0)
            if power in result:
                result[power] += term
            else:
                result[power] = Polynomial(term)
        return result

    def __eq__(self, other):
        p1 = self.simplify()
        p2 = Polynomial(other).simplify()
        if len(p1._terms) != len(p2._terms):
            return False
        for m1 in p1._terms:
            found = False
            for m2 in p2._terms:
                if m1 == m2:
                    found = True
                    break
            if not found:
                return False
        return True

    def __add__(p, q):
        if type(q) != Polynomial:
            q = Polynomial(q)
        r = Polynomial()
        r._terms = p._terms + q._terms
        return r.simplify()

    def __neg__(p):
        q = deepcopy(p)
        for i in range(len(q._terms)):
            q._terms[i]._coe *= -1
        return q

    def __sub__(p, q):
        if type(q) != Polynomial:
            q = Polynomial(q)
        return p.__add__(q.__neg__())

    def __mul__(p, q):
        if type(q) != Polynomial:
            q = Polynomial(q)
        r = Polynomial()
        for pi in p._terms:
            for qi in q._terms:
                r._terms.append(pi*qi)
        return r.simplify()

    def __pow__(self, e: int):
        if len(self._terms) == 0:
            return Polynomial(1)
        if len(self._terms) == 1:
            return Polynomial(self._terms[0] ** e)
        if not e >= 0:
            raise ValueError("Exponent must be a positive integer.")
        r = Polynomial('1')
        x = deepcopy(self)
        while e:
            if e & 1:
                r = r * x
            e >>= 1
            if e:
                x = x * x
        return r

    def __radd__(p, q):
        return Polynomial(q).__add__(p)

    def __rsub__(p, q):
        return Polynomial(q).__sub__(p)

    def __rmul__(p, q):
        return Polynomial(q).__mul__(p)

    def subs(self, maps: dict) -> "Polynomial":
        ans = Polynomial()
        for t in self._terms:
            ans += Polynomial(t.subs(maps))
        return ans


def integrate(poly: Union[Polynomial, Monomial],
              vars: List[Union[str, Tuple[str, Fraction, Fraction]]]) -> Union[Polynomial, Monomial]:
    """Integrate a monomial or a polynomial
    Args:
        poly: a Polynomial or Monomial object, to be integrated
        vars: a list of integration variables, each is
              either a string for the variable name for indefinite integral
              or a tuple of variable name and boundries for definite integral
    Returns:
        The integral of the given expression, same type
    """
    if type(poly) == Monomial:
        mor = deepcopy(poly)
        for a in vars:
            if type(a) == str:  # indefinite
                if a in mor._symbols:
                    if mor._symbols[a] == -1:
                        raise ZeroDivisionError("Integral of -1th power")
                    mor._symbols[a] += 1
                    mor._coe /= mor._symbols[a]
                else:
                    mor._symbols[a] = 1
            elif type(a) == tuple:  # definite
                a, x0, x1 = a
                if a in mor._symbols:
                    if mor._symbols[a] == -1:
                        raise ZeroDivisionError("Integral of -1th power")
                    deg = mor._symbols[a] + 1
                    mor._coe *= Fraction(Fraction(x1) **
                                         deg-Fraction(x0)**deg, deg)
                    mor._symbols.pop(a)
                else:
                    mor._coe *= x1-x0
            else:
                raise TypeError('Integral bound must be string or tuple')
        return mor
    else:
        poly = Polynomial(poly)
        for i in range(len(poly._terms)):
            poly._terms[i] = integrate(poly._terms[i], vars)
        poly = poly.simplify()
        return poly


def diff(poly: Union[Polynomial, Monomial],
         vars: List[str]) -> Union[Polynomial, Monomial]:
    """Calculate the derivative of a monomial or a polynomial
    Args:
        poly: a Polynomial or Monomial object to be differentiated
        vars: a list of differentiation variables
    Returns:
        The derivative of the given expression, same type
    """
    if type(poly) == Monomial:
        mor = deepcopy(poly)
        for var in vars:
            if var not in mor._symbols:
                return Monomial(0)
            mor._coe *= mor._symbols[var]
            mor._symbols[var] -= 1
            if mor._symbols[var] == 0:
                mor._symbols.pop(var)
        if mor._coe == 0:
            mor._symbols = {}
        return mor
    else:
        poly = Polynomial(poly)
        for i in range(len(poly._terms)):
            poly._terms[i] = diff(poly._terms[i], vars)
        return poly.simplify()


def grad(poly: Polynomial, vars: List[str]) -> List[Polynomial]:
    result = []
    for var in vars:
        result.append(diff(poly, [var]))
    return result


def laplacian(poly: Polynomial, vars: List[str]) -> Polynomial:
    ans = Polynomial(0)
    for var in vars:
        d2fdx2 = diff(poly, [var, var])
        ans += d2fdx2
    return ans


def polyeval(_expr: str) -> str:
    try:
        # using eval currently, should parse it

        keywords = ['False', 'None', 'True', '__import__', '__peg_parser__', 'abs', 'aiter', 'all', 'and', 'anext', 'any', 'as',
                    'ascii', 'assert', 'async', 'await', 'bin', 'bool', 'break', 'breakpoint', 'bytearray', 'bytes', 'callable', 'chr', 'class',
                    'classmethod', 'compile', 'complex', 'continue', 'def', 'del', 'delattr', 'dict', 'dir', 'divmod', 'elif', 'else', 'enumerate',
                    'eval', 'except', 'exec', 'filter', 'finally', 'float', 'for', 'format', 'from', 'frozenset', 'getattr', 'global', 'globals',
                    'hasattr', 'hash', 'help', 'hex', 'id', 'if', 'import', 'in', 'input', 'int', 'is', 'isinstance', 'issubclass', 'iter',
                    'lambda', 'len', 'list', 'locals', 'map', 'max', 'memoryview', 'min', 'next', 'nonlocal', 'not', 'object', 'oct', 'open',
                    'or', 'ord', 'pass', 'pow', 'print', 'property', 'raise', 'range', 'repr', 'return', 'reversed', 'round', 'set', 'setattr',
                    'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super', 'try', 'tuple', 'type', 'vars', 'while', 'with', 'yield', 'zip']

        for _varname in re.findall(r"[A-Za-z_][A-Za-z_0-9]*", _expr):
            if _varname in keywords:
                raise ValueError(
                    f"Variable name '{_varname}' is a Python keyword")
            if _varname.startswith('_'):
                raise ValueError(
                    f"Variable name '{_varname}' cannot start with underscore")
            if _varname not in globals():
                locals()[_varname] = Polynomial(_varname)
        _expr = _expr.replace('^', '**')
        return str(eval(_expr)).replace('**', '^')
    except BaseException as _error:
        return 'Error: ' + str(_error)
