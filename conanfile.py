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
    settings = "os", "compiler", "build_type", "arch", "arch_build"
    generators = "cmake", "cmake_find_package"
    requires = "eigen/3.3.7@conan/stable" ,"glog/0.4.0@bincrafters/stable", "gflags/2.2.2@bincrafters/stable"
    build_policy    = 'missing'
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
        "verbose"               : [True, False],
        "march"                 : "ANY",
        "eigen_malloc_already_aligned"  : "ANY",
        "eigen_max_align_bytes"         : "ANY",
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
        "verbose"               : False,
        "march"                 : None,
        "eigen_malloc_already_aligned"  : None,
        "eigen_max_align_bytes"         : None,
    }

    _cmake = None
    @property
    def _source_subfolder(self):
        return "source_subfolder"
    @property
    def _build_subfolder(self):
        return "build_subfolder"

    def requirements(self):
        if self.options.blas == "OpenBLAS":
            self.requires("openblas/0.3.10")

    def configure(self):
        if self.settings.compiler == 'Visual Studio':
            del self.options.fPIC
        if self.options.blas == "MKL":
            self.options.blas = "Intel10_64lp"
        if self.options.blas == "OpenBLAS":
            # Override default of openblas
            self.options["openblas"].build_lapack   = True

    def _configure_cmake(self):
        if not self._cmake:
            self._cmake = CMake(self)

            valid_ext = []
            if self.options.shared:
                valid_ext = ['.so', '.dll', '.dylib']
            else:
                valid_ext = ['.a', '.lib']

            # Collect roots for all dependencies, as these usually contain
            # the Find???.cmake modules ceres looks for, e.g. glog, gflags and eigen.
            module_paths = []
            for dep in self.deps_cpp_info.deps:
                module_paths.append(self.deps_cpp_info[dep].rootpath)
            module_paths = ';'.join(str(x) for x in module_paths)

            # The ceres build process will only honor the standard set in CMAKE_CXX_STANDARD
            if self.settings.compiler.cppstd:
                print(
                    "Conan setting ceres-solver build option CMAKE_CXX_STANDARD=" + str(self.settings.compiler.cppstd))
                self._cmake.definitions["CMAKE_CXX_STANDARD"] = self.settings.compiler.cppstd
            elif self._cmake.definitions["CONAN_CMAKE_CXX_STANDARD"]:
                print("Conan setting ceres-solver build option CMAKE_CXX_STANDARD=" + str(
                    self._cmake.definitions["CONAN_CMAKE_CXX_STANDARD"]))
                self._cmake.definitions["CMAKE_CXX_STANDARD"] = self._cmake.definitions["CONAN_CMAKE_CXX_STANDARD"]

            self._cmake.definitions['CMAKE_FIND_PACKAGE_NO_PACKAGE_REGISTRY'] = True
            self._cmake.definitions['CMAKE_FIND_PACKAGE_NO_SYSTEM_PACKAGE_REGISTRY'] = True
            self._cmake.definitions['CMAKE_VERBOSE_MAKEFILE'] = self.options.verbose
            self._cmake.definitions["BUILD_EXAMPLES"] = self.options.examples
            self._cmake.definitions["BUILD_TESTING"] = self.options.tests
            self._cmake.definitions["BUILD_BENCHMARKS"] = self.options.benchmarks
            self._cmake.definitions["BUILD_DOCUMENTATION"] = self.options.documentation
            self._cmake.definitions["MINIGLOG"] = self.options.miniglog
            self._cmake.definitions["GFLAGS"] = self.options.gflags
            self._cmake.definitions["LAPACK"] = self.options.lapack
            self._cmake.definitions["CUSTOM_BLAS"] = self.options.custom_blas
            self._cmake.definitions["EIGENSPARSE"] = self.options.eigensparse
            self._cmake.definitions["SUITESPARSE"] = self.options.suitesparse
            self._cmake.definitions["ACCELERATESPARSE"] = self.options.acceleratesparese
            self._cmake.definitions["CXSPARSE"] = self.options.cxsparse
            self._cmake.definitions["SCHUR_SPECIALIZATIONS"] = self.options.schur
            self._cmake.definitions['CMAKE_MODULE_PATH'] = module_paths
            self._cmake.definitions['CMAKE_PREFIX_PATH'] = module_paths
            self._cmake.definitions['EIGEN3_INCLUDE_DIR'] = self.deps_cpp_info['eigen'].include_paths[0]
            self._cmake.definitions["BLA_PREFER_PKGCONFIG"] = self.options.blas_prefer_pkgconfig
            self._cmake.definitions["BLA_STATIC"] = not self.options.shared
            if not self.options.blas_libraries:
                self._cmake.definitions["BLA_VENDOR"] = self.options.blas

            # Set extra compiler flags for architecture and alignment
            CXXFLAGS = ""
            if self.options.march:
                CXXFLAGS = CXXFLAGS + "-march=" + str(self.options.march)
            if self.options.eigen_malloc_already_aligned:
                CXXFLAGS = CXXFLAGS + " -DEIGEN_MALLOC_ALREADY_ALIGNED=" + str(
                    self.options.eigen_malloc_already_aligned)
            if self.options.eigen_max_align_bytes:
                CXXFLAGS = CXXFLAGS + " -DEIGEN_MAX_ALIGN_BYTES=" + str(self.options.eigen_max_align_bytes)
            if CXXFLAGS:
                self._cmake.definitions["CMAKE_CXX_FLAGS_INIT"] = CXXFLAGS


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

                openblas_libs = ';'.join(str(x) for x in openblas_libs)
                self._cmake.definitions["BLAS_LIBRARIES"] = openblas_libs
                self._cmake.definitions["LAPACK_LIBRARIES"] = openblas_libs
            # Or override if manually specified
            if self.options.blas_libraries:
                self._cmake.definitions["BLAS_LIBRARIES"] = self.options.blas_libraries
            if self.options.lapack_libraries:
                self._cmake.definitions["LAPACK_LIBRARIES"] = self.options.lapack_libraries
            self._cmake.configure(source_folder=self._source_subfolder)
        return self._cmake

    def source(self):
        git = tools.Git(folder=self._source_subfolder)
        git.clone("https://github.com/ceres-solver/ceres-solver.git")
        #git.checkout("edb8322bdabef336db290be1cc557145b6d4bf80") # <-Works!
        # git.checkout("8c36bcc81fbd4f78a2faa2c914ef40af264f4c31") # <- 27 april 2020
        # git.checkout("e39d9ed1d60dfeb58dd2a0df4622c683f87b28e3") # <- 18 june 2020
        git.checkout("79bbf95103672fa4b5485e055ff7692ee4a1f9da") # <- 4 august 2020 (2.0.0 rc1)
        # Patch to find Eigen3 properly
        tools.patch(base_path=self._source_subfolder, patch_file="ceres-solver.patch")

    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    def test(self):
        if self.options.tests:
            cmake = self._configure_cmake()
            cmake.build()
            cmake.test()

    def package(self):
        cmake = self._configure_cmake()
        cmake.install()
        self.copy("LICENSE", src=self._source_subfolder, dst="licenses")
        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.names["cmake_find_package"] = "ceres"
        self.cpp_info.names["cmake_find_package_multi"] = "ceres"
        if os.path.isdir(self.cpp_info.rootpath + "/lib64"):
            self.cpp_info.libdirs.append("lib64")
        self.cpp_info.libs = tools.collect_libs(self)
        if not self.cpp_info.libs:
            raise Exception("No libs collected")
