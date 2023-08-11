# CMake 最低版本号要求
cmake_minimum_required (VERSION 3.5)

# 项目信息
set(PluginFileName "keyReducer")
project(keyReducer LANGUAGES CXX VERSION 1.0 DESCRIPTION "Maya Key reducer")

# 设置输出路径
set(EXECUTABLE_OUTPUT_PATH "${PROJECT_SOURCE_DIR}/plug-ins/$ENV{MayaVersion}")
set(LIBRARY_OUTPUT_PATH "${PROJECT_SOURCE_DIR}/plug-ins/$ENV{MayaVersion}")

# 设置Maya文件目录
set(MAYA_PATH "$ENV{AutodeskDirPath}/Maya$ENV{MayaVersion}")
set(MAYA_HEAD "${MAYA_PATH}/include/")
set(MAYA_LIBRARY_DIR "${MAYA_PATH}/lib")
set(PLUGIN_HEAD "${PROJECT_SOURCE_DIR}/include")

message(WARNING "Start build project" ...)

# 查找source目录下的所有*.cpp,*.c源文件,并将文件列表保存到 SRC_DIR_LIST 变量
file(GLOB_RECURSE SRC_DIR_LIST "${PROJECT_SOURCE_DIR}/source/*.cpp" "${PROJECT_SOURCE_DIR}/source/*.c" "${PROJECT_SOURCE_DIR}/include/*.h" "${PROJECT_SOURCE_DIR}/include/*.hpp")

#添加同文件路径
include_directories(
        ${MAYA_HEAD}
        ${PLUGIN_HEAD}
)

# 查找Lib文件
foreach(MAYA_LIB_NAME OpenMaya OpenMayaAnim OpenMayaFX OpenMayaRender OpenMayaUI Foundation tbb)
	find_library(MAYA_${MAYA_LIB_NAME}_LIBRARY NAMES ${MAYA_LIB_NAME} PATHS ${MAYA_LIBRARY_DIR} NO_DEFAULT_PATH)
	set(MAYA_LIBRARIES ${MAYA_LIBRARIES} ${MAYA_${MAYA_LIB_NAME}_LIBRARY}) #append a lib to MAYA_LIBRARIES list
endforeach()

#将SRC_DIR_LIST中文件列表以静态库的方式加入工程
add_library(${PROJECT_NAME} SHARED ${SRC_DIR_LIST})


#添加链接目录
target_link_directories(${PROJECT_NAME} PUBLIC ${MAYA_LIBRARY_DIR})
target_link_libraries(${PROJECT_NAME} ${MAYA_LIBRARIES})

set_target_properties(
    ${PROJECT_NAME}
    PROPERTIES
        OUTPUT_NAME ${PluginFileName}
        SUFFIX ".mll"
)