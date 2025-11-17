import math

def compute_heading(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute heading (bearing) between two lat/lon points.

    Parameters:
        lat1 (float): Latitude of point 1 in degrees.
        lon1 (float): Longitude of point 1 in degrees.
        lat2 (float): Latitude of point 2 in degrees.
        lon2 (float): Longitude of point 2 in degrees.

    Returns:
        float: Bearing (heading) in degrees clockwise from North in range [0, 360).
    """
    # convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon_rad = math.radians(lon2 - lon1)

    x = math.sin(dlon_rad) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)

    initial_bearing = math.atan2(x, y)
    # Convert from radians to degrees and normalize to [0,360)
    bearing = (math.degrees(initial_bearing) + 360.0) % 360.0

    return bearing