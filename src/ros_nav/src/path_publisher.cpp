#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/nav_sat_fix.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "mavros_msgs/srv/set_mode.hpp"
#include "ament_index_cpp/get_package_share_directory.hpp"
#include "geographic_msgs/msg/geo_pose_stamped.hpp"
#include <tf2/LinearMath/Quaternion.h> 
#include "tf2_geometry_msgs/tf2_geometry_msgs.h"
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
    }

private:
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

    // void heading_callback(const geographic_msgs::msg::GeoPoseStamped::SharedPtr msg)
    // {
    //     const auto& orientation = msg->pose.orientation;
        
    //     // Convert quaternion to RPY angles
    //     tf2::Quaternion tf_quat;
    //     tf2::fromMsg(orientation, tf_quat);
        
    //     double roll, pitch, yaw;
    //     tf2::Matrix3x3(tf_quat).getRPY(roll, pitch, yaw);
    //     current_heading_ = yaw;
    // }

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

        move_waypoint();

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

    void move_waypoint(){
        auto [outer_index, outer_dist, inner_index, inner_dist] = find_adjacent_lines();
        RCLCPP_INFO(this->get_logger(), "inner index vs outer index, %zu vs %.zu", inner_index, outer_index);
        RCLCPP_INFO(this->get_logger(), "inner dist vs outer dist, %.10f vs %.10f", inner_dist, outer_dist);
        return;
    }

    std::tuple<size_t, double, size_t, double> find_adjacent_lines(){
        size_t outer_min_index = 0;
        size_t inner_min_index = 0;
        double outer_min_dist = std::numeric_limits<double>::max();
        double inner_min_dist = std::numeric_limits<double>::max();
        double dist;
        for (size_t i=0; i < outerspline_vec.size();i++){
            dist = (current_latitude_ - outerspline_vec[i][0]) * (current_latitude_ - outerspline_vec[i][0]) + (current_longitude_ - outerspline_vec[i][1]) * (current_longitude_ - outerspline_vec[i][1]);
            if (dist < outer_min_dist){
                outer_min_dist = dist;
                outer_min_index = i;
            }
        }
        for (size_t i=0; i < innerspline_vec.size();i++){
            dist = (current_latitude_ - innerspline_vec[i][0]) * (current_latitude_ - innerspline_vec[i][0]) + (current_longitude_ - innerspline_vec[i][1]) * (current_longitude_ - innerspline_vec[i][1]);
            if (dist < inner_min_dist){
                inner_min_dist = dist;
                inner_min_index = i;
            }
        }
        return {outer_min_index, sqrt(outer_min_dist), inner_min_index, sqrt(inner_min_dist)};
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
            last_waypoint_latitude = latitude_vec[counter-1];
            last_waypoint_longitude = longitude_vec[counter-1];
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
        std::string outerspline_lat_file_path = package_share_path + "/data/outerlat_spline.txt";
        std::string outerspline_lon_file_path = package_share_path + "/data/outerlon_spline.txt";
        std::string innerspline_lat_file_path = package_share_path + "/data/innerlat_spline.txt";
        std::string innerspline_lon_file_path = package_share_path + "/data/innerlon_spline.txt";

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

        // Read outer spline latitudes from file
        ifstream read_outerspline_lat(outerspline_lat_file_path);
        if (!read_outerspline_lat.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", outerspline_lat_file_path.c_str());
            return;
        }
        while (read_outerspline_lat >> value) {
            outerspline_lat_vec.push_back(value);
        }
        read_outerspline_lat.close();

        // Read outer spline longitutdes from file
        ifstream read_outerspline_lon(outerspline_lon_file_path);
        if (!read_outerspline_lon.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", outerspline_lon_file_path.c_str());
            return;
        }
        while (read_outerspline_lon >> value) {
            outerspline_lon_vec.push_back(value);
        }
        read_outerspline_lon.close();

        // Read inner spline latitudes from file
        ifstream read_innerspline_lat(innerspline_lat_file_path);
        if (!read_innerspline_lat.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", innerspline_lat_file_path.c_str());
            return;
        }
        while (read_innerspline_lat >> value) {
            innerspline_lat_vec.push_back(value);
        }
        read_innerspline_lat.close();

        // Read inner spline longitutdes from file
        ifstream read_innerspline_lon(innerspline_lon_file_path);
        if (!read_innerspline_lon.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", innerspline_lon_file_path.c_str());
            return;
        }
        while (read_innerspline_lon >> value) {
            innerspline_lon_vec.push_back(value);
        }
        read_innerspline_lon.close();


        // Check if latitude and longitude vectors are the same size
        if (latitude_vec.size() != longitude_vec.size()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Latitude and Longitude vectors are not of equal size.");
            return;
        }

        // Check if outer spline latitude and longitude vectors are the same size
        if (outerspline_lat_vec.size() != outerspline_lon_vec.size()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Outer Spline Latitude and Longitude vectors are not of equal size.");
            return;
        }

        // Check if inner spline latitude and longitude vectors are the same size
        if (innerspline_lat_vec.size() != innerspline_lon_vec.size()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Inner Spline Latitude and Longitude vectors are not of equal size.");
            return;
        }

        for(size_t i=0; i<outerspline_lat_vec.size(); i++) {
            outerspline_vec.push_back({outerspline_lat_vec[i], outerspline_lon_vec[i]});
        }

        for(size_t i=0; i<innerspline_lat_vec.size(); i++) {
            innerspline_vec.push_back({innerspline_lat_vec[i], innerspline_lon_vec[i]});
        }
    }

    rclcpp::Subscription<sensor_msgs::msg::NavSatFix>::SharedPtr gps_subscriber_;
    rclcpp::Publisher<geographic_msgs::msg::GeoPoseStamped>::SharedPtr waypoint_publisher_;
    rclcpp::Subscription<geographic_msgs::msg::GeoPoseStamped>::SharedPtr heading_subscriber_;
    rclcpp::Client<mavros_msgs::srv::SetMode>::SharedPtr set_mode_client_;
    rclcpp::TimerBase::SharedPtr waypoint_timer_;
    rclcpp::TimerBase::SharedPtr services_timer_;

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

    const double meters_per_degree_ = 111000.0;

    const double offset_latitude = 0.00004;
    const double offset_longitude = 0.00004;


    vector<double> longitude_vec;  // Vector to store longitudes
    vector<double> latitude_vec;  // Vector to store latitudes
    vector<double> outerspline_lon_vec;
    vector<double> outerspline_lat_vec;
    vector<double> innerspline_lon_vec;
    vector<double> innerspline_lat_vec;
    vector<array<double, 2>> outerspline_vec;
    vector<array<double, 2>> innerspline_vec;

    int counter = 0;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<WaypointPublisher>());
    rclcpp::shutdown();
    return 0;
}
