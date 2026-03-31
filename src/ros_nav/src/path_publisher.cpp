#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/nav_sat_fix.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "mavros_msgs/srv/set_mode.hpp"
#include "ament_index_cpp/get_package_share_directory.hpp"
#include "geographic_msgs/msg/geo_pose_stamped.hpp"
#include "geometry_msgs/msg/point.hpp"
#include <tf2/LinearMath/Quaternion.h> 
#include "tf2_geometry_msgs/tf2_geometry_msgs.h"
#include "geometry_msgs/msg/twist_stamped.hpp"
#include "geometry_msgs/msg/point.hpp"
#include <fstream>
#include <vector>
#include <iostream>
#include <cmath>

using namespace std;
using namespace std::chrono_literals;
using std::placeholders::_1;

class WaypointPublisher : public rclcpp::Node
{
public:
    WaypointPublisher() : Node("waypoint_publisher")
    {
        get_coords();

        lane_center_subscriber_ = this->create_subscription<geometry_msgs::msg::Point>(
            "lane_center", 10, std::bind(&WaypointPublisher::lane_center_callback, this, std::placeholders::_1));

        // Subscription to the kart's GPS position
        gps_subscriber_ = this->create_subscription<sensor_msgs::msg::NavSatFix>(
            "/mavros/global_position/global", rclcpp::SensorDataQoS(), std::bind(&WaypointPublisher::gps_callback, this, _1));

        // Publisher for waypoints to the MAVROS setpoint topic
        waypoint_publisher_ = this->create_publisher<geographic_msgs::msg::GeoPoseStamped>("/mavros/setpoint_position/global", 10);

        // heading_subscriber_ = this->create_subscription<geographic_msgs::msg::GeoPoseStamped>(
        //     "/mavros/setpoint_position/global", rclcpp::SensorDataQoS(), std::bind(&WaypointPublisher::heading_callback, this, _1));

        // Create the service client to change the mode
        set_mode_client_ = this->create_client<mavros_msgs::srv::SetMode>("/mavros/set_mode");

        // Change the mode to OFFBOARD after a delay
        services_timer_ = this->create_wall_timer(3s, [this]() {
            RCLCPP_INFO(this->get_logger(), "Initiating OFFBOARD mode...");
            change_to_offboard_mode();
        });

        // Start a timer to publish dummy waypoints
        waypoint_timer_ = this->create_wall_timer(200ms, [this]() { publish_waypoint(); });
    
        // Subscribe to velo (m/s)
        velo_sub_ = this->create_subscription<geometry_msgs::msg::TwistStamped>(
            "/mavros/local_position/velocity_body", rclcpp::SensorDataQoS(),
            [this](const geometry_msgs::msg::TwistStamped::SharedPtr msg) {
                velo_callback(msg);});

        velo_timer_ = this->create_wall_timer(1s, [this]() {
            velo_fake_callback();
        });
    }

private:
    void lane_center_callback(const geometry_msgs::msg::Point::SharedPtr msg)
    {
        RCLCPP_INFO(this->get_logger(), "Received lane center: x=%.2f, y=%.2f, z=%.2f", msg->x, msg->y, msg->z);
        // Use lane center data as needed
    }
    void gps_callback(const sensor_msgs::msg::NavSatFix::SharedPtr msg)
    {
        if (isfinite(msg->latitude) && isfinite(msg->longitude)) {
            last_kart_latitude = current_latitude_;
            last_kart_longitude = current_longitude_;
            current_latitude_ = msg->latitude;
            current_longitude_ = msg->longitude;

        } else {
            RCLCPP_WARN(this->get_logger(), "Invalid GPS data received. Waiting for valid GPS signal...");
        }
    }

    void velo_callback(const geometry_msgs::msg::TwistStamped::SharedPtr msg)
    {
        current_velo_x_ = msg->twist.linear.x;
        current_velo_y_ = msg->twist.linear.y;
    }

    void velo_fake_callback()
    {
        RCLCPP_INFO(this->get_logger(), "--- Velocity Update ---");
        RCLCPP_INFO(this->get_logger(), "x: %f (m/s)", current_velo_x_);
        RCLCPP_INFO(this->get_logger(), "y: %f (m/s)", current_velo_y_);
        
    }    


    void heading_callback(const geographic_msgs::msg::GeoPoseStamped::SharedPtr msg)
    {
        const auto& orientation = msg->pose.orientation;
        
        // Convert quaternion to RPY angles
        tf2::Quaternion tf_quat;
        tf2::fromMsg(orientation, tf_quat);
        
        double roll, pitch, yaw;
        tf2::Matrix3x3(tf_quat).getRPY(roll, pitch, yaw);
        current_heading_ = yaw;
    }

    void change_to_offboard_mode()
    {
        if (!set_mode_client_->wait_for_service(5s)) {
            RCLCPP_ERROR(this->get_logger(), "SetMode service not available");
            return;
        }

        auto request = std::make_shared<mavros_msgs::srv::SetMode::Request>();
        request->base_mode = 0; // No change to base_mode
        request->custom_mode = "OFFBOARD";

        std::thread([this, request]() {
            auto result = set_mode_client_->async_send_request(request);
            try {
                if (result.wait_for(5s) == std::future_status::ready) {
                    auto response = result.get();
                    if (response->mode_sent) {
                        RCLCPP_INFO(this->get_logger(), "Successfully changed to OFFBOARD mode");
                        waypoint_timer_->cancel(); // Stop publishing dummy waypoints
                        waypoint_timer_ = this->create_wall_timer(1s, [this]() { publish_waypoint(); }); // Publish real waypoints
                    } else {
                        RCLCPP_ERROR(this->get_logger(), "Failed to change to OFFBOARD mode");
                    }
                } else {
                    RCLCPP_ERROR(this->get_logger(), "Timeout while changing to OFFBOARD mode");
                }
            } catch (const std::exception &e) {
                RCLCPP_ERROR(this->get_logger(), "Exception in setting mode: %s", e.what());
            }
        }).detach(); // Detach the thread
    }

    void publish_waypoint()
    {
        // RCLCPP_INFO(this->get_logger(), "waypoint_latidtude: %.6f, waypoint_longitude: %.6f", waypoint_latitude, waypoint_longitude);
        
        get_next_waypoint();
        // Convert GPS (latitude, longitude) to a local coordinate system
        // double waypoint_x = (waypoint_latitude - origin_latitude_) * meters_per_degree_;
        // double waypoint_y = (waypoint_longitude - origin_longitude_) * meters_per_degree_;       

        reynolds_pathfollowing();

        // Set message values
        auto waypoint_msg = geographic_msgs::msg::GeoPoseStamped();
        waypoint_msg.header.stamp = this->get_clock()->now();
        waypoint_msg.header.frame_id = "global"; // Replace with your local frame if needed
        waypoint_msg.pose.position.latitude = waypoint_latitude;
        waypoint_msg.pose.position.longitude = waypoint_longitude;
        waypoint_msg.pose.position.altitude = 0.0; // Assuming ground-level operation


        RCLCPP_INFO(this->get_logger(), "Publishing Waypoint: latitude: %.2f, longitude: %.2f, current counter = %d", waypoint_latitude, waypoint_longitude, counter);
        waypoint_publisher_->publish(waypoint_msg);
    }


    double normalize_angle(double angle){
        if (angle < - M_PI) {
            angle += 2 * M_PI;
        }
        else if (angle >= M_PI){
            angle -= 2 * M_PI;
        }
        return angle;
    }


    // this is where the magic happens
    void reynolds_pathfollowing()
    {

        if (waypoint_latitude == 0.0 || last_waypoint_latitude == 0.0) {
            RCLCPP_WARN(this->get_logger(), "Reynolds skipped: invalid waypoint data");
            return;
        }
        // Convert current GPS -> local meters
        double pos_x = (current_latitude_  - origin_latitude_)  * meters_per_degree_;
        double pos_y = (current_longitude_ - origin_longitude_) * meters_per_degree_;

        // Current velocity vector  m/s)
        double vel_x = current_velo_x_;
        double vel_y = current_velo_y_;

        // Velocity magnitude (speed)
        double speed = std::sqrt(vel_x * vel_x + vel_y * vel_y);

        // Avoid divide-by-zero when stopped
        if (speed < 0.1) {
            vel_x = std::cos(current_heading_);
            vel_y = std::sin(current_heading_);
            speed = 0.1;
        }

        // STEP 1: Predict future position
        const double lookahead_time = 0.5;  // seconds - arbitrary
        double future_x = pos_x + vel_x * lookahead_time;
        double future_y = pos_y + vel_y * lookahead_time;

        // Find closest point on the path
        // Path = line segment between last & next waypoint
        double wp1_x = (last_waypoint_latitude  - origin_latitude_)  * meters_per_degree_;
        double wp1_y = (last_waypoint_longitude - origin_longitude_) * meters_per_degree_;

        double wp2_x = (waypoint_latitude  - origin_latitude_)  * meters_per_degree_;
        double wp2_y = (waypoint_longitude - origin_longitude_) * meters_per_degree_;

        // Path direction vector
        double path_dx = wp2_x - wp1_x;
        double path_dy = wp2_y - wp1_y;

        double path_len_sq = path_dx * path_dx + path_dy * path_dy;
        if (path_len_sq < 1e-6) return;

        // Project future position onto path segment
        double t = ((future_x - wp1_x) * path_dx + (future_y - wp1_y) * path_dy) / path_len_sq;
        t = std::max(0.0, std::min(1.0, t));  // clamp to segment

        double closest_x = wp1_x + t * path_dx;
        double closest_y = wp1_y + t * path_dy;

        // Check distance from path
        double dist_x = future_x - closest_x;
        double dist_y = future_y - closest_y;
        double distance_from_path = std::sqrt(dist_x * dist_x + dist_y * dist_y);

        //Choose target ahead on the path
        // Reynolds: seek a point slightly forward
        const double target_ahead_dist = 2.0;  // meters ahead on path
        double path_len = std::sqrt(path_len_sq);

        double path_dir_x = path_dx / path_len;
        double path_dir_y = path_dy / path_len;

        double target_x = closest_x + path_dir_x * target_ahead_dist;
        double target_y = closest_y + path_dir_y * target_ahead_dist;

        // Compute steering (SEEK behavior)
        double desired_x = target_x - pos_x;
        double desired_y = target_y - pos_y;

        double desired_mag = std::sqrt(desired_x * desired_x + desired_y * desired_y);
        if (desired_mag < 1e-6) return;

        desired_x /= desired_mag;
        desired_y /= desired_mag;

        // Max speed for dev 
        const double max_speed = 11.0;  // m/s (kart limit)
        desired_x *= max_speed;
        desired_y *= max_speed;

        double steer_x = desired_x - vel_x;
        double steer_y = desired_y - vel_y;

        // Convert steering to heading
        double desired_heading = std::atan2(steer_y, steer_x);
        double heading_error = normalize_angle(desired_heading - current_heading_);

        //Convert back to GPS waypoint
        double target_lat = target_x / meters_per_degree_ + origin_latitude_;
        double target_lon = target_y / meters_per_degree_ + origin_longitude_;

        waypoint_latitude  = target_lat;
        waypoint_longitude = target_lon;

        RCLCPP_INFO(this->get_logger(),
            "[Reynolds] dist=%.2f m | heading_error=%.2f deg",
            distance_from_path,
            heading_error * 180.0 / M_PI
        );
    }


    void get_next_waypoint()
    {
        // Ensure counter does not exceed vector size
        if (counter >= (int) latitude_vec.size()) {
            RCLCPP_INFO(this->get_logger(), "All waypoints have been processed.");
            waypoint_latitude = 0.0;
            waypoint_longitude = 0.0;
            return;
        }
        double latitude_differential = abs(waypoint_latitude - current_latitude_);
        double longitude_differential = abs(waypoint_longitude - current_longitude_);
        RCLCPP_INFO(this->get_logger(), "latitude_differential = %.6f, longitude_differential = %.6f", latitude_differential, longitude_differential);
        // If this is the first waypoint or we have reached the current waypoint
        if ((waypoint_latitude == 0.0 && waypoint_longitude == 0.0) || (latitude_differential < offset_latitude && longitude_differential < offset_longitude)) {
            waypoint_latitude = latitude_vec[counter];
            waypoint_longitude = longitude_vec[counter];
            next_waypoint_latitude = latitude_vec[counter+1];
            next_waypoint_longitude = longitude_vec[counter+2];
            next2_waypoint_latitude = latitude_vec[counter+2];
            next2_waypoint_longitude = longitude_vec[counter+1];
            int last_idx = (counter == 0) ? latitude_vec.size() - 1 : counter - 1;
            last_waypoint_latitude  = latitude_vec[last_idx];
            last_waypoint_longitude = longitude_vec[last_idx];
            RCLCPP_INFO(this->get_logger(), "Updating to next waypoint: Latitude: %.6f, Longitude: %.6f",
                        waypoint_latitude, waypoint_longitude);
            counter++;
            counter %= latitude_vec.size();
        }
    }

    void get_coords()
    {
        // Get the path to the package's share directory
        std::string package_share_path = ament_index_cpp::get_package_share_directory("ros_nav");
        std::string latitude_file_path = package_share_path + "/data/latitudes_minimal.txt";
        std::string longitude_file_path = package_share_path + "/data/longitudes_minimal.txt";
        std::string outer_latitude_file_path = package_share_path + "/data/outterlat_spline.txt";
        std::string outer_longitude_file_path = package_share_path + "/data/outterlon_spline.txt";
        std::string inner_latitude_file_path = package_share_path + "/data/innerlat_spline.txt";
        std::string inner_longitude_file_path = package_share_path + "/data/innerlon_spline.txt";


        // Read latitudes from file
        ifstream read_latitude(latitude_file_path);
        if (!read_latitude.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", latitude_file_path.c_str());
            return;
        }
        double value;
        while (read_latitude >> value) {
            latitude_vec.push_back(value);
        }
        read_latitude.close();

        // Read longitudes from file
        ifstream read_longitude(longitude_file_path);
        if (!read_longitude.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", longitude_file_path.c_str());
            return;
        }
        while (read_longitude >> value) {
            longitude_vec.push_back(value);
        }
        read_longitude.close();

        // Check if latitude and longitude vectors are the same size
        if (latitude_vec.size() != longitude_vec.size()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Latitude and Longitude vectors are not of equal size.");
            return;
        }

        //

        // Read outer spline latitudes from file
        ifstream read_outer_latitude(outer_latitude_file_path);
        if (!read_outer_latitude.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", outer_latitude_file_path.c_str());
            return;
        }
        while (read_outer_latitude >> value) {
            outer_latitude_vec.push_back(value);
        }
        read_outer_latitude.close();

        // Read outer spline longitudes from file
        ifstream read_outer_longitude(outer_longitude_file_path);
        if (!read_outer_longitude.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", outer_longitude_file_path.c_str());
            return;
        }
        while (read_outer_longitude >> value) {
            outer_longitude_vec.push_back(value);
        }
        read_outer_longitude.close();

        // Check if outer spline latitude and longitude vectors are the same size
        if (outer_latitude_vec.size() != outer_longitude_vec.size()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Outer Spline Latitude and Longitude vectors are not of equal size.");
            return;
        }

        //

        // Read inner spline latitudes from file
        ifstream read_inner_latitude(inner_latitude_file_path);
        if (!read_inner_latitude.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", inner_latitude_file_path.c_str());
            return;
        }
        while (read_inner_latitude >> value) {
            inner_latitude_vec.push_back(value);
        }
        read_inner_latitude.close();

        // Read inner spline longitudes from file
        ifstream read_inner_longitude(inner_longitude_file_path);
        if (!read_inner_longitude.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", inner_longitude_file_path.c_str());
            return;
        }
        while (read_inner_longitude >> value) {
            inner_longitude_vec.push_back(value);
        }
        read_inner_longitude.close();

        // Check if inner spline latitude and longitude vectors are the same size
        if (inner_latitude_vec.size() != inner_longitude_vec.size()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Inner Spline Latitude and Longitude vectors are not of equal size.");
            return;
        }


    }

    rclcpp::Subscription<sensor_msgs::msg::NavSatFix>::SharedPtr gps_subscriber_;
    rclcpp::Publisher<geographic_msgs::msg::GeoPoseStamped>::SharedPtr waypoint_publisher_;
    rclcpp::Subscription<geographic_msgs::msg::GeoPoseStamped>::SharedPtr heading_subscriber_;
    rclcpp::Client<mavros_msgs::srv::SetMode>::SharedPtr set_mode_client_;
    rclcpp::Subscription<geometry_msgs::msg::TwistStamped>:: SharedPtr velo_sub_;
    rclcpp::Subscription<geometry_msgs::msg::Point>::SharedPtr lane_center_subscriber_;
    rclcpp::TimerBase::SharedPtr waypoint_timer_;
    rclcpp::TimerBase::SharedPtr services_timer_;
    rclcpp::TimerBase::SharedPtr velo_timer_;

    double current_latitude_ = 0.0;
    double current_longitude_ = 0.0;

    double last_kart_latitude = 0.0;
    double last_kart_longitude = 0.0;

    double waypoint_latitude = 0.0;
    double waypoint_longitude = 0.0;

    double next_waypoint_latitude = 0.0;
    double next_waypoint_longitude = 0.0;

    double next2_waypoint_latitude = 0.0;
    double next2_waypoint_longitude = 0.0;

    double last_waypoint_latitude = 0.0;
    double last_waypoint_longitude = 0.0;

    double current_heading_ = 0.0;

    const double origin_latitude_ = 40.437688;
    const double origin_longitude_ = -86.944469;

    const double offset_latitude = 0.00004;
    const double offset_longitude = 0.00004;

    const double meters_per_degree_ = 111000.0;

    // meters
    const int path_rad = 0.9;

    double current_velo_x_ = 0.0;
    double current_velo_y_ = 0.0;


    vector<double> longitude_vec;  // Vector to store longitudes
    vector<double> latitude_vec;  // Vector to store latitudes

    vector<double> outer_latitude_vec;
    vector<double> inner_latitude_vec;
    vector<double> outer_longitude_vec;
    vector<double> inner_longitude_vec;

    int counter = 0;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<WaypointPublisher>());
    rclcpp::shutdown();
    return 0;
}
