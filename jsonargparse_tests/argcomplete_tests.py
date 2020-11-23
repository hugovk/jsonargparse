#!/usr/bin/env python3

import sys
from enum import Enum
from typing import List, Optional
from io import BytesIO, StringIO
from contextlib import redirect_stdout, redirect_stderr
from jsonargparse_tests.base import *


@unittest.skipIf(not argcomplete_support, 'argcomplete package is required')
class ArgcompleteTests(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.orig_environ = os.environ.copy()
        self.argcomplete = import_argcomplete('ArgcompleteTests')


    @classmethod
    def tearDownClass(self):
        os.environ.clear()
        os.environ.update(self.orig_environ)


    def setUp(self):
        super().setUp()
        self.tearDownClass()
        os.environ['_ARGCOMPLETE'] = '1'
        os.environ['_ARGCOMPLETE_SUPPRESS_SPACE'] = '1'
        os.environ['_ARGCOMPLETE_COMP_WORDBREAKS'] = " \t\n\"'><=;|&(:"
        os.environ['COMP_TYPE'] = str(ord('?'))   # ='63'  str(ord('\t'))='9'
        self.parser = ArgumentParser(error_handler=lambda x: x.exit(2))


    def test_complete_nested_one_option(self):
        self.parser.add_argument('--group1.op')

        os.environ['COMP_LINE'] = 'tool.py --group1'
        os.environ['COMP_POINT'] = str(len(os.environ['COMP_LINE']))

        out = BytesIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            self.argcomplete.autocomplete(self.parser, exit_method=sys.exit, output_stream=sys.stdout)
        self.assertEqual(out.getvalue(), b'--group1.op')


    def test_complete_nested_two_options(self):
        self.parser.add_argument('--group2.op1')
        self.parser.add_argument('--group2.op2')

        os.environ['COMP_LINE'] = 'tool.py --group2'
        os.environ['COMP_POINT'] = str(len(os.environ['COMP_LINE']))

        out = BytesIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            self.argcomplete.autocomplete(self.parser, exit_method=sys.exit, output_stream=sys.stdout)
        self.assertEqual(out.getvalue(), b'--group2.op1\x0b--group2.op2')


    def test_ActionYesNo(self):
        self.parser.add_argument('--op1', action=ActionYesNo)
        self.parser.add_argument('--op2', nargs='?', action=ActionYesNo)
        self.parser.add_argument('--with-op3', action=ActionYesNo(yes_prefix='with-', no_prefix='without-'))

        for arg, expected in [('--op1', b'--op1'),
                              ('--no_op1', b'--no_op1'),
                              ('--op2', b'--op2'),
                              ('--no_op2', b'--no_op2'),
                              ('--op2=', b'true\x0bfalse\x0byes\x0bno'),
                              ('--with-op3', b'--with-op3'),
                              ('--without-op3', b'--without-op3')]:
            os.environ['COMP_LINE'] = 'tool.py '+arg
            os.environ['COMP_POINT'] = str(len(os.environ['COMP_LINE']))

            with self.subTest(os.environ['COMP_LINE']):
                out = BytesIO()
                with redirect_stdout(out), self.assertRaises(SystemExit):
                    self.argcomplete.autocomplete(self.parser, exit_method=sys.exit, output_stream=sys.stdout)
                self.assertEqual(expected, out.getvalue())


    def test_ActionEnum(self):
        class MyEnum(Enum):
            abc = 1
            xyz = 2
            abd = 3

        self.parser.add_argument('--enum', type=MyEnum)

        os.environ['COMP_LINE'] = 'tool.py --enum=ab'
        os.environ['COMP_POINT'] = str(len(os.environ['COMP_LINE']))

        out = BytesIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            self.argcomplete.autocomplete(self.parser, exit_method=sys.exit, output_stream=sys.stdout)
        self.assertEqual(out.getvalue(), b'abc\x0babd')


    @unittest.skipIf(not jsonschema_support, 'jsonschema package is required')
    def test_optional(self):
        class MyEnum(Enum):
            A = 1
            B = 2

        self.parser.add_argument('--enum', type=Optional[MyEnum])
        self.parser.add_argument('--bool', type=Optional[bool])

        for arg, expected in [('--enum=', b'A\x0bB\x0bnull'),
                              ('--bool=', b'true\x0bfalse\x0bnull')]:
            os.environ['COMP_LINE'] = 'tool.py '+arg
            os.environ['COMP_POINT'] = str(len(os.environ['COMP_LINE']))

            with self.subTest(os.environ['COMP_LINE']):
                out = BytesIO()
                with redirect_stdout(out), self.assertRaises(SystemExit):
                    self.argcomplete.autocomplete(self.parser, exit_method=sys.exit, output_stream=sys.stdout)
                self.assertEqual(expected, out.getvalue())


    @unittest.skipIf(not jsonschema_support, 'jsonschema package is required')
    def test_ActionJsonSchema(self):
        self.parser.add_argument('--json', action=ActionJsonSchema(schema={'type': 'object'}))
        self.parser.add_argument('--list', type=List[int])
        self.parser.add_argument('--bool', type=bool)

        for arg, expected in [('--json=1',            'value not yet valid'),
                              ("--json='{\"a\": 1}'", 'value already valid'),
                              ("--list='[1, 2, 3]'",  'value already valid, expected type List[int]')]:
            os.environ['COMP_LINE'] = 'tool.py '+arg
            os.environ['COMP_POINT'] = str(len(os.environ['COMP_LINE']))

            with self.subTest(os.environ['COMP_LINE']):
                out, err = BytesIO(), StringIO()
                with redirect_stdout(out), redirect_stderr(err), self.assertRaises(SystemExit):
                    self.argcomplete.autocomplete(self.parser, exit_method=sys.exit, output_stream=sys.stdout)
                self.assertEqual(out.getvalue(), b'')
                self.assertIn(expected, err.getvalue())

                with mock.patch('os.popen') as popen_mock:
                    popen_mock.side_effect = ValueError
                    with redirect_stdout(out), redirect_stderr(err), self.assertRaises(SystemExit):
                        self.argcomplete.autocomplete(self.parser, exit_method=sys.exit, output_stream=sys.stdout)
                    self.assertEqual(out.getvalue(), b'')
                    self.assertIn(expected, err.getvalue())

        os.environ['COMP_LINE'] = 'tool.py --bool='
        os.environ['COMP_POINT'] = str(len(os.environ['COMP_LINE']))

        with self.subTest(os.environ['COMP_LINE']):
            out = BytesIO()
            with redirect_stdout(out), self.assertRaises(SystemExit):
                self.argcomplete.autocomplete(self.parser, exit_method=sys.exit, output_stream=sys.stdout)
            self.assertEqual(b'true\x0bfalse', out.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
