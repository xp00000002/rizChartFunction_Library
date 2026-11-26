#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <utility>
#include <vector>

namespace py = pybind11;

namespace {

constexpr double EPS = 1e-9;

using Point = std::pair<double, double>;

double cross(double ax, double ay, double bx, double by) {
    return ax * by - ay * bx;
}

double polygon_area(const std::vector<Point>& points) {
    double total = 0.0;
    for (std::size_t i = 0; i < points.size(); ++i) {
        const auto& point = points[i];
        const auto& following = points[(i + 1) % points.size()];
        total += point.first * following.second - following.first * point.second;
    }
    return total * 0.5;
}

bool point_on_segment(const Point& start, const Point& end, const Point& point) {
    const double c = cross(
        end.first - start.first,
        end.second - start.second,
        point.first - start.first,
        point.second - start.second
    );
    if (std::abs(c) > EPS) {
        return false;
    }
    return (
        std::min(start.first, end.first) - EPS <= point.first
        && point.first <= std::max(start.first, end.first) + EPS
        && std::min(start.second, end.second) - EPS <= point.second
        && point.second <= std::max(start.second, end.second) + EPS
    );
}

bool segments_intersect(
    const Point& first_start,
    const Point& first_end,
    const Point& second_start,
    const Point& second_end
) {
    const double first = cross(
        first_end.first - first_start.first,
        first_end.second - first_start.second,
        second_start.first - first_start.first,
        second_start.second - first_start.second
    );
    const double second = cross(
        first_end.first - first_start.first,
        first_end.second - first_start.second,
        second_end.first - first_start.first,
        second_end.second - first_start.second
    );
    const double third = cross(
        second_end.first - second_start.first,
        second_end.second - second_start.second,
        first_start.first - second_start.first,
        first_start.second - second_start.second
    );
    const double fourth = cross(
        second_end.first - second_start.first,
        second_end.second - second_start.second,
        first_end.first - second_start.first,
        first_end.second - second_start.second
    );

    if (
        ((first > EPS && second < -EPS) || (first < -EPS && second > EPS))
        && ((third > EPS && fourth < -EPS) || (third < -EPS && fourth > EPS))
    ) {
        return true;
    }

    return (
        (std::abs(first) <= EPS && point_on_segment(first_start, first_end, second_start))
        || (std::abs(second) <= EPS && point_on_segment(first_start, first_end, second_end))
        || (std::abs(third) <= EPS && point_on_segment(second_start, second_end, first_start))
        || (std::abs(fourth) <= EPS && point_on_segment(second_start, second_end, first_end))
    );
}

bool point_in_polygon(
    const std::vector<Point>& points,
    const Point& query,
    bool include_boundary
) {
    for (std::size_t i = 0; i < points.size(); ++i) {
        const auto& start = points[i];
        const auto& end = points[(i + 1) % points.size()];
        if (point_on_segment(start, end, query)) {
            return include_boundary;
        }
    }

    bool inside = false;
    for (std::size_t i = 0; i < points.size(); ++i) {
        const auto& start = points[i];
        const auto& end = points[(i + 1) % points.size()];
        if ((start.second > query.second) != (end.second > query.second)) {
            const double ratio =
                (query.second - start.second) / (end.second - start.second);
            const double cross_x =
                start.first + (end.first - start.first) * ratio;
            if (cross_x > query.first) {
                inside = !inside;
            }
        }
    }
    return inside;
}

std::vector<Point> unpack_coords(const std::vector<double>& coords) {
    if (coords.size() < 6 || coords.size() % 2 != 0) {
        throw std::invalid_argument("polygon coordinates must contain at least 3 x/y pairs");
    }
    std::vector<Point> points;
    points.reserve(coords.size() / 2);
    for (std::size_t i = 0; i + 1 < coords.size(); i += 2) {
        points.emplace_back(coords[i], coords[i + 1]);
    }
    return points;
}

bool is_simple_polygon(const std::vector<double>& coords) {
    const auto points = unpack_coords(coords);
    const std::size_t count = points.size();
    if (count < 3 || std::abs(polygon_area(points)) <= EPS) {
        return false;
    }

    for (std::size_t i = 0; i < count; ++i) {
        const auto& start = points[i];
        const auto& end = points[(i + 1) % count];
        if (std::hypot(end.first - start.first, end.second - start.second) <= EPS) {
            return false;
        }
    }

    for (std::size_t first_index = 0; first_index < count; ++first_index) {
        const auto& first_start = points[first_index];
        const auto& first_end = points[(first_index + 1) % count];
        for (std::size_t second_index = first_index + 1; second_index < count; ++second_index) {
            if (
                second_index == first_index
                || second_index == (first_index + 1) % count
                || first_index == (second_index + 1) % count
            ) {
                continue;
            }
            const auto& second_start = points[second_index];
            const auto& second_end = points[(second_index + 1) % count];
            if (segments_intersect(first_start, first_end, second_start, second_end)) {
                return false;
            }
        }
    }
    return true;
}

std::vector<std::pair<double, double>> compute_line_intervals(
    const std::vector<Point>& polygon,
    double origin_x,
    double origin_y,
    double direction_x,
    double direction_y,
    std::optional<double> start_t,
    std::optional<double> end_t
) {
    std::vector<double> events;

    for (std::size_t i = 0; i < polygon.size(); ++i) {
        const auto& start = polygon[i];
        const auto& end = polygon[(i + 1) % polygon.size()];
        const double edge_x = end.first - start.first;
        const double edge_y = end.second - start.second;
        const double ax = start.first - origin_x;
        const double ay = start.second - origin_y;
        const double denominator = cross(direction_x, direction_y, edge_x, edge_y);

        if (std::abs(denominator) <= EPS) {
            if (std::abs(cross(ax, ay, direction_x, direction_y)) <= EPS) {
                events.push_back(ax * direction_x + ay * direction_y);
                events.push_back(
                    (end.first - origin_x) * direction_x
                    + (end.second - origin_y) * direction_y
                );
            }
            continue;
        }

        const double distance = cross(ax, ay, edge_x, edge_y) / denominator;
        const double edge_ratio = cross(ax, ay, direction_x, direction_y) / denominator;
        if (-EPS <= edge_ratio && edge_ratio <= 1.0 + EPS) {
            events.push_back(distance);
        }
    }

    if (start_t.has_value()) {
        events.push_back(*start_t);
    }
    if (end_t.has_value()) {
        events.push_back(*end_t);
    }

    std::sort(events.begin(), events.end());
    std::vector<double> unique;
    for (double value : events) {
        if (unique.empty() || std::abs(value - unique.back()) > EPS) {
            unique.push_back(value);
        }
    }

    std::vector<std::pair<double, double>> intervals;
    for (std::size_t i = 0; i + 1 < unique.size(); ++i) {
        const double left = unique[i];
        const double right = unique[i + 1];
        if (right - left <= EPS) {
            continue;
        }
        if (start_t.has_value() && right <= *start_t + EPS) {
            continue;
        }
        if (end_t.has_value() && left >= *end_t - EPS) {
            continue;
        }
        const double middle = (left + right) * 0.5;
        const Point query{
            origin_x + direction_x * middle,
            origin_y + direction_y * middle,
        };
        if (point_in_polygon(polygon, query, true)) {
            intervals.emplace_back(left, right);
        }
    }
    return intervals;
}

std::vector<std::pair<double, double>> line_intervals(
    const std::vector<double>& coords,
    double origin_x,
    double origin_y,
    double direction_x,
    double direction_y,
    std::optional<double> start_t,
    std::optional<double> end_t
) {
    return compute_line_intervals(
        unpack_coords(coords),
        origin_x,
        origin_y,
        direction_x,
        direction_y,
        start_t,
        end_t
    );
}

std::vector<std::vector<std::pair<double, double>>> line_intervals_many(
    const std::vector<double>& coords,
    const std::vector<double>& origin_coords,
    const std::vector<double>& direction_coords,
    std::optional<std::vector<double>> start_ts,
    std::optional<std::vector<double>> end_ts
) {
    const auto polygon = unpack_coords(coords);
    if (
        origin_coords.size() % 2 != 0
        || direction_coords.size() != origin_coords.size()
    ) {
        throw std::invalid_argument(
            "origin and direction arrays must contain matching x/y pairs"
        );
    }

    const std::size_t count = origin_coords.size() / 2;
    if (start_ts.has_value() && start_ts->size() != count) {
        throw std::invalid_argument("start_ts length must match ray count");
    }
    if (end_ts.has_value() && end_ts->size() != count) {
        throw std::invalid_argument("end_ts length must match ray count");
    }

    std::vector<std::vector<std::pair<double, double>>> result;
    result.reserve(count);
    for (std::size_t index = 0; index < count; ++index) {
        std::optional<double> start_t;
        std::optional<double> end_t;
        if (start_ts.has_value()) {
            start_t = (*start_ts)[index];
        }
        if (end_ts.has_value()) {
            end_t = (*end_ts)[index];
        }
        result.push_back(
            compute_line_intervals(
                polygon,
                origin_coords[index * 2],
                origin_coords[index * 2 + 1],
                direction_coords[index * 2],
                direction_coords[index * 2 + 1],
                start_t,
                end_t
            )
        );
    }
    return result;
}

py::list point_in_polygon_many(
    const std::vector<double>& coords,
    const std::vector<double>& point_coords,
    bool include_boundary
) {
    const auto polygon = unpack_coords(coords);
    if (point_coords.size() % 2 != 0) {
        throw std::invalid_argument("point coordinates must be x/y pairs");
    }
    py::list result;
    for (std::size_t i = 0; i + 1 < point_coords.size(); i += 2) {
        result.append(py::bool_(
            point_in_polygon(
                polygon,
                Point{point_coords[i], point_coords[i + 1]},
                include_boundary
            )
        ));
    }
    return result;
}

}  // namespace

PYBIND11_MODULE(_rizchart_native, module) {
    module.doc() = "Optional C++ geometry kernels for rizChartFunction";
    module.attr("__version__") = "0.5.0";
    module.def("ping", []() { return std::string("rizchart-native"); });
    module.def("is_simple_polygon", &is_simple_polygon);
    module.def(
        "line_intervals",
        &line_intervals,
        py::arg("coords"),
        py::arg("origin_x"),
        py::arg("origin_y"),
        py::arg("direction_x"),
        py::arg("direction_y"),
        py::arg("start_t") = py::none(),
        py::arg("end_t") = py::none()
    );
    module.def(
        "line_intervals_many",
        &line_intervals_many,
        py::arg("coords"),
        py::arg("origin_coords"),
        py::arg("direction_coords"),
        py::arg("start_ts") = py::none(),
        py::arg("end_ts") = py::none()
    );
    module.def(
        "point_in_polygon_many",
        &point_in_polygon_many,
        py::arg("coords"),
        py::arg("points"),
        py::arg("include_boundary") = true
    );
}
