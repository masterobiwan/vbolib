from collections import OrderedDict
import logging
from typing import Callable, List, Optional, Any
from functools import partial

from functions.format import pad_with_zeros
from functions.compute import compute_oversteer, compute_rotation_speed, gps_heading_function, add_avitime_column

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

        # Add 'avifileindex' to [column names] section if not present
        if 'avifileindex' not in self.sections['[data]']:
            number_str = pad_with_zeros(number, 4)
            self.add_constant_column('avifileindex', 'avifileindex', str(number_str))

        if 'avisynctime' not in self.sections['[data]']:
            self.add_computed_column(
                'avisynctime',
                partial(
                    add_avitime_column,
                    start_sync_time=start_sync_time,
                    time_column=time_column
                )
            )

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

        self.add_computed_column(
            heading_column,
            partial(
                gps_heading_function,
                heading_column=heading_column,
                lat_column=lat_column,
                long_column=long_column,
                smoothing_window=smoothing_window
            )
        )

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

        self.add_computed_column(
            rotation_speed_column,
            partial(
                compute_rotation_speed,
                rotation_speed_column=rotation_speed_column,
                heading_column=heading_column,
                time_column=time_column,
                smoothing_window=smoothing_window
            )
        )

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

        self.add_computed_column(
            oversteer_column,
            partial(
                compute_oversteer,
                rotation_speed_column=rotation_speed_column,
                gyro_z_column=gyro_z_column,
                oversteer_column=oversteer_column
            )
        )

        if remove_rotation_column:
            self.remove_column(rotation_speed_column, rotation_speed_column)