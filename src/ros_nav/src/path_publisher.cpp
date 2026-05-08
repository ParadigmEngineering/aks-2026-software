#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/nav_sat_fix.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "mavros_msgs/srv/set_mode.hpp"
#include "ament_index_cpp/get_package_share_directory.hpp"
#include "geographic_msgs/msg/geo_pose_stamped.hpp"
#include "geometry_msgs/msg/point.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"
#include <fstream>
#include <vector>
#include <iostream>
#include <cmath>

using namespace std;
using namespace std::chrono_literals;
using std::placeholders::_1;

// This doesn't have seek
// The other file does with me trying to also make a testing routine for it

class WaypointPublisher : public rclcpp::Node
{
public:
    WaypointPublisher() : Node("waypoint_publisher")
    {
        get_coords();

        waypoint_publisher_ =
            this->create_publisher<geographic_msgs::msg::GeoPoseStamped>(
                "/mavros/setpoint_position/global", 10);

        waypoint_timer_ =
            this->create_wall_timer(300ms, std::bind(&WaypointPublisher::step_sim, this));

        // open logs
        lat_file_.open("lat_log.txt");
        lon_file_.open("lon_log.txt");
    }

private:
    // =========================
    // SIM STATE
    // =========================
    double sim_x_ = 0.0;
    double sim_y_ = 0.0;
    double sim_vx_ = 0.0;
    double sim_vy_ = 0.0;
    double sim_heading_ = 0.0;

    const double dt_ = 0.3;
    const double meters_per_degree_ = 111000.0;

    const double origin_latitude_ = 40.437688;
    const double origin_longitude_ = -86.944469;

    const double max_speed_ = 16.67; // 60 km/h
    const double friction_ = 1.0;

    const double mass_kg_ = 300.0 * 0.453592;

    // =========================
    // LOG FILES
    // =========================
    ofstream lat_file_;
    ofstream lon_file_;

    // =========================
    // WAYPOINTS
    // =========================
    vector<double> latitude_vec;
    vector<double> longitude_vec;

    int counter = 0;

    double waypoint_x_ = 0.0;
    double waypoint_y_ = 0.0;

    // =========================
    // UTIL
    // =========================
    double clamp(double v, double a, double b)
    {
        return std::max(a, std::min(b, v));
    }

    double normalize_angle(double a)
    {
        while (a > M_PI) a -= 2 * M_PI;
        while (a < -M_PI) a += 2 * M_PI;
        return a;
    }

    int map_linear(double v, double in_min, double in_max, int out_min, int out_max)
    {
        double t = (v - in_min) / (in_max - in_min);
        return out_min + t * (out_max - out_min);
    }

    struct ControlOutput
    {
        double accel;
        double heading_error;
        int accel_cmd;
        int steer_cmd;
    };

    // =========================
    // SEEK (USES SIM STATE ONLY)
    // =========================
    ControlOutput seek(double tx, double ty)
    {
        ControlOutput out{0, 0, 1500, 1500};

        double dx = tx - sim_x_;
        double dy = ty - sim_y_;

        double dist = std::sqrt(dx * dx + dy * dy);
        if (dist < 1e-6) return out;

        double desired_heading = std::atan2(dy, dx);
        double err = normalize_angle(desired_heading - sim_heading_);

        const double max_steer = 30.0 * M_PI / 180.0;
        err = clamp(err, -max_steer, max_steer);

        out.heading_error = err;

        double accel = clamp(dist, 0.0, 15.0);

        out.accel = accel;

        out.steer_cmd = map_linear(err, -max_steer, max_steer, 1000, 2000);
        out.accel_cmd = map_linear(accel, 0.0, 15.0, 1000, 2000);

        return out;
    }

    // =========================
    // WAYPOINT SWITCH (SIM BASED)
    // =========================
    void get_next_waypoint()
    {
        if (counter >= (int)latitude_vec.size()) return;

        double dx = waypoint_x_ - sim_x_;
        double dy = waypoint_y_ - sim_y_;

        double dist = std::sqrt(dx * dx + dy * dy);

        if (dist < 2.0 || waypoint_x_ == 0.0)
        {
            waypoint_x_ = (latitude_vec[counter] - origin_latitude_) * meters_per_degree_;
            waypoint_y_ = (longitude_vec[counter] - origin_longitude_) * meters_per_degree_;

            counter = (counter + 1) % latitude_vec.size();
        }
    }

    // =========================
    // PHYSICS STEP
    // =========================
    void step_sim()
    {
        get_next_waypoint();

        auto ctrl = seek(waypoint_x_, waypoint_y_);

        // heading update
        sim_heading_ = normalize_angle(sim_heading_ + ctrl.heading_error * dt_);

        double fx = std::cos(sim_heading_);
        double fy = std::sin(sim_heading_);

        double ax = fx * ctrl.accel;
        double ay = fy * ctrl.accel;

        sim_vx_ += ax * dt_;
        sim_vy_ += ay * dt_;

        // friction
        sim_vx_ *= (1.0 - friction_ * dt_);
        sim_vy_ *= (1.0 - friction_ * dt_);

        // speed cap
        double speed = std::sqrt(sim_vx_ * sim_vx_ + sim_vy_ * sim_vy_);
        if (speed > max_speed_)
        {
            sim_vx_ *= max_speed_ / speed;
            sim_vy_ *= max_speed_ / speed;
        }

        sim_x_ += sim_vx_ * dt_;
        sim_y_ += sim_vy_ * dt_;

        // log to lat/lon
        double lat = sim_x_ / meters_per_degree_ + origin_latitude_;
        double lon = sim_y_ / meters_per_degree_ + origin_longitude_;

        lat_file_ << lat << "\n";
        lon_file_ << lon << "\n";

        RCLCPP_INFO(this->get_logger(),
            "SIM x=%.2f y=%.2f heading=%.2f deg speed=%.2f",
            sim_x_, sim_y_, sim_heading_ * 180.0 / M_PI, speed);
    }

    // =========================
    // LOAD WAYPOINTS
    // =========================
    void get_coords()
    {
        std::string pkg = ament_index_cpp::get_package_share_directory("ros_nav");

        std::ifstream lat(pkg + "/data/latitudes_minimal.txt");
        std::ifstream lon(pkg + "/data/longitudes_minimal.txt");

        double v;

        while (lat >> v) latitude_vec.push_back(v);
        while (lon >> v) longitude_vec.push_back(v);
    }

    // unused ROS objects (kept minimal)
    rclcpp::Publisher<geographic_msgs::msg::GeoPoseStamped>::SharedPtr waypoint_publisher_;
    rclcpp::TimerBase::SharedPtr waypoint_timer_;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<WaypointPublisher>());
    rclcpp::shutdown();
    return 0;
}