#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/nav_sat_fix.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "mavros_msgs/srv/set_mode.hpp"
#include "ament_index_cpp/get_package_share_directory.hpp"
#include "geographic_msgs/msg/geo_pose_stamped.hpp"
#include "geometry_msgs/msg/point.hpp"
#include <tf2/LinearMath/Quaternion.h> 
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"
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

    // -------------------- Main algorithm integration --------------------
    void move_waypoint()
    {
        // Find nearest inner/outer spline points
        auto result = find_adjacent_lines();
        size_t outer_idx = get<0>(result);
        double outer_dist_m = get<1>(result);
        size_t inner_idx = get<2>(result);
        double inner_dist_m = get<3>(result);

        double track_width_m = computeDistanceMeters(
            innerspline_vec[inner_idx][0], innerspline_vec[inner_idx][1],
            outerspline_vec[outer_idx][0], outerspline_vec[outer_idx][1]);

        double d_center_m = 0.5 * (outer_dist_m - inner_dist_m);
        double w_half = 0.5 * track_width_m;
        double effective_halfwidth = w_half - 0.5 * w_vehicle;
        if (effective_halfwidth < 0.1) effective_halfwidth = w_half;

        double centerness = d_center_m / (effective_halfwidth + EPS);
        centerness = std::max(-1.0, std::min(1.0, centerness));

        // Heading from last kart position to current
        double heading_rad = computeHeadingFromWaypoints(last_kart_latitude, last_kart_longitude,
                                                         current_latitude_, current_longitude_);

        // Lateral shift Δ
        double delta_center = -K_e * sat(centerness, B);
        double delta_turn = K_theta * copysign(1.0, theta_ahead_) * w_half *
                            (1 - exp(-fabs(theta_ahead_) / theta_0)) *
                            f_L(L_measured_);
        double delta = delta_center + delta_turn;

        // Clip delta to safe region
        double delta_max = effective_halfwidth - s_safety;
        delta = std::max(-delta_max, std::min(delta_max, delta));

        // Left-normal vector
        double n_x = -sin(heading_rad);
        double n_y = cos(heading_rad);

        double dX = delta * n_x; // east meters
        double dY = delta * n_y; // north meters

        double delta_lat = (dY / R_earth) * 180.0 / M_PI;
        double delta_lon = (dX / (R_earth * cos(waypoint_latitude * M_PI / 180.0))) * 180.0 / M_PI;

        waypoint_latitude += delta_lat;
        waypoint_longitude += delta_lon;

        RCLCPP_INFO(this->get_logger(), "Lateral Δ=%.3f m -> Δlat %.8f° Δlon %.8f°",
                    delta, delta_lat, delta_lon);
    }

    // -------------------- Helpers --------------------
    inline double sat(double e, double B) {
        return (fabs(e) <= B) ? 0.0 : e - copysign(B, e);
    }

    inline double f_L(double L) {
        return std::min(L, L_max) / L;
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

    double computeDistanceMeters(double lat1_deg, double lon1_deg, double lat2_deg, double lon2_deg) const {
        double phi1 = lat1_deg * M_PI / 180.0;
        double phi2 = lat2_deg * M_PI / 180.0;
        double dlat = (lat2_deg - lat1_deg) * meters_per_degree_;
        double dlon = (lon2_deg - lon1_deg) * meters_per_degree_;
        return sqrt(dlat * dlat + dlon * dlon);
    }

    double computeHeadingFromWaypoints(double latA_deg, double lonA_deg, double latB_deg, double lonB_deg) const {
        double dy = (latB_deg - latA_deg) * meters_per_degree_;
        double dx = (lonB_deg - lonA_deg) * meters_per_degree_;
        return atan2(dy, dx);
    }


    std::tuple<size_t, double, size_t, double> find_adjacent_lines(){
        size_t outer_min_index = 0;
        size_t inner_min_index = 0;
        double outer_min_dist = std::numeric_limits<double>::max();
        double inner_min_dist = std::numeric_limits<double>::max();
        double dist;
        for (size_t i=0; i < outerspline_vec.size();i++){
            dist = ((current_latitude_ - outerspline_vec[i][0]) * meters_per_degree_) * ((current_latitude_ - outerspline_vec[i][0])*meters_per_degree_) + ((current_longitude_ - outerspline_vec[i][1])*meters_per_degree_) * ((current_longitude_ - outerspline_vec[i][1])*meters_per_degree_);
            if (dist < outer_min_dist){
                outer_min_dist = dist;
                outer_min_index = i;
            }
        }
        for (size_t i=0; i < innerspline_vec.size();i++){
            dist = ((current_latitude_ - innerspline_vec[i][0])*meters_per_degree_) * ((current_latitude_ - innerspline_vec[i][0])*meters_per_degree_) + ((current_longitude_ - innerspline_vec[i][1])*meters_per_degree_) * ((current_longitude_ - innerspline_vec[i][1])*meters_per_degree_);
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
    rclcpp::Subscription<geometry_msgs::msg::Point>::SharedPtr lane_center_subscriber_;
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

    const double offset_latitude = 0.00004;
    const double offset_longitude = 0.00004;

    // Algorithm parameters
    double theta_ahead_ = 0.25;   // radians, can be updated from vision/track info
    double L_measured_ = 3.0;     // meters, distance to next waypoint

    const double w_vehicle = 0.5;
    const double EPS = 1e-6;
    const double K_e = 0.6;
    const double B = 0.05;
    const double K_theta = 0.6;
    const double theta_0 = 0.25;
    const double L_max = 9.0;
    const double s_safety = 0.2;
    const double R_earth = 6378137.0;
    const double meters_per_degree_ = 111000.0;


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
