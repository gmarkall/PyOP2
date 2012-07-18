import unittest
import numpy
import random

from pyop2 import op2
# Initialise OP2
op2.init(backend='sequential', diags=0)

def _seed():
    return 0.02041724

#max...
nelems = 92681

class IndirectLoopTest(unittest.TestCase):
    """

    Indirect Loop Tests

    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_onecolor_wo(self):
        iterset = op2.Set(nelems, "iterset")
        indset = op2.Set(nelems, "indset")

        x = op2.Dat(indset, 1, numpy.array(range(nelems), dtype=numpy.uint32), numpy.uint32, "x")

        u_map = numpy.array(range(nelems), dtype=numpy.uint32)
        random.shuffle(u_map, _seed)
        iterset2indset = op2.Map(iterset, indset, 1, u_map, "iterset2indset")

        kernel_wo = "void kernel_wo(unsigned int* x) { *x = 42; }\n"

        op2.par_loop(op2.Kernel(kernel_wo, "kernel_wo"), iterset, x(iterset2indset(0), op2.WRITE))
        self.assertTrue(all(map(lambda x: x==42, x.data)))

    def test_onecolor_rw(self):
        iterset = op2.Set(nelems, "iterset")
        indset = op2.Set(nelems, "indset")

        x = op2.Dat(indset, 1, numpy.array(range(nelems), dtype=numpy.uint32), numpy.uint32, "x")

        u_map = numpy.array(range(nelems), dtype=numpy.uint32)
        random.shuffle(u_map, _seed)
        iterset2indset = op2.Map(iterset, indset, 1, u_map, "iterset2indset")

        kernel_rw = "void kernel_rw(unsigned int* x) { (*x) = (*x) + 1; }\n"

        op2.par_loop(op2.Kernel(kernel_rw, "kernel_rw"), iterset, x(iterset2indset(0), op2.RW))
        self.assertEqual(sum(x.data), nelems * (nelems + 1) / 2);

    def test_indirect_inc(self):
        iterset = op2.Set(nelems, "iterset")
        unitset = op2.Set(1, "unitset")

        u = op2.Dat(unitset, 1, numpy.array([0], dtype=numpy.uint32), numpy.uint32, "u")

        u_map = numpy.zeros(nelems, dtype=numpy.uint32)
        iterset2unit = op2.Map(iterset, unitset, 1, u_map, "iterset2unitset")

        kernel_inc = "void kernel_inc(unsigned int* x) { (*x) = (*x) + 1; }\n"

        op2.par_loop(op2.Kernel(kernel_inc, "kernel_inc"), iterset, u(iterset2unit(0), op2.INC))
        self.assertEqual(u.data[0], nelems)

    def test_global_inc(self):
        iterset = op2.Set(nelems, "iterset")
        indset = op2.Set(nelems, "indset")

        x = op2.Dat(indset, 1, numpy.array(range(nelems), dtype=numpy.uint32), numpy.uint32, "x")
        g = op2.Global(1, 0, numpy.uint32, "g")

        u_map = numpy.array(range(nelems), dtype=numpy.uint32)
        random.shuffle(u_map, _seed)
        iterset2indset = op2.Map(iterset, indset, 1, u_map, "iterset2indset")

        kernel_global_inc = "void kernel_global_inc(unsigned int *x, unsigned int *inc) { (*x) = (*x) + 1; (*inc) += (*x); }\n"

        op2.par_loop(op2.Kernel(kernel_global_inc, "kernel_global_inc"), iterset,
                     x(iterset2indset(0), op2.RW),
                     g(op2.INC))
        self.assertEqual(sum(x.data), nelems * (nelems + 1) / 2)
        self.assertEqual(g.data[0], nelems * (nelems + 1) / 2)

    def test_2d_dat(self):
        iterset = op2.Set(nelems, "iterset")
        indset = op2.Set(nelems, "indset")

        x = op2.Dat(indset, 2, numpy.array([range(nelems), range(nelems)], dtype=numpy.uint32), numpy.uint32, "x")

        u_map = numpy.array(range(nelems), dtype=numpy.uint32)
        random.shuffle(u_map, _seed)
        iterset2indset = op2.Map(iterset, indset, 1, u_map, "iterset2indset")

        kernel_wo = "void kernel_wo(unsigned int* x) { x[0] = 42; x[1] = 43; }\n"

        op2.par_loop(op2.Kernel(kernel_wo, "kernel_wo"), iterset, x(iterset2indset(0), op2.WRITE))
        self.assertTrue(all(map(lambda x: all(x==[42,43]), x.data)))

    def test_2d_map(self):
        nedges = nelems - 1
        nodes = op2.Set(nelems, "nodes")
        edges = op2.Set(nedges, "edges")
        node_vals = op2.Dat(nodes, 1, numpy.array(range(nelems), dtype=numpy.uint32), numpy.uint32, "node_vals")
        edge_vals = op2.Dat(edges, 1, numpy.array([0] * nedges, dtype=numpy.uint32), numpy.uint32, "edge_vals")

        e_map = numpy.array([(i, i+1) for i in range(nedges)], dtype=numpy.uint32)
        edge2node = op2.Map(edges, nodes, 2, e_map, "edge2node")

        kernel_sum = """
        void kernel_sum(unsigned int *nodes1, unsigned int *nodes2, unsigned int *edge)
        { *edge = *nodes1 + *nodes2; }
        """
        op2.par_loop(op2.Kernel(kernel_sum, "kernel_sum"), edges,
                     node_vals(edge2node(0), op2.READ),
                     node_vals(edge2node(1), op2.READ),
                     edge_vals(op2.IdentityMap, op2.WRITE))

        expected = numpy.asarray(range(1, nedges * 2 + 1, 2)).reshape(nedges, 1)
        self.assertTrue(all(expected == edge_vals.data))

suite = unittest.TestLoader().loadTestsFromTestCase(IndirectLoopTest)
unittest.TextTestRunner(verbosity=0, failfast=False).run(suite)

# refactor to avoid recreating input data for each test cases