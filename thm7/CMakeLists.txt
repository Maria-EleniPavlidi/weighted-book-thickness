# set to your OGDF directory
list(APPEND CMAKE_PREFIX_PATH "/opt/local/OGDF")

project ( wbt )
cmake_minimum_required(VERSION 3.1...3.23)
set(CMAKE_VERBOSE_MAKEFILE ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_BUILD_TYPE Release)

find_package(OGDF REQUIRED)
 
add_executable(plagen plagen.cpp)
target_link_libraries(plagen OGDF)
