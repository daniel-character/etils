# Copyright 2021 The etils Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for tensorflow_datasets.core.utils.gpath."""

import os
import pathlib
import types

from etils import epath
import pytest
import tensorflow as tf

# TODO(epot): Remove TFDS dependency for tests
import tensorflow_datasets as tfds

_GCS_SCHEME = 'gs://'


@pytest.fixture
def gcs_mocked_path(tmp_path: pathlib.Path):
  """Fixture which patch the gfile API to redirect `gs://` calls."""
  prefix_path = os.fspath(tmp_path) + '/'

  def _norm_path(path: str):
    return path.replace(_GCS_SCHEME, prefix_path)

  gfile_fn_names = [
      'GFile',
      'copy',
      'exists',
      'glob',
      'isdir',
      'listdir',
      'makedirs',
      'mkdir',
      'remove',
      'rename',
      'rmtree',
      # 'stat',
      # 'walk',
  ]
  origin_gfile = types.SimpleNamespace(
      **{name: getattr(tf.io.gfile, name) for name in gfile_fn_names})
  with tfds.testing.mock_tf(
      'tf.io.gfile',
      GFile=lambda p, *args, **kwargs: origin_gfile.GFile(  # pylint: disable=g-long-lambda
          _norm_path(p), *args, **kwargs),
      copy=lambda p1, p2, **kwargs: origin_gfile.copy(  # pylint: disable=g-long-lambda
          _norm_path(p1), _norm_path(p2), **kwargs),
      exists=lambda p: origin_gfile.exists(_norm_path(p)),
      glob=lambda p: origin_gfile.glob(_norm_path(p)),
      isdir=lambda p: origin_gfile.isdir(_norm_path(p)),
      listdir=lambda p: origin_gfile.listdir(_norm_path(p)),
      makedirs=lambda p: origin_gfile.makedirs(_norm_path(p)),
      mkdir=lambda p: origin_gfile.mkdir(_norm_path(p)),
      remove=lambda p: origin_gfile.remove(_norm_path(p)),
      rename=lambda p1, p2, **kwargs: origin_gfile.rename(  # pylint: disable=g-long-lambda
          _norm_path(p1), _norm_path(p2), **kwargs),
      rmtree=lambda p: origin_gfile.rmtree(_norm_path(p)),
  ):
    yield tmp_path


def test_repr_gcs():
  path = epath.Path('gs://bucket/dir')
  assert isinstance(path, epath.Path)
  assert repr(path) == f'PosixGPath(\'{_GCS_SCHEME}bucket/dir\')'
  assert str(path) == f'{_GCS_SCHEME}bucket/dir'
  assert os.fspath(path) == f'{_GCS_SCHEME}bucket/dir'

  path = path.parent / 'some/other/file.json'
  assert isinstance(path, epath.Path)
  assert os.fspath(path) == f'{_GCS_SCHEME}bucket/some/other/file.json'

  path = epath.Path(path, 'other')
  assert isinstance(path, epath.Path)
  assert os.fspath(path) == f'{_GCS_SCHEME}bucket/some/other/file.json/other'


def test_repr_s3():
  path = epath.Path('s3://bucket/dir')
  assert isinstance(path, epath.Path)
  assert repr(path) == "PosixGPath('s3://bucket/dir')"
  assert str(path) == 's3://bucket/dir'
  assert os.fspath(path) == 's3://bucket/dir'

  path = path.parent / 'some/other/file.json'
  assert isinstance(path, epath.Path)
  assert os.fspath(path) == 's3://bucket/some/other/file.json'

  path = epath.Path(path, 'other')
  assert isinstance(path, epath.Path)
  assert os.fspath(path) == 's3://bucket/some/other/file.json/other'


def test_repr_windows():
  path = epath.gpath.WindowsGPath('C:\\Program Files\\Directory')
  assert isinstance(path, epath.gpath.WindowsGPath)
  assert str(path) == 'C:\\Program Files\\Directory'
  assert os.fspath(path) == 'C:\\Program Files\\Directory'

  path = path.parent / 'other/file.json'
  assert isinstance(path, epath.gpath.WindowsGPath)
  assert os.fspath(path) == 'C:\\Program Files\\other\\file.json'


@pytest.mark.parametrize(
    'parts',
    [
        (),  # No args
        ('.',),
        ('~',),
        ('relative/path',),
        ('/tmp/to/something',),
        (
            '/tmp/to',
            'something',
        ),
        (
            pathlib.Path('/tmp/to'),
            'something',
        ),
        ('~/to/something',),
    ],
)
def test_repr(parts):
  path = pathlib.Path(*parts)
  gpath = epath.Path(*parts)
  assert isinstance(gpath, epath.Path)
  assert str(gpath) == str(path)
  assert os.fspath(gpath) == os.fspath(path)

  assert gpath == path
  assert str(gpath.resolve()) == str(path.resolve())
  assert str(gpath.expanduser()) == str(path.expanduser())
  assert isinstance(gpath.resolve(), epath.Path)
  assert isinstance(gpath.expanduser(), epath.Path)


# pylint: disable=redefined-outer-name


def test_gcs(gcs_mocked_path: pathlib.Path):
  # mkdir()
  gpath = epath.Path(f'{_GCS_SCHEME}bucket/dir')
  gcs_mocked_path = gcs_mocked_path.joinpath('bucket/dir')
  assert not gpath.exists()
  gpath.mkdir(parents=True)

  # exists()
  assert gpath.exists()
  assert gcs_mocked_path.exists()

  # is_dir()
  assert gpath.is_dir()
  assert gcs_mocked_path.is_dir()

  gpath /= 'some_file.txt'
  gcs_mocked_path /= 'some_file.txt'

  # touch()
  assert not gpath.exists()
  gpath.touch()
  assert gpath.exists()
  assert gcs_mocked_path.exists()

  # is_file()
  assert gpath.is_file()
  assert gcs_mocked_path.is_file()

  # iterdir()
  gpath = gpath.parent
  gcs_mocked_path = gcs_mocked_path.parent
  assert list(gpath.iterdir()) == [
      epath.Path('gs://bucket/dir/some_file.txt'),
  ]

  assert isinstance(gpath, epath.Path)
  assert not isinstance(gcs_mocked_path, epath.Path)


def test_open(gcs_mocked_path: pathlib.Path):

  files = [
      'foo.py', 'bar.py', 'foo_bar.py', 'dataset.json', 'dataset_info.json',
      'readme.md'
  ]
  dataset_path = epath.Path('gs://bucket/dataset')

  dataset_path.mkdir(parents=True)
  assert dataset_path.exists()

  with pytest.raises(ValueError, match='Only UTF-8 encoding supported.'):
    dataset_path.open('w', encoding='latin-1')

  # open()
  for file in files:
    with dataset_path.joinpath(file).open('w') as f:
      f.write(' ')

  # encoding argument
  with dataset_path.joinpath('foo.py').open('r', encoding='UTF-8') as f:
    f.read()

  # iterdir()
  assert len(list(gcs_mocked_path.joinpath('bucket/dataset').iterdir())) == 6


@pytest.mark.usefixtures('gcs_mocked_path')
def test_touch():
  root_path = epath.Path('gs://bucket/')
  root_path.mkdir(parents=True)
  assert root_path.exists()

  # File don't exists, touch create it
  file_path = root_path / 'test.txt'
  assert not file_path.exists()
  file_path.touch()
  assert file_path.exists()
  assert file_path.read_text() == ''  # File content is empty  # pylint: disable=g-explicit-bool-comparison

  file_path.write_text('Some content')
  file_path.touch()  # Should be a no-op
  assert file_path.read_text() == 'Some content'  # Content still exists

  with pytest.raises(FileExistsError):
    file_path.touch(exist_ok=False)


@pytest.mark.usefixtures('gcs_mocked_path')
def test_read_write():

  gpath = epath.Path('gs://file.txt')

  with gpath.open('w') as f:
    f.write('abcd')

  with gpath.open('r') as f:
    assert f.read() == 'abcd'

  gpath.write_text('def')
  assert gpath.read_text() == 'def'

  with gpath.open('wb') as f:
    f.write(b'ghi')

  with gpath.open('rb') as f:
    assert f.read() == b'ghi'

  gpath.write_bytes(b'def')
  assert gpath.read_bytes() == b'def'


@pytest.mark.usefixtures('gcs_mocked_path')
def test_unlink():
  path = epath.Path('gs://bucket')
  path.mkdir()

  path = path / 'text.txt'

  with pytest.raises(FileNotFoundError):
    path.unlink()

  path.unlink(missing_ok=True)  # no-op if missing_ok=True

  path.touch()  # Path created
  assert path.exists()
  path.unlink()  # Path deleted
  assert not path.exists()


def test_mkdir(gcs_mocked_path: pathlib.Path):
  g_path = epath.Path('gs://bucket')
  assert not g_path.exists()

  g_path.mkdir()
  assert g_path.exists()

  with pytest.raises(FileExistsError, match='already exists'):
    g_path.mkdir()

  assert gcs_mocked_path.joinpath('bucket').exists()


def test_rename(gcs_mocked_path: pathlib.Path):
  src_path = epath.Path('gs://foo.py')
  src_path.write_text(' ')

  assert gcs_mocked_path.joinpath('foo.py').exists()

  src_path.rename('gs://bar.py')

  assert not gcs_mocked_path.joinpath('foo.py').exists()
  assert gcs_mocked_path.joinpath('bar.py').exists()

  file_name = lambda l: l.name
  assert sorted(list(map(file_name, gcs_mocked_path.iterdir()))) == ['bar.py']


def test_replace(tmp_path: pathlib.Path):

  file_path = epath.Path(os.path.join(tmp_path, 'tfds.py'))
  file_path.write_text('tfds')

  file_path.replace(os.path.join(tmp_path, 'tfds-dataset.py'))

  assert not tmp_path.joinpath('tfds.py').exists()
  assert tmp_path.joinpath('tfds-dataset.py').exists()
  assert tmp_path.joinpath('tfds-dataset.py').read_text() == 'tfds'

  mnist_path = epath.Path(tmp_path / 'mnist.py')
  mnist_path.write_text('mnist')

  mnist_path.replace(tmp_path / 'mnist-100.py')

  assert not tmp_path.joinpath('mnist.py').exists()
  assert tmp_path.joinpath('mnist-100.py').exists()
  assert tmp_path.joinpath('mnist-100.py').read_text() == 'mnist'

  assert len(list(tmp_path.iterdir())) == 2

  assert sorted(epath.Path(tmp_path).iterdir()) == [
      tmp_path / 'mnist-100.py', tmp_path / 'tfds-dataset.py'
  ]


@pytest.mark.usefixtures('gcs_mocked_path')
def test_copy():
  src_path = epath.Path('gs://foo.py')
  src_path.write_text('abc')

  assert not src_path.parent.joinpath('bar.py').exists()
  assert not src_path.parent.joinpath('bar2.py').exists()

  src_path.copy('gs://bar.py')
  src_path.copy(epath.Path('gs://bar2.py'))

  assert src_path.exists()
  assert src_path.parent.joinpath('bar.py').read_text() == 'abc'
  assert src_path.parent.joinpath('bar2.py').read_text() == 'abc'


def test_format():
  template_path = epath.Path('/home/{user}/foo.py')
  template_path = template_path.format(user='adibou')
  assert template_path == epath.Path('/home/adibou/foo.py')


def test_default():
  path = epath.Path()
  assert isinstance(path, epath.Path)
  assert os.fspath(path) == '.'
  assert path == epath.Path('.')

  path = epath.Path('a/x', 'y', 'z')
  assert isinstance(path, epath.Path)
  assert os.fspath(path) == 'a/x/y/z'
  assert path == epath.Path('a/x/y/z')