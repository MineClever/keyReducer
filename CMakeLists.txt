cmake_minimum_required(VERSION 3.12)
project(keyReducer LANGUAGES CXX VERSION 1.0 DESCRIPTION "Maya Key reducer")

# Match boneDynamicsNode: use the selected SDK's official plugin build helpers.
if(NOT EXISTS "$ENV{DEVKIT_LOCATION}/cmake/pluginEntry.cmake")
    message(FATAL_ERROR "Set DEVKIT_LOCATION to a Maya devkitBase directory containing cmake/pluginEntry.cmake")
endif()
include("$ENV{DEVKIT_LOCATION}/cmake/pluginEntry.cmake")

set(SOURCE_FILES
    source/PluginMain.cpp
    source/keyReducerCmd.cpp
    source/restoreKeys.cpp
    include/keyReducerCmd.h
    include/restoreKeys.h
)
set(INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/include")
set(LIBRARIES OpenMaya OpenMayaAnim Foundation)
# The same build folder can switch between Devkit and installed Maya libraries.
# SDK helpers cache find_library results, so resolve them again on configure.
foreach(MAYA_LIBRARY IN LISTS LIBRARIES)
    unset(${MAYA_LIBRARY}_PATH CACHE)
endforeach()
build_plugin()

if(NOT DEFINED CXX_STANDARD_VER OR CXX_STANDARD_VER STREQUAL "")
    set(CXX_STANDARD_VER 17)
endif()
set_target_properties(${PROJECT_NAME} PROPERTIES
    CXX_STANDARD ${CXX_STANDARD_VER}
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
if(MSVC)
    target_compile_options(${PROJECT_NAME} PRIVATE /permissive- /Zc:__cplusplus /utf-8)
endif()
