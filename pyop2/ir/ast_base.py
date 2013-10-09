# This file contains the hierarchy of classes that implement a kernel's
# Abstract Syntax Tree (ast)

# This dictionary is used as a template generator for simple exprs and commands
util = {}

util.update({
    "point": lambda p: "[%s]" % p,
    "assign": lambda s, e: "%s = %s" % (s, e),
    "incr": lambda s, e: "%s += %s" % (s, e),
    "incr++": lambda s: "%s++" % s,
    "wrap": lambda e: "(%s)" % e,
    "bracket": lambda s: "{%s}" % s,
    "decl": lambda q, t, s, a: "%s%s %s%s;" % (q, t, s, a),
    "decl_init": lambda q, t, s, a, e: "%s%s %s%s = %s" % (q, t, s, a, e),
    "for": lambda s1, e, s2, s3: "for (%s; %s; %s)\n%s" % (s1, e, s2, s3)
})

# Base classes of the AST ###


class Node(object):

    """The base class of the AST."""

    def __init__(self):
        self.children = []

    def gencode(self):
        code = ""
        for n in self.children:
            code += n.gencode() + "\n"
        return code


class Root(Node):

    """Root of the AST."""

    def __init__(self, children):
        Node.__init__(self)
        self.children = children

    def gencode(self):
        header = '// This code is generated by reading a pyop2 kernel AST\n\n'
        return header + Node.gencode(self)


# Expressions ###

class Expr(Node):

    def __init__(self):
        Node.__init__(self)


class BinExpr(Expr):

    def __init__(self, expr1, expr2, op):
        Expr.__init__(self)
        self.children.append(expr1)
        self.children.append(expr2)
        self.op = op

    def gencode(self):
        return self.op.join([n.gencode() for n in self.children])


class UnExpr(Expr):

    def __init__(self, expr):
        Expr.__init__(self)
        self.children.append(expr)


class ArrayInit(Expr):

    def __init__(self, values):
        Expr.__init__(self)
        self.values = values

    def gencode(self):
        return self.values


class Par(UnExpr):

    def gencode(self):
        return util["wrap"](self.children[0].gencode())


class Sum(BinExpr):

    def __init__(self, expr1, expr2):
        BinExpr.__init__(self, expr1, expr2, " + ")


class Prod(BinExpr):

    def __init__(self, expr1, expr2):
        BinExpr.__init__(self, expr1, expr2, " * ")


class Div(BinExpr):

    def __init__(self, expr1, expr2):
        BinExpr.__init__(self, expr1, expr2, " / ")


class Less(BinExpr):

    def __init__(self, expr1, expr2):
        BinExpr.__init__(self, expr1, expr2, " < ")


class Symbol(Expr):

    """A generic symbol. len(rank) = 0 => scalar, 1 => array, 2 => matrix, etc
    rank is a tuple whose entries represent iteration variables the symbol
    depends on or explicit numbers representing the entry of a tensor the
    symbol is accessing. """

    def __init__(self, symbol, rank):
        Expr.__init__(self)
        self.symbol = symbol
        self.rank = rank
        self.loop_dep = tuple([i for i in rank if not str(i).isdigit()])

    def gencode(self):
        points = ""
        for p in self.rank:
            points += util["point"](p)
        return str(self.symbol) + points


# Statements ###


class Statement(Node):

    """Base class for the statement set of productions"""

    def __init__(self, pragma=None):
        Node.__init__(self)
        self.pragma = pragma


class EmptyStatement(Statement):

    def gencode(self):
        return ""


class Assign(Statement):

    def __init__(self, sym, exp, pragma=None):
        Statement.__init__(self, pragma)
        self.children.append(sym)
        self.children.append(exp)

    def gencode(self, for_scope=False):
        return util["assign"](self.children[0].gencode(),
                              self.children[1].gencode()) + semicolon(for_scope)


class Incr(Statement):

    def __init__(self, sym, exp, pragma=None):
        Statement.__init__(self, pragma)
        self.children.append(sym)
        self.children.append(exp)

    def gencode(self, for_scope=False):
        if type(self.children[1]) == Symbol and self.children[1].symbol == 1:
            return util["incr++"](self.children[0].gencode())
        else:
            return util["incr"](self.children[0].gencode(),
                                self.children[1].gencode()) + semicolon(for_scope)


class Decl(Statement):

    """syntax: [qualifiers] typ sym [attributes] [= init];
    e.g. static const double FE0[3][3] __attribute__(align(32)) = {{...}};
    """

    def __init__(self, typ, sym, init=None, qualifiers=[], attributes=[]):
        Statement.__init__(self)
        self.typ = typ
        self.sym = sym
        self.qual = qualifiers
        self.att = attributes
        if not init:
            self.init = EmptyStatement()
        else:
            self.init = init

    def gencode(self, for_scope=False):

        def spacer(v):
            if v:
                return " ".join(self.qual) + " "
            else:
                return ""

        if type(self.init) == EmptyStatement:
            return util["decl"](spacer(self.qual), self.typ,
                                self.sym.gencode(), spacer(self.att))
        else:
            return util["decl_init"](spacer(self.qual), self.typ,
                                     self.sym.gencode(), spacer(self.att),
                                     self.init.gencode()) + semicolon(for_scope)


class Block(Statement):

    def __init__(self, stmts, pragma=None, open_scope=False):
        Statement.__init__(self, pragma)
        self.children = stmts
        self.open_scope = open_scope

    def gencode(self):
        code = "\n".join([n.gencode() for n in self.children])
        if self.open_scope:
            code = "{\n%s\n}" % indent(code)
        return code


class For(Statement):

    def __init__(self, init, cond, incr, body, pragma=None):
        Statement.__init__(self, pragma)
        self.children.append(body)
        self.init = init
        self.cond = cond
        self.incr = incr

    def gencode(self):
        return util["for"](self.init.gencode(for_scope=True),
                           self.cond.gencode(), self.incr.gencode(),
                           self.children[0].gencode())


class FunCall(Statement):

    def __init__(self, funcall):
        Statement.__init__(self)
        self.funcall = funcall

    def gencode(self):
        return self.funcall


class FunDecl(Statement):

    def __init__(self, ret, name, args, body, pred=[]):
        Statement.__init__(self)
        self.children.append(body)
        self.pred = pred
        self.ret = ret
        self.name = name
        self.args = args

    def gencode(self):
        sign_list = self.pred + [self.ret, self.name, util["wrap"](self.args)]
        return " ".join(sign_list) + \
               "\n{\n%s\n}" % indent(self.children[0].gencode())


# Utility functions ###


def indent(block):
    """Indent each row of the given string block with n*4 spaces."""
    indentation = " " * 4
    return indentation + ("\n" + indentation).join(block.split("\n"))


def semicolon(scope):
    if scope:
        return ""
    else:
        return ";\n"
