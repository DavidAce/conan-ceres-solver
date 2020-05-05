from conans import ConanFile, CMake, tools, __version__ as conan_version
from conans.model.version import Version
from conans.client.build.cppstd_flags import cppstd_default

from conans.tools import download, unzip
import os, re

class CeresSolver(ConanFile):
    name = "ceres-solver"
    version = "2.0.0"
    license = "New BSD"
    url = "https://github.com/ceres-solver/ceres-solver"
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"
    requires = "eigen/3.3.7@conan/stable" ,"glog/0.4.0@bincrafters/stable", "gflags/2.2.2@bincrafters/stable"
    build_policy    = 'missing'
    #exports_sources = ["ceres-solver.patch", "FindEigen3.cmake"]
    exports_sources = ["ceres-solver.patch"]
    options         = {
        "fPIC"                  : [True, False],
        "shared"                : [True, False],
        "examples"              : [True, False],
        "tests"                 : [True, False],
        "benchmarks"            : [True, False],
        "documentation"         : [True, False],
        "miniglog"              : [True, False],
        "gflags"                : [True, False],
        "lapack"                : [True, False],
        "custom_blas"           : [True, False],
        "eigensparse"           : [True, False],
        "suitesparse"           : [True, False],
        "acceleratesparese"     : [True, False],
        "cxsparse"              : [True, False],
        "schur"                 : [True, False],
        "blas_prefer_pkgconfig" : [True, False],
        "blas"                  : ['OpenBLAS', 'MKL', 'Intel', 'Intel10_64lp', 'Intel10_64lp_seq', 'Intel10_64ilp',
                                    'Intel10_64lp_seq', 'FLAME', 'Goto', 'ATLAS PhiPACK', 'Generic', 'All'],
        "blas_libraries"        : "ANY",
        "lapack_libraries"      : "ANY",
    }
    default_options = {
        "fPIC"                  : True,
        "shared"                : False,
        "examples"              : False,
        "tests"                 : False,
        "benchmarks"            : False,
        "documentation"         : False,
        "miniglog"              : False,
        "gflags"                : True,
        "lapack"                : True,
        "custom_blas"           : True,
        "eigensparse"           : True,
        "suitesparse"           : False,
        "acceleratesparese"     : False,
        "cxsparse"              : False,
        "schur"                 : False,
        "blas_prefer_pkgconfig" : False,
        "blas"                  : "OpenBLAS",
        "blas_libraries"        : None,
        "lapack_libraries"      : None,
    }

    _source_subfolder = "ceres-solver-"+version
    _build_subfolder  = "ceres-solver-"+version

    def requirements(self):
        if self.options.blas == "OpenBLAS":
            self.requires("openblas/0.3.7")

    def configure(self):
        if self.settings.compiler == 'Visual Studio':
            del self.options.fPIC
        if self.options.blas == "MKL":
            self.options.blas = "Intel10_64lp"
        if self.options.blas == "OpenBLAS":
            # Override default of openblas
            self.options["openblas"].build_lapack   = True

    def source(self):
        git = tools.Git(folder=self._source_subfolder)
        git.clone("https://github.com/ceres-solver/ceres-solver.git")
        #git.checkout("edb8322bdabef336db290be1cc557145b6d4bf80") # <-Works!
        git.checkout("8c36bcc81fbd4f78a2faa2c914ef40af264f4c31") # <- 27 april 2020

    def build(self):
        # Patch to find Eigen3 properly
        tools.patch(base_path=self._build_subfolder, patch_file="ceres-solver.patch")
        valid_ext = []
        if self.options.shared:
            valid_ext = ['.so', '.dll', '.dylib']
        else:
            valid_ext = ['.a', '.lib']

        # Collect roots for all dependencies, as these usually contain
        # the Find???.cmake modules ceres looks for, for instane to find
        # glog, gflags and eigen.
        module_paths = []
        for dep in self.deps_cpp_info.deps:
            module_paths.append(self.deps_cpp_info[dep].rootpath)
        module_paths = ';'.join(str(x) for x in module_paths)

        cmake = CMake(self)
        cmake.definitions['CMAKE_FIND_PACKAGE_NO_PACKAGE_REGISTRY']         = True
        cmake.definitions['CMAKE_FIND_PACKAGE_NO_SYSTEM_PACKAGE_REGISTRY']  = True
        cmake.definitions["BUILD_EXAMPLES"]                     = self.options.examples
        cmake.definitions["BUILD_TESTING"]                      = self.options.tests
        cmake.definitions["BUILD_BENCHMARKS"]                   = self.options.benchmarks
        cmake.definitions["BUILD_DOCUMENTATION"]                = self.options.documentation
        cmake.definitions["MINIGLOG"]                           = self.options.miniglog
        cmake.definitions["GFLAGS"]                             = self.options.gflags
        cmake.definitions["LAPACK"]                             = self.options.lapack
        cmake.definitions["CUSTOM_BLAS"]                        = self.options.custom_blas
        cmake.definitions["EIGENSPARSE"]                        = self.options.eigensparse
        cmake.definitions["SUITESPARSE"]                        = self.options.suitesparse
        cmake.definitions["ACCELERATESPARSE"]                   = self.options.acceleratesparese
        cmake.definitions["CXSPARSE"]                           = self.options.cxsparse
        cmake.definitions["SCHUR_SPECIALIZATIONS"]              = self.options.schur
        cmake.definitions['CMAKE_MODULE_PATH']                  = module_paths
        cmake.definitions['CMAKE_PREFIX_PATH']                  = module_paths
        cmake.definitions['EIGEN3_INCLUDE_DIR']                 = self.deps_cpp_info['eigen'].include_paths[0]
        cmake.definitions["BLA_PREFER_PKGCONFIG"]               = self.options.blas_prefer_pkgconfig
        cmake.definitions["BLA_STATIC"]                         = not self.options.shared
        if not self.options.blas_libraries:
            cmake.definitions["BLA_VENDOR"]                     = self.options.blas


        # Find the openblas library
        if self.options.blas == "OpenBLAS":
            openblas_libs = []
            for path in self.deps_cpp_info["openblas"].lib_paths:
                for file in os.listdir(path):
                    if "openblas" in file and any(file.endswith(ext) for ext in valid_ext):
                        openblas_libs.append(path + '/' + file)
            if not openblas_libs:
                raise ValueError("Could not find any openblas libraries")
            for lib in self.deps_cpp_info["openblas"].system_libs:
                openblas_libs.append(lib)

            openblas_libs=';'.join(str(x) for x in openblas_libs)
            cmake.definitions["BLAS_LIBRARIES"]     = openblas_libs
            cmake.definitions["LAPACK_LIBRARIES"]   = openblas_libs
        # Or override if manually specified
        if self.options.blas_libraries:
            cmake.definitions["BLAS_LIBRARIES"]     = self.options.blas_libraries
        if self.options.lapack_libraries:
            cmake.definitions["LAPACK_LIBRARIES"]   = self.options.lapack_libraries

        cmake.configure(source_folder=self._build_subfolder)
        cmake.build()
        cmake.install()

    def package_info(self):
        if os.path.isdir(self.cpp_info.rootpath + "/lib64"):
            self.cpp_info.libdirs.append("lib64")
        self.cpp_info.libs = tools.collect_libs(self)
        if not self.cpp_info.libs:
            raise Exception("No libs collected")
