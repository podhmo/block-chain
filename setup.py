from setuptools import setup, find_packages
requires = [
    ]
test_requires =[
    "pytest"
]

from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        import pytest
        pytest.main(self.test_args)

setup(name='block.chain',
      version='0.0.0',
      description='fmm..',
      long_description="", 
      author='podhmo',
      package_dir={'': '.'},
      packages=find_packages('.'),
      namespace_packages=["block"],
      install_requires = requires,
      cmdclass = {'test': PyTest},
      tests_require=["pytest"],
      extras_require = {
        "testing": test_requires
      },
      entry_points = """
      """,
      )



