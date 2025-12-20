#!/usr/bin/env python
# coding:utf8
"""Unit tests for py_cxx_builder module."""

import os
import sys
import tempfile
import pytest

from py_cxx_builder import CXXBuilder, ModiGCC, ModiMSVC


class TestCXXBuilder:
    """Tests for CXXBuilder class."""

    def test_init(self):
        """Test CXXBuilder initialization."""
        builder = CXXBuilder()
        assert builder.include_dirs == [] or isinstance(builder.include_dirs, list)
        assert builder.libdirs == [] or isinstance(builder.libdirs, list)
        assert isinstance(builder.macros, list)
        assert isinstance(builder.libs, list)
        assert isinstance(builder.extra_compile_args, list)
        assert isinstance(builder.extra_link_args, list)
        assert isinstance(builder.files, dict)
        assert builder.mainsrc is None

    def test_is_win_detection(self):
        """Test platform detection."""
        builder = CXXBuilder()
        assert builder.is_win == (os.name == "nt")

    def test_modi_selection(self):
        """Test correct modifier class is selected based on platform."""
        builder = CXXBuilder()
        if os.name == "nt":
            assert isinstance(builder.modi, ModiMSVC)
        else:
            assert isinstance(builder.modi, ModiGCC)

    def test_add_macro_with_value(self):
        """Test adding macro with explicit value."""
        builder = CXXBuilder()
        initial_count = len(builder.macros)
        builder.add_macro('TEST_MACRO', 42)
        assert len(builder.macros) == initial_count + 1
        assert ('TEST_MACRO', 42) in builder.macros

    def test_add_macro_without_value(self):
        """Test adding macro without value defaults to 1."""
        builder = CXXBuilder()
        initial_count = len(builder.macros)
        builder.add_macro('ENABLE_FEATURE')
        assert len(builder.macros) == initial_count + 1
        assert ('ENABLE_FEATURE', 1) in builder.macros

    def test_add_files(self):
        """Test adding source files."""
        builder = CXXBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_file = os.path.join(tmpdir, 'test.cpp')
            with open(test_file, 'w') as f:
                f.write('int main() { return 0; }')

            builder.add_files([test_file])
            assert test_file in builder.files

    def test_add_files_with_directory(self):
        """Test adding source files with directory prefix."""
        builder = CXXBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = 'test.cpp'
            full_path = os.path.join(tmpdir, test_file)
            with open(full_path, 'w') as f:
                f.write('int main() { return 0; }')

            builder.add_files([test_file], directory=tmpdir)
            assert os.path.abspath(full_path) in builder.files

    def test_add_files_empty_string_ignored(self):
        """Test that empty strings in file list are ignored."""
        builder = CXXBuilder()
        initial_count = len(builder.files)
        builder.add_files(['', None] if None else [''])
        assert len(builder.files) == initial_count

    def test_remove_files(self):
        """Test removing source files."""
        builder = CXXBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and add test file
            test_file = os.path.join(tmpdir, 'test.cpp')
            with open(test_file, 'w') as f:
                f.write('int main() { return 0; }')

            builder.add_files([test_file])
            assert test_file in builder.files

            builder.remove_files([test_file])
            assert test_file not in builder.files

    def test_remove_nonexistent_file(self):
        """Test removing a file that was never added."""
        builder = CXXBuilder()
        # Should not raise any exception
        builder.remove_files(['/nonexistent/file.cpp'])

    def test_set_main_file(self):
        """Test setting the main source file."""
        builder = CXXBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            main_file = os.path.join(tmpdir, 'main.cpp')
            with open(main_file, 'w') as f:
                f.write('int main() { return 0; }')

            builder.set_main_file(main_file)
            assert builder.mainsrc == main_file
            assert builder._need_test_link is False

    def test_set_main_file_with_test_linker(self):
        """Test setting main file that contains TEST_LINKER."""
        builder = CXXBuilder()
        with tempfile.TemporaryDirectory() as tmpdir:
            main_file = os.path.join(tmpdir, 'main.cpp')
            with open(main_file, 'w') as f:
                f.write('#ifdef TEST_LINKER\nint main() { return 0; }\n#endif')

            builder.set_main_file(main_file)
            assert builder._need_test_link is True

    def test_sysver_format(self):
        """Test system version string format."""
        builder = CXXBuilder()
        expected = f"{sys.version_info[0]}.{sys.version_info[1]}"
        assert builder.sysver == expected


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

    def test_init_method(self):
        """Test ModiMSVC init method."""
        modi = ModiMSVC()
        builder = CXXBuilder.__new__(CXXBuilder)
        builder.include_dirs = []
        builder.macros = []
        builder.extra_compile_args = []
        builder.extra_link_args = []
        builder.libdirs = []
        builder.sysver = "3.10"

        modi.init(builder)

        assert len(builder.include_dirs) > 0
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

    def test_import_classes(self):
        """Test that classes can be imported directly."""
        from py_cxx_builder import CXXBuilder, ModiGCC, ModiMSVC
        assert CXXBuilder is not None
        assert ModiGCC is not None
        assert ModiMSVC is not None
