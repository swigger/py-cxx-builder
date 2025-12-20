#!/usr/bin/env python
# coding:utf8
"""Unit tests for py_cxx_builder module."""

import os
import sys
import tempfile
import pytest

from py_cxx_builder import CXXBuilder, ModiGCC, ModiMSVC


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory with pyproject.toml for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = os.path.join(tmpdir, 'pyproject.toml')
        with open(pyproject_path, 'w') as f:
            f.write('''[project]
name = "test-project"
version = "1.2.3"
''')
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(old_cwd)


class TestCXXBuilder:
    """Tests for CXXBuilder class."""

    def test_init(self, temp_project_dir):
        """Test CXXBuilder initialization."""
        builder = CXXBuilder()
        assert isinstance(builder.include_dirs, list)
        assert isinstance(builder.libdirs, list)
        assert isinstance(builder.macros, list)
        assert isinstance(builder.libs, list)
        assert isinstance(builder.extra_compile_args, list)
        assert isinstance(builder.extra_link_args, list)
        assert isinstance(builder.files, dict)
        assert builder.mainsrc is None
        assert builder.name == "test-project"
        assert builder.version == "1.2.3"

    def test_is_win_detection(self, temp_project_dir):
        """Test platform detection."""
        builder = CXXBuilder()
        assert builder.is_win == (os.name == "nt")

    def test_modi_selection(self, temp_project_dir):
        """Test correct modifier class is selected based on platform."""
        builder = CXXBuilder()
        if os.name == "nt":
            assert isinstance(builder.modi, ModiMSVC)
        else:
            assert isinstance(builder.modi, ModiGCC)

    def test_add_macro_with_value(self, temp_project_dir):
        """Test adding macro with explicit value."""
        builder = CXXBuilder()
        initial_count = len(builder.macros)
        builder.add_macro('TEST_MACRO', 42)
        assert len(builder.macros) == initial_count + 1
        assert ('TEST_MACRO', 42) in builder.macros

    def test_add_macro_without_value(self, temp_project_dir):
        """Test adding macro without value defaults to 1."""
        builder = CXXBuilder()
        initial_count = len(builder.macros)
        builder.add_macro('ENABLE_FEATURE')
        assert len(builder.macros) == initial_count + 1
        assert ('ENABLE_FEATURE', 1) in builder.macros

    def test_add_files(self, temp_project_dir):
        """Test adding source files."""
        builder = CXXBuilder()
        # Create test file
        test_file = os.path.join(temp_project_dir, 'test.cpp')
        with open(test_file, 'w') as f:
            f.write('int main() { return 0; }')

        builder.add_files([test_file])
        assert test_file in builder.files

    def test_add_files_with_directory(self, temp_project_dir):
        """Test adding source files with directory prefix."""
        builder = CXXBuilder()
        # Create test file
        test_file = 'test.cpp'
        full_path = os.path.join(temp_project_dir, test_file)
        with open(full_path, 'w') as f:
            f.write('int main() { return 0; }')

        builder.add_files([test_file], directory=temp_project_dir)
        assert os.path.abspath(full_path) in builder.files

    def test_add_files_empty_string_ignored(self, temp_project_dir):
        """Test that empty strings in file list are ignored."""
        builder = CXXBuilder()
        initial_count = len(builder.files)
        builder.add_files([''])
        assert len(builder.files) == initial_count

    def test_remove_files(self, temp_project_dir):
        """Test removing source files."""
        builder = CXXBuilder()
        # Create and add test file
        test_file = os.path.join(temp_project_dir, 'test.cpp')
        with open(test_file, 'w') as f:
            f.write('int main() { return 0; }')

        builder.add_files([test_file])
        assert test_file in builder.files

        builder.remove_files([test_file])
        assert test_file not in builder.files

    def test_remove_nonexistent_file(self, temp_project_dir):
        """Test removing a file that was never added."""
        builder = CXXBuilder()
        # Should not raise any exception
        builder.remove_files(['/nonexistent/file.cpp'])

    def test_set_main_file(self, temp_project_dir):
        """Test setting the main source file."""
        builder = CXXBuilder()
        # Create test file
        main_file = os.path.join(temp_project_dir, 'main.cpp')
        with open(main_file, 'w') as f:
            f.write('int main() { return 0; }')

        builder.set_main_file(main_file)
        assert builder.mainsrc == main_file
        assert builder._need_test_link is False

    def test_set_main_file_with_test_linker(self, temp_project_dir):
        """Test setting main file that contains TEST_LINKER."""
        builder = CXXBuilder()
        main_file = os.path.join(temp_project_dir, 'main.cpp')
        with open(main_file, 'w') as f:
            f.write('#ifdef TEST_LINKER\nint main() { return 0; }\n#endif')

        builder.set_main_file(main_file)
        assert builder._need_test_link is True

    def test_sysver_format(self, temp_project_dir):
        """Test system version string format."""
        builder = CXXBuilder()
        expected = f"{sys.version_info[0]}.{sys.version_info[1]}"
        assert builder.sysver == expected

    def test_hooker_called(self, temp_project_dir):
        """Test that platform hooker is called."""
        called = []

        def hooker(builder):
            called.append(True)
            builder.add_macro('HOOKER_CALLED', 1)

        if os.name == "nt":
            builder = CXXBuilder(nt_hooker=hooker)
        else:
            builder = CXXBuilder(posix_hooker=hooker)

        assert len(called) == 1
        assert ('HOOKER_CALLED', 1) in builder.macros

    def test_load_toml_static_method(self, temp_project_dir):
        """Test load_toml static method."""
        data = CXXBuilder.load_toml('pyproject.toml')
        assert data['project']['name'] == 'test-project'
        assert data['project']['version'] == '1.2.3'


class TestModiGCC:
    """Tests for ModiGCC class (only run on non-Windows)."""

    @pytest.mark.skipif(os.name == 'nt', reason="GCC tests only run on Unix-like systems")
    def test_init(self):
        """Test ModiGCC initialization."""
        modi = ModiGCC()
        assert isinstance(modi.libdir1, list)

    @pytest.mark.skipif(os.name == 'nt', reason="GCC tests only run on Unix-like systems")
    def test_pref_static_nonexistent(self):
        """Test pref_static falls back to -l flag for nonexistent lib."""
        modi = ModiGCC()
        result = modi.pref_static('nonexistent_lib_xyz')
        assert result == '-lnonexistent_lib_xyz'


class TestModiMSVC:
    """Tests for ModiMSVC class."""

    def test_init_method(self, temp_project_dir):
        """Test ModiMSVC init method."""
        modi = ModiMSVC()
        builder = CXXBuilder.__new__(CXXBuilder)
        builder.include_dirs = []
        builder.macros = []
        builder.extra_compile_args = []
        builder.extra_link_args = []
        builder.libdirs = []
        builder.sysver = "3.10"
        builder.name = "test"

        modi.init(builder)

        assert len(builder.macros) > 0
        assert len(builder.extra_compile_args) > 0


class TestImport:
    """Tests for module import."""

    def test_import_module(self):
        """Test that module can be imported."""
        import py_cxx_builder
        assert hasattr(py_cxx_builder, 'CXXBuilder')
        assert hasattr(py_cxx_builder, 'ModiGCC')
        assert hasattr(py_cxx_builder, 'ModiMSVC')
        assert hasattr(py_cxx_builder, '__version__')

    def test_import_classes(self):
        """Test that classes can be imported directly."""
        from py_cxx_builder import CXXBuilder, ModiGCC, ModiMSVC
        assert CXXBuilder is not None
        assert ModiGCC is not None
        assert ModiMSVC is not None

    def test_version(self):
        """Test version string."""
        from py_cxx_builder import __version__
        assert __version__ == "0.1.0"
