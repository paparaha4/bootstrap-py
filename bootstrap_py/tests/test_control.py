# -*- coding: utf-8 -*-
"""bootstrap_py.tests.test_control."""
import unittest
import os
import shutil
import tempfile
from glob import glob
from filecmp import dircmp
from datetime import datetime
import requests_mock
from bootstrap_py import control
from bootstrap_py.classifiers import Classifiers


# pylint: disable=too-few-public-methods
class Dummy(object):
    """Dummy class."""
    pass


class PackageDataTests(unittest.TestCase):
    """bootstrap_py.control.PackageData tests."""

    def setUp(self):
        """Prepare test data."""
        with requests_mock.Mocker() as mock:
            with open('bootstrap_py/tests/data/classifiers.txt') as fobj:
                data = fobj.read()
            mock.get(Classifiers.url,
                     text=data,
                     status_code=200)

        self.params = Dummy()
        setattr(self.params, 'foo', 'hoge')
        setattr(self.params, 'bar', 'moge')
        setattr(self.params, 'baz', 'fuga')

        self.default_params = Dummy()
        setattr(self.default_params, 'date', '2016-01-29')
        setattr(self.default_params, 'version', '1.0.0')
        setattr(self.default_params, 'description', 'dummy description.')

    def test_provides_params(self):
        """provides params without default params."""
        # pylint: disable=no-member
        pkg_data = control.PackageData(self.params)
        self.assertEqual(pkg_data.foo, 'hoge')
        self.assertEqual(pkg_data.bar, 'moge')
        self.assertEqual(pkg_data.baz, 'fuga')
        self.assertEqual(pkg_data.date, datetime.utcnow().strftime('%Y-%m-%d'))
        self.assertEqual(pkg_data.version, '0.1.0')
        self.assertEqual(pkg_data.description, '##### ToDo: Rewrite me #####')

    def test_provides_default_params(self):
        """provides params without default params."""
        # pylint: disable=no-member
        pkg_data = control.PackageData(self.default_params)
        self.assertEqual(pkg_data.date, '2016-01-29')
        self.assertEqual(pkg_data.version, '1.0.0')
        self.assertEqual(pkg_data.description, 'dummy description.')

    def test_convert_to_dict(self):
        """convert PackageData to dict."""
        dict_data = control.PackageData(self.default_params).to_dict()
        self.assertEqual(dict_data.get('date'), '2016-01-29')
        self.assertEqual(dict_data.get('version'), '1.0.0')
        self.assertEqual(dict_data.get('description'), 'dummy description.')


class PackageTreeTests(unittest.TestCase):
    """bootstrap.control.PackageTree tests."""

    def setUp(self):
        """Prepare test data."""
        self.cwd = os.getcwd()
        self.testdir = tempfile.mkdtemp(suffix='-bootstrap-py-test')
        params = Dummy()
        setattr(params, 'name', 'foo')
        setattr(params, 'author', 'Alice')
        setattr(params, 'author_email', 'alice@example.org')
        setattr(params, 'url', 'https://example.org/foo')
        setattr(params, 'license', 'gplv3')
        setattr(params, 'outdir', self.testdir)
        self.pkg_data = control.PackageData(params)
        self.pkg_tree = control.PackageTree(self.pkg_data)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.testdir)
        if os.path.isdir(self.pkg_tree.tmpdir):
            self.pkg_tree.clean()

    def test_initialize(self):
        """initialize PackageTree."""
        self.assertEqual(self.pkg_tree.name, 'foo')
        self.assertEqual(self.pkg_tree.outdir, self.testdir)
        self.assertTrue(os.path.isdir(self.pkg_tree.tmpdir))
        self.assertEqual(len(self.pkg_tree.templates.list_templates()), 16)
        self.assertEqual(self.pkg_tree.pkg_data, self.pkg_data)

    def test_mod_name(self):
        """convert path to module name."""
        self.assertEqual(getattr(self.pkg_tree, '_modname')('bar'), 'bar')
        self.assertEqual(getattr(self.pkg_tree, '_modname')('{name}'), 'foo')
        self.assertEqual(getattr(self.pkg_tree, '_modname')('{name}/tests'),
                         'foo.tests')

    def test_init_py(self):
        """convert __init__.py path."""
        self.assertEqual(getattr(self.pkg_tree, '_init_py')('foo/bar'),
                         os.path.join(self.pkg_tree.tmpdir,
                                      'foo/bar/__init__.py'))

    def test_tmpl_path(self):
        """convert tmplate path."""
        self.assertEqual(getattr(self.pkg_tree, '_tmpl_path')('foo.py.j2'),
                         os.path.join(self.pkg_tree.tmpdir,
                                      'foo.py'))

    def test_generate_dirs(self):
        """generate directories."""
        getattr(self.pkg_tree, '_generate_dirs')()
        os.chdir(self.pkg_tree.tmpdir)
        self.assertTrue(os.path.isdir(self.pkg_tree.name))
        self.assertTrue(os.path.isdir(os.path.join(self.pkg_tree.name,
                                                   'tests')))
        self.assertTrue(os.path.isdir('utils'))
        self.assertTrue(os.path.isdir('docs/source/modules'))

    def test_list_module_dirs(self):
        """list module directories."""
        self.assertEqual(getattr(self.pkg_tree, '_list_module_dirs')(),
                         ['{name}', '{name}/tests'])

    def test_generate_init(self):
        """generate __init__.py."""
        getattr(self.pkg_tree, '_generate_dirs')()
        getattr(self.pkg_tree, '_generate_init')()
        os.chdir(self.pkg_tree.tmpdir)
        self.assertTrue(os.path.isfile('foo/__init__.py'))
        self.assertTrue(os.path.isfile('foo/tests/__init__.py'))

    def test_generate_files(self):
        """generate files."""
        getattr(self.pkg_tree, '_generate_dirs')()
        getattr(self.pkg_tree, '_generate_files')()
        os.chdir(self.pkg_tree.tmpdir)
        self.assertEqual(len([i for i in glob('./*')
                              if os.path.isfile(i)]), 6)
        self.assertEqual(len([i for i in glob('./.*')
                              if os.path.isfile(i)]), 5)
        self.assertEqual(len([i for i in glob('utils/*')
                              if os.path.isfile(i)]), 1)
        self.assertEqual(len([i for i in glob('docs/source/*')
                              if os.path.isfile(i)]), 2)
        self.assertEqual(len([i for i in glob('docs/source/modules/*')
                              if os.path.isfile(i)]), 1)

    def test_copy(self):
        """copy source directory to destination directory."""
        self.pkg_tree.copy()
        dcmp = dircmp(self.pkg_tree.tmpdir, self.testdir)
        self.assertListEqual(dcmp.left_only, [])
        self.assertListEqual(dcmp.right_only, ['foo'])
        self.assertTrue(len(dcmp.common) == 0)

    def test_generate(self):
        """generate directories, and files."""
        self.pkg_tree.generate()
        os.chdir(self.pkg_tree.tmpdir)
        self.assertTrue(os.path.isdir(self.pkg_tree.name))
        self.assertTrue(os.path.isdir(os.path.join(self.pkg_tree.name,
                                                   'tests')))
        self.assertTrue(os.path.isdir('utils'))
        self.assertTrue(os.path.isdir('docs/source/modules'))
        self.assertTrue(os.path.isfile('foo/__init__.py'))
        self.assertTrue(os.path.isfile('foo/tests/__init__.py'))
        self.assertEqual(len([i for i in glob('./*')
                              if os.path.isfile(i)]), 6)
        self.assertEqual(len([i for i in glob('./.*')
                              if os.path.isfile(i)]), 5)
        self.assertEqual(len([i for i in glob('utils/*')
                              if os.path.isfile(i)]), 1)
        self.assertEqual(len([i for i in glob('docs/source/*')
                              if os.path.isfile(i)]), 2)
        self.assertEqual(len([i for i in glob('docs/source/modules/*')
                              if os.path.isfile(i)]), 1)

    def test_clean(self):
        """clean up."""
        self.pkg_tree.clean()
        self.assertFalse(os.path.isdir(self.pkg_tree.tmpdir))
