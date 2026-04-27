# AKS Software 2026

**Paradigm Engineering - Software Team**

## About

This is the main repo for ROS2 code that digests and processes sensor data for autonomous kart control. This repository uses [Humble-Hawksbill](https://docs.ros.org/en/humble/index.html) (Ubuntu 22.0) configured for the SeeedStudio Jetson.

This repository also contains the code for training the line-detection computer vision model under the `computer_vision` subdirectory. For more information, see the dedicated README.

## Installation

These instructions are for installing the core ROS2 software for autonomous control of the kart. They have been tested on Ubuntu 22 on a dev device and on the Jetson. Windows installs may differ.

For instructions on installing the Computer Vision training and lane detection code, see the dedicated README.

x. clone repo (ssh keys recommended)
x. install ros
x. Get zed-ros2 submodules

```bash
git submodule update --init --recursive
```
x. install dependencies
```bash
rosdep install --from-paths src --ignore-src -r -y
```
x. build
```bash
colcon build
```

## Updates

_coming soon_

## Useful Resources

_coming soon_