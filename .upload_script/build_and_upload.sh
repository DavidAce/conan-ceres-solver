#!/bin/bash

conan create . davidace/stable --profile=dmrg --build=missing
conan upload ceres-solver/2.0.0@davidace/stable  -r conan-dmrg --all

#conan create . conan-dmrg/stable --profile=dmrg --build=missing
#conan upload ceres-solver/1.14.0@conan-dmrg/stable  -r conan-dmrg --all
