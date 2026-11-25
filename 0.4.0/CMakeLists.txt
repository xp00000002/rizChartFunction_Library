cmake_minimum_required(VERSION 3.15)
project(rizchart_native LANGUAGES NONE)

option(RIZCHART_BUILD_NATIVE "Build the optional C++ acceleration module" ON)
if(DEFINED ENV{RIZCHART_BUILD_NATIVE})
    set(
        RIZCHART_BUILD_NATIVE
        "$ENV{RIZCHART_BUILD_NATIVE}"
        CACHE BOOL "Build the optional C++ acceleration module" FORCE
    )
endif()

if(NOT RIZCHART_BUILD_NATIVE)
    message(STATUS "rizChartFunction: optional native acceleration disabled")
else()
    enable_language(CXX)
    set(CMAKE_CXX_STANDARD 17)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
    set(CMAKE_CXX_EXTENSIONS OFF)

    find_package(pybind11 CONFIG REQUIRED)

    pybind11_add_module(_rizchart_native MODULE cpp/src/rizchart_native.cpp)
    target_compile_features(_rizchart_native PRIVATE cxx_std_17)

    install(
        TARGETS _rizchart_native
        LIBRARY DESTINATION rizChartFunction
        RUNTIME DESTINATION rizChartFunction
    )
endif()
