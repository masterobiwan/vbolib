from collections import OrderedDict
import logging
from typing import Callable, List, Optional, Any
from functools import partial
import math
import numpy as np

class VboFile:
    """
    Parser, editor, and writer for Racelogic/VBox .vbo files.

    Attributes:
        filepath (str): Path to the source .vbo file.
        sections (OrderedDict[str, Any]): Parsed sections of the file. Section names are keys
            (including their surrounding brackets, e.g. '[data]') and values contain the raw
            content for that section (lists of lines or OrderedDict for data).
        nval (int): Number of data rows parsed from the [data] section.
    """

    def __init__(self, filepath: str) -> None:
        """
        Initialize a VboFile by reading and parsing a .vbo file.

        Parameters:
            filepath (str): Path to the .vbo file to parse.

        Raises:
            ValueError: If multiple [column names] lines are found.
        """

        self.filepath: str = filepath
        self.sections: OrderedDict[str, Any] = OrderedDict()
        self.nval: int = 0
        section: Optional[str] = None

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                line_stripped = line.strip()
                if line_stripped.startswith('[') and line_stripped.endswith(']'):
                    section = line_stripped.lower()
                    if section != '[data]':
                        self.sections[section] = []
                    else:
                        self.sections[section] = OrderedDict()
                    continue
                if line != '':
                    if section == '[column names]':
                        if '[column names]' in self.sections and not self.sections['[column names]']:
                            self.sections['[column names]'] = line.split(' ')
                        else:
                            raise ValueError("Multiple [column names] lines found.")
                    elif section == '[data]':
                        if '[column names]' in self.sections and self.sections['[column names]']:
                            self.nval += 1
                            for i, col in enumerate(self.sections['[column names]']):
                                line_list = line.split(' ')
                                if col in self.sections[section]:
                                    self.sections[section][col].append(line_list[i])
                                else:
                                    self.sections[section][col] = [line_list[i]]
                    elif section:
                        self.sections[section].append(line)
                    else:
                        # For lines before any section (file header)
                        self.sections.setdefault('file_header', []).append(line)

    def write(self, filepath: str) -> None:
        """
        Write the VBOX content back to a file.

        Parameters:
            filepath (str): Destination file path where the .vbo content will be written.
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            for section, lines in self.sections.items():
                if section == 'file_header':
                    for line in lines:
                        f.write(line + '\n')
                    f.write('\n')
                    continue
                
                # The [section] header
                f.write(section + '\n')

                if section == '[column names]' and self.sections[section] is not None:
                    f.write(' '.join(self.sections[section]) + '\n')
                    # Add exactly one blank line after [column names]
                    f.write('\n')
                elif section == '[data]' and self.sections['[column names]'] is not None:
                    for i in range(self.nval):
                        line = []
                        if self.sections[section]:
                            for col in self.sections[section]:
                                line.append(self.sections[section][col][i])
                            f.write(' '.join(line) + '\n')
                elif section == '[header]' and self.sections[section] is not None:
                    for line in self.sections[section]:
                        f.write(line + '\n')
                    f.write('\n')
                else:
                    for line in lines:
                        f.write(line + '\n')
                    f.write('\n')

    def __move_section(self, section_to_move: str, after_section: str) -> None:
        """
        Move a section in the internal OrderedDict to a new position.

        Parameters:
            section_to_move (str): Section key to move (including brackets), e.g. '[avi]'.
            after_section (str): The section key after which section_to_move should be inserted.

        Notes:
            - If either key is missing, the method does nothing.
        """

        if section_to_move not in self.sections or after_section not in self.sections:
            logging.warning(f"Cannot move section {section_to_move} after {after_section}: one of the sections is missing.")
            return

        items = list(self.sections.items())
        # Remove the section to move
        section_item = None
        for i, (k, v) in enumerate(items):
            if k == section_to_move:
                section_item = items.pop(i)
                break
        # Find the index after which to insert
        for i, (k, v) in enumerate(items):
            if k == after_section:
                items.insert(i + 1, section_item)
                break
        # Rebuild OrderedDict
        self.sections = OrderedDict(items)

    def add_avi_section(self, video_file_name: str, format: str, number: int, start_sync_time: int, time_column: str = 'time') -> None:
        """
        Add an [avi] section and required data/header columns.

        Parameters:
            video_file_name (str): Base name for the video file to write into the [avi] section.
            format (str): Video format string (e.g. 'mp4').
            number (int): Integer index to store in the 'avifileindex' data column.
            start_sync_time (int): Initial avitime value (typically milliseconds) used to sync the first frame.
            time_column (str): Name of the time column in the data section (default 'time').
        """
        
        if '[avi]' not in self.sections:
            self.sections['[avi]'] = []
            self.sections['[avi]'].append(f'{video_file_name}')
            self.sections['[avi]'].append(f'{format}')

        def add_avitime_column(data: OrderedDict[str, List[str]], start_sync_time: int) -> OrderedDict[str, List[str]]:
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
            # ...existing code...
            if 'avitime' not in data:
                data['avitime'] = []
                for i in range(self.nval):
                    if i == 0:
                        avitime = start_sync_time
                    else:
                        prev_time_ms = hhmmsscc_to_milliseconds(data[time_column][i - 1])
                        curr_time_ms = hhmmsscc_to_milliseconds(data[time_column][i])
                        avitime += curr_time_ms - prev_time_ms
                    avitime_str = pad_with_zeros(avitime, 9)
                    data['avitime'].append(avitime_str)
                return data

        # Add 'avifileindex' to [column names] section if not present
        if 'avifileindex' not in self.sections['[data]']:
            number_str = pad_with_zeros(number, 4)
            self.add_constant_column('avifileindex', 'avifileindex', str(number_str))

        if 'avisynctime' not in self.sections['[data]']:
            self.add_computed_column('avisynctime', partial(add_avitime_column, start_sync_time=start_sync_time))

        self.__move_section('[avi]', '[laptiming]')

    def remove_column(self, header_column_name: str, data_column_name: str) -> None:
        """
        Remove a column from header, column names and data sections.

        Parameters:
            header_column_name (str): The human-readable header entry to remove (e.g. 'heading').
            data_column_name (str): The data column key to remove from [column names] and [data].
        """
        
        if data_column_name in self.sections['[column names]']:
            self.sections['[column names]'].remove(data_column_name)

        if header_column_name in self.sections['[header]']:
            self.sections['[header]'].remove(header_column_name)

        if data_column_name in self.sections['[data]']:
            self.sections['[data]'].pop(data_column_name)

    def add_constant_column(self, header_column_name: str, data_column_name: str, constant_value: str) -> None:
        """
        Add a constant-valued column to the data section.

        Parameters:
            header_column_name (str): Header entry to add to the '[header]' section.
            data_column_name (str): Column key to add to the '[data]' mapping and '[column names]'.
            constant_value (str): String value to use for every row in the new column.
        """

        def constant_function(data: OrderedDict[str, List[str]]) -> OrderedDict[str, List[str]]:
            data[data_column_name] = [constant_value] * self.nval
            return data

        if data_column_name not in self.sections['[data]']:
            self.add_computed_column(header_column_name, constant_function)

    def add_computed_column(
        self,
        header_column_name: str,
        compute_function: Callable[[OrderedDict[str, List[str]]], OrderedDict[str, List[str]]]
    ) -> None:
        """
        Add a computed column by applying a compute function to the current data.

        Parameters:
            header_column_name (str): Header name to add to the '[header]' section.
            compute_function (Callable): Function that accepts the current data OrderedDict and
                returns the updated data OrderedDict including exactly one new data column.

        Raises:
            ValueError: If the computed column does not add exactly one new column.
            ValueError: If the header column already exists.

        Help on compute_function:
            The compute_function should have the signature:
                def compute_function(data: OrderedDict[str, List[str]]) -> OrderedDict[str, List[str]]:
            It should add exactly one new column to the data mapping and return the updated mapping.
            The new column should have the same number of rows as existing columns.

            data OrderedDict details:
                Keys: data column names (strings). Order matters — iteration order defines the field order when writing rows.
                Values: lists of strings. Each string is the textual representation as it will be written to the .vbo file (keep leading zeros, signs, width, decimals, etc.).
        """
        
        if header_column_name not in self.sections['[header]']:
            self.sections['[header]'].append(header_column_name)
        else:
            raise ValueError(f"Header column {header_column_name} already exists in headers.")

        self.sections['[data]'] = compute_function(self.sections['[data]'])

        # Find out which column has been added
        new_columns = [col for col in self.sections['[data]'] if col not in self.sections['[column names]']]
        if len(new_columns) != 1:
            raise ValueError("Computed column must add exactly one new column.")
        else:
            self.sections['[column names]'].append(new_columns[0])

    def add_gps_heading_column(self, heading_column: str = 'heading_gps', long_column: str = 'long', lat_column: str = 'lat', smoothing_window: int = 5) -> None:
        """
        Compute and add a GPS-derived heading column.

        Parameters:
            heading_column (str): Name of the new heading data column (default 'heading_gps').
            long_col (str): Name of the longitude column in data (default 'long').
            lat_col (str): Name of the latitude column in data (default 'lat').
            smoothing_window (int): Moving-average window size for heading smoothing (odd recommended). Defaults to 5.
        """

        if heading_column in self.sections['[data]']:
            logging.warning(f"Column {heading_column} already exists. Skipping GPS heading computation.")
            return
        
        def gps_heading_function(data: OrderedDict[str, List[str]]) -> OrderedDict[str, List[str]]:
            if heading_column not in data:
                raw_headings = []
                for i in range(self.nval):
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
        

        self.add_computed_column(heading_column, gps_heading_function)

    def add_rotation_speed_from_heading_column(
        self,
        time_column: str = 'time',
        heading_column: str = 'heading_gps',
        rotation_speed_column: str = 'rotation_speed_deg_per_s',
        smoothing_window: int = 9
    ) -> None:
        """
        Add a rotation speed (yaw rate) column computed from heading column.

        Parameters:
            time_column (str): Name of the time column in HHMMSS.CC format (default 'time').
            heading_column (str): Name of the heading column to read (degrees, default 'heading').
            rotation_speed_column (str): Name of the data column to create (default 'rotation_speed_deg_per_s').
            smoothing_window (int): Moving-average window size (odd recommended). Defaults to 9.

        Raises:
            KeyError: If time_column is missing from the data.
        
        Notes for compute_function implementers/users:
            - The method will raise a KeyError if heading_column or time_column are missing from the data.
            - The returned data mapping will include exactly one new column (rotation_speed_column) with string values,
              each list having the same length self.nval.
        """

        if rotation_speed_column in self.sections['[data]']:
            logging.warning(f"Column {rotation_speed_column} already exists. Skipping rotation speed computation.")
            return
        
        if time_column not in self.sections['[data]']:
            raise KeyError(f"Time column '{time_column}' not found in data.")
        
        remove_heading_column = False
        if heading_column not in self.sections['[data]']:
            self.add_gps_heading_column(heading_column=heading_column)
            remove_heading_column = True

        def compute_rotation_speed(data: OrderedDict[str, List[str]]) -> OrderedDict[str, List[str]]:
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

        self.add_computed_column(rotation_speed_column, compute_rotation_speed)

        if remove_heading_column:
            self.remove_column(heading_column, heading_column)

    def add_oversteer_column(
        self,
        rotation_speed_column: str = 'rotation_speed_deg_per_s',
        gyro_z_column: str = 'z_rate_of_rotation-gyro',
        oversteer_column: str = 'oversteer'
    ) -> None:
        """
        Add an 'oversteer' computed column representing the difference between GPS based rotation to gyroscope z-axis rotation.
        Unit: deg/s.
        Convention:
            - positive value indicates oversteer.
            - negative value indicates understeer.

        Parameters:
            rotation_speed_column (str): Name of the rotation speed column in deg/s (default 'rotation_speed_deg_per_s').
            gyro_z_column (str): Name of the z-rotation gyroscope column (default 'z_rate_of_rotation-gyro').
            oversteer_column (str): Name of the oversteer column to create (default 'oversteer').

        Raises:
            KeyError: If gyro_z_column is missing from the data.

        Notes:
            - Both input columns must exist in the data OrderedDict; otherwise KeyError is raised.
        """

        if oversteer_column in self.sections['[data]']:
            logging.warning(f"Column {oversteer_column} already exists. Skipping oversteer computation.")
            return
        
        if gyro_z_column not in self.sections['[data]']:
            raise KeyError(f"Gyro Z column '{gyro_z_column}' not found in data.")
        
        remove_rotation_column = False
        if rotation_speed_column not in self.sections['[data]']:
            self.add_rotation_speed_from_heading_column(rotation_speed_column=rotation_speed_column)
            remove_rotation_column = True

        def compute_oversteer(data: OrderedDict[str, List[str]]) -> OrderedDict[str, List[str]]:
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

        self.add_computed_column(oversteer_column, compute_oversteer)

        if remove_rotation_column:
            self.remove_column(rotation_speed_column, rotation_speed_column)


def pad_with_zeros(number: int, total_length: int) -> str:
    """
    Zero-pad an integer to a fixed width.

    Parameters:
        number (int): Integer to format.
        total_length (int): Total number of digits desired (leading zeros added as needed).

    Returns:
        str: Zero-padded decimal string.
    """
    return str(number).zfill(total_length)

def format_heading(heading: float) -> str:
    """
    Format heading value for VBO output.

    Parameters:
        heading (float): Heading in degrees.

    Returns:
        str: Formatted heading string with 2 decimal places and at least 5 characters,
             zero-padded as needed (example '012.345').
    """
    return f"{heading:05.2f}"

def hhmmsscc_to_milliseconds(timestr: str) -> int:
    """
    Convert a time string in HHMMSS.CC format (hours, minutes, seconds, centiseconds)
    to milliseconds.

    Parameters:
        timestr (str): Time string in the format 'HHMMSS.CC' (centiseconds). Leading zeros are allowed.

    Returns:
        int: Total milliseconds corresponding to the input time.

    Example:
        '094559.96' -> (9 hours, 45 minutes, 59.96 seconds) -> 34,199,960 ms
    """
    # ...existing code...
    timestr = timestr.strip()
    if '.' in timestr:
        main, centis = timestr.split('.')
    else:
        main, centis = timestr, '00'
    main = main.zfill(6)
    hours = int(main[:2])
    minutes = int(main[2:4])
    seconds = int(main[4:6])
    centiseconds = int(centis.ljust(2, '0'))  # pad right if needed

    total_ms = (
        hours * 3600 * 1000 +
        minutes * 60 * 1000 +
        seconds * 1000 +
        centiseconds * 10
    )
    return total_ms