from collections import OrderedDict
from typing import List
import numpy as np

from functions.format import format_heading, hhmmsscc_to_milliseconds, pad_with_zeros
from functions.maths import compute_heading
from functions.physics import estimate_instant_fuel_consumption

def compute_oversteer(
    data: OrderedDict[str, List[str]],
    rotation_speed_column: str,
    gyro_z_column: str,
    oversteer_column: str
) -> OrderedDict[str, List[str]]:
    """
    Compute oversteer values based on rotation speed and gyro Z values.

    Parameters:
        data (OrderedDict[str, List[str]]): Input data with existing columns.
        rotation_speed_column (str): Name of the column containing rotation speed values.
        gyro_z_column (str): Name of the column containing gyro Z values.
        oversteer_column (str): Name of the column to store computed oversteer values.

    Returns:
        OrderedDict[str, List[str]]: Updated data with the new oversteer column.
    """
    nval = len(next(iter(data.values()))) if data else 0
    data[oversteer_column] = []
    for i in range(nval):
        if i == 0:
            over_val = 0.0
        else:
            rot = float(data[rotation_speed_column][i])
            gyro_z = float(data[gyro_z_column][i])
            over_val = rot + gyro_z # gyro_z is typically negative for clockwise rotation
        data[oversteer_column].append(format_heading(over_val))
    return data

def compute_rotation_speed(
    data: OrderedDict[str, List[str]],
    rotation_speed_column: str,
    heading_column: str,
    time_column: str,
    smoothing_window: int
) -> OrderedDict[str, List[str]]:
    """
    Compute rotation speed from heading and time columns.

    Parameters:
        data (OrderedDict[str, List[str]]): Input data with existing columns.
        rotation_speed_column (str): Name of the column to store computed rotation speed values.
        heading_column (str): Name of the column containing heading values.
        time_column (str): Name of the column containing time values.
        smoothing_window (int): Size of the smoothing window for moving average.

    Returns:
        OrderedDict[str, List[str]]: Updated data with the new rotation speed column.
    """
    nval = len(next(iter(data.values()))) if data else 0
    raw_rotation_speeds: List[float] = []
    for i in range(nval):
        if i == 0:
            raw_rotation_speeds.append(0.0)
        else:
            prev_heading = float(data[heading_column][i - 1])
            curr_heading = float(data[heading_column][i])
            # shortest angle difference in degrees (-180, +180]
            delta_heading = (curr_heading - prev_heading + 540.0) % 360.0 - 180.0
            prev_time = hhmmsscc_to_milliseconds(data[time_column][i - 1]) / 1000.0
            curr_time = hhmmsscc_to_milliseconds(data[time_column][i]) / 1000.0
            dt = curr_time - prev_time if curr_time != prev_time else 1e-6
            raw_rotation_speeds.append(delta_heading / dt)
    # smoothing (moving average)
    window = max(1, int(smoothing_window))
    smoothed: List[str] = []
    for i in range(nval):
        start = max(0, i - window // 2)
        end = min(nval, i + window // 2 + 1)
        smoothed_val = sum(raw_rotation_speeds[start:end]) / (end - start)
        smoothed.append(f"{smoothed_val:.2f}")
    data[rotation_speed_column] = smoothed
    return data

def gps_heading_function(
    data: OrderedDict[str, List[str]],
    heading_column: str,
    lat_column: str,
    long_column: str,
    smoothing_window: int
) -> OrderedDict[str, List[str]]:
    """
    Compute GPS heading from latitude and longitude columns.
    
    Parameters:
        data (OrderedDict[str, List[str]]): Input data with existing columns.
        heading_column (str): Name of the column to store computed heading values.
        lat_column (str): Name of the column containing latitude values.
        long_column (str): Name of the column containing longitude values.
        smoothing_window (int): Size of the smoothing window for moving average.

    Returns:
        OrderedDict[str, List[str]]: Updated data with the new heading column.
    """
    nval = len(next(iter(data.values()))) if data else 0
    if heading_column not in data:
        raw_headings = []
        for i in range(nval):
            if i == 0:
                heading = 0.0
            else:
                lat1 = float(data[lat_column][i - 1])
                lon1 = float(data[long_column][i - 1])
                lat2 = float(data[lat_column][i])
                lon2 = float(data[long_column][i])
                heading = compute_heading(lat1, lon1, lat2, lon2)
            raw_headings.append(heading)

        # Apply moving average smoothing
        if len(raw_headings) == 0:
            smoothed_headings = []
        else:
            # convert degrees -> radians, build unit phasors
            raw_rad = np.deg2rad(np.asarray(raw_headings, dtype=float))
            phasors = np.exp(1j * raw_rad)
            # uniform kernel and convolution (same length output)
            kernel = np.ones(smoothing_window, dtype=float) / smoothing_window
            smoothed_phasors = np.convolve(phasors, kernel, mode='same')
            # extract angle, convert to degrees and normalize
            smoothed_headings = ((np.degrees(np.angle(smoothed_phasors)) + 360.0) % 360.0).tolist()

        data[heading_column] = [format_heading(h) for h in smoothed_headings]

    return data

def add_avitime_column(
    data: OrderedDict[str, List[str]],
    start_sync_time: int,
    time_column: str
) -> OrderedDict[str, List[str]]:
    """
    Compute and add an 'avitime' column to the data section.

    Parameters:
        data (OrderedDict[str, List[str]]): Current data mapping column->list-of-values.
        start_sync_time (int): Initial avitime value to use for the first row (milliseconds).

    Returns:
        OrderedDict[str, List[str]]: The updated data mapping including 'avitime'.

    Notes:
        - Assumes time_column contains values in HHMMSS.CC format and uses hhmmsscc_to_milliseconds()
            to obtain per-row timestamps in milliseconds.
        - Each avitime value is formatted as a zero-padded string of length 9.
    """
    if 'avitime' not in data:
        data['avitime'] = []
        nval = len(next(iter(data.values()))) if data else 0
        for i in range(nval):
            if i == 0:
                avitime = start_sync_time
            else:
                prev_time_ms = hhmmsscc_to_milliseconds(data[time_column][i - 1])
                curr_time_ms = hhmmsscc_to_milliseconds(data[time_column][i])
                avitime += curr_time_ms - prev_time_ms
            avitime_str = pad_with_zeros(avitime, 9)
            data['avitime'].append(avitime_str)
        return data

def compute_fuel_consumption_avg(
    data: OrderedDict[str, List[str]],
    fuel_consumption_column: str,
    rpm_column: str,
    throttle_column: str,
    intake_temp_column: str,
    time_column: str,
    engine_displacement_cc: int,
    ve: float,
    lambda_value: float,
    time_window_sec: int
) -> OrderedDict[str, List[str]]:
    """
    Compute average fuel consumption over a time window in liters per minute.

    Parameters:
        data (OrderedDict[str, List[str]]): Input data with existing columns.
        fuel_consumption_column (str): Name of the column to store computed fuel consumption average values.
        rpm_column (str): Name of the column containing RPM values.
        throttle_column (str): Name of the column containing throttle position values (0-100).
        intake_temp_column (str): Name of the column containing intake air temperature values (°C).
        time_column (str): Name of the column containing time values.
        engine_displacement_cc (int): Engine displacement in cubic centimeters.
        ve (float): Volumetric efficiency (range 0.7-0.95).
        lambda_value (float): Air-fuel ratio (1.0 for stoichiometric).
        time_window_sec (int): Time window in seconds for averaging.

    Returns:
        OrderedDict[str, List[str]]: Updated data with new fuel consumption columns.
    """
    nval = len(next(iter(data.values()))) if data else 0
    fuel_consumption_inst = []
    data[fuel_consumption_column] = []
    
    for i in range(nval):
        # Estimate instantaneous fuel consumption
        rpm = float(data[rpm_column][i])
        throttle = float(data[throttle_column][i])
        intake_temp = float(data[intake_temp_column][i])
        
        inst_fuel_consumption = estimate_instant_fuel_consumption(
            rpm, throttle, intake_temp, engine_displacement_cc, ve, lambda_value
        )
        fuel_consumption_inst.append(f"{inst_fuel_consumption:.4f}")
        
        # Compute average over time window
        if i == 0:
            avg_fuel_consumption = inst_fuel_consumption
        else:
            curr_time = hhmmsscc_to_milliseconds(data[time_column][i]) / 1000.0
            window_start_time = curr_time - time_window_sec

            # Collect instantaneous fuel consumption values within the time window
            fuel_consumption_values = []
            for j in range(i, -1, -1):
                row_time = hhmmsscc_to_milliseconds(data[time_column][j]) / 1000.0
                if row_time < window_start_time:
                    break
                fuel_consumption_values.append(float(fuel_consumption_inst[j]))

            # Compute average
            avg_fuel_consumption = sum(fuel_consumption_values) / len(fuel_consumption_values) if fuel_consumption_values else 0.0

        data[fuel_consumption_column].append(f"{avg_fuel_consumption:.4f}")
    
    return data