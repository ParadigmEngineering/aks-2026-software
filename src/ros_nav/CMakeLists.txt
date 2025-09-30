cmake_minimum_required(VERSION 3.5)
project(ros_nav)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(ament_index_cpp REQUIRED) # Added ament_index_cpp
find_package(mavros_msgs REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Widgets Core WebEngineWidgets)

# Add executable
add_executable(waypoint src/path_publisher.cpp)
ament_target_dependencies(waypoint 
  rclcpp 
  std_msgs 
  geometry_msgs # If geometry_msgs is used
  ament_index_cpp # Added ament_index_cpp
  sensor_msgs
  mavros_msgs
  tf2_geometry_msgs
)

# Add executable
add_executable(topic_data src/topic_data.cpp)
ament_target_dependencies(topic_data
  rclcpp 
  std_msgs 
  geometry_msgs # If geometry_msgs is used
  ament_index_cpp # Added ament_index_cpp
  sensor_msgs
  mavros_msgs
)

# Add executable
add_executable(topicsUI src/topicsUI.cpp)
ament_target_dependencies(topicsUI
  rclcpp 
  std_msgs 
  geometry_msgs # If geometry_msgs is used
  ament_index_cpp # Added ament_index_cpp
  sensor_msgs
  mavros_msgs
)

# Install data directory
install(DIRECTORY data/
  DESTINATION share/${PROJECT_NAME}/data
)

include_directories(
  include
  ${Qt5Widgets_INCLUDE_DIRS}
)

# Link libraries using modern CMake syntax
target_link_libraries(topicsUI
  Qt5::Widgets
  Qt5::Core
  Qt5::WebEngineWidgets
  rclcpp::rclcpp
  mavros_msgs::mavros_msgs__rosidl_generator_cpp
  mavros_msgs::mavros_msgs__rosidl_typesupport_cpp
)

# Install the executable
install(TARGETS
  waypoint
  topic_data
  topicsUI
  DESTINATION lib/${PROJECT_NAME}
)


# Enable testing
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # Uncomment the line if copyright/license check is not required
  # set(ament_cmake_copyright_FOUND TRUE)
  # Uncomment the line if not in a git repo
  # set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
