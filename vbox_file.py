from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Any
from functools import partial

class VboxFile:

    def __init__(self, filepath: str) -> None:
        """
        Initialize VboxFile with the given file path.
        Save all sections in plain text except the ones we intend to modify.
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
        Write the VBOX file content to the specified file path.
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
        Move section_to_move in sections OrderedDict to be after after_section.
        """
        if section_to_move not in self.sections or after_section not in self.sections:
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

    def add_avi_section(self, name: str, format: str, number: int, start_sync_time: int) -> None:
        """
        Add an [avi] section to the VBOX file and also the required related columns:
        - avifileindex
        - avitime
        """
        if '[avi]' not in self.sections:
            self.sections['[avi]'] = []
            self.sections['[avi]'].append(f'{name}')
            self.sections['[avi]'].append(f'{format}')

        def add_avitime_column(data: OrderedDict[str, List[str]], start_sync_time: int) -> OrderedDict[str, List[str]]:
            """
            Add 'avitime' column to the data section if it does not exists.
            Computed using the difference between consecutive time values.
            """
            if 'avitime' not in data:
                data['avitime'] = []
                prev_time: Optional[int] = None
                for i in range(self.nval):
                    time_value_ms = hhmmsscc_to_milliseconds(data['time'][i])
                    if prev_time is not None:
                        avitime += time_value_ms - prev_time
                    else:
                        avitime = start_sync_time
                    avitime_str = pad_with_zeros(avitime, 9)
                    data['avitime'].append(avitime_str)
                    prev_time = time_value_ms
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
        Remove a column from the data section and update relevant metadata.
        """
        if data_column_name in self.sections['[column names]']:
            self.sections['[column names]'].remove(data_column_name)

        if header_column_name in self.sections['[header]']:
            self.sections['[header]'].remove(header_column_name)

        # Remove the column from the data section
        if data_column_name in self.sections['[data]']:
            self.sections['[data]'].pop(data_column_name)

    def add_constant_column(self, header_column_name: str, data_column_name: str, constant_value: str) -> None:
        """
        Add a constant column to the data section.
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
        Add a computed column to the data section using the compute function.
        The compute function takes the data ordered dict as input and must
        return the updated data ordered dict including the new column.
        """
        if header_column_name not in self.sections['[header]']:
            self.sections['[header]'].append(header_column_name)

        self.sections['[data]'] = compute_function(self.sections['[data]'])

        # Find out which column has been added
        new_columns = [col for col in self.sections['[data]'] if col not in self.sections['[column names]']]
        if len(new_columns) != 1:
            raise ValueError("Computed column must add exactly one new column.")
        else:
            self.sections['[column names]'].append(new_columns[0])

def pad_with_zeros(number: int, total_length: int) -> str:
    return str(number).zfill(total_length)

def hhmmsscc_to_milliseconds(timestr: str) -> int:
    # Ensure string is zero-padded and split into parts
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