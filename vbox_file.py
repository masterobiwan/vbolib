from collections import OrderedDict

class VboxFile:

    def __init__(self, filepath):
        self.filepath = filepath

        sections = OrderedDict()
        section = None

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                line_stripped = line.strip()
                if line_stripped.startswith('[') and line_stripped.endswith(']'):
                    section = line_stripped.lower()
                    sections[section] = []
                    continue
                if section and line != '':
                    sections[section].append(line)
                elif line != '':
                    # For lines before any section (file header)
                    sections.setdefault('file_header', []).append(line)

        # Parse header columns
        header_columns = sections.get('[header]', [])
        # Parse column names
        column_names = []
        if '[column names]' in sections and sections['[column names]']:
            column_names = sections['[column names]'][0].split()

        self.sections = sections
        self.header_columns = header_columns
        self.column_names = column_names

    def write(self, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            for section, lines in self.sections.items():
                if section == 'file_header':
                    for line in lines:
                        f.write(line + '\n')
                    f.write('\n')
                    continue
                
                # The [section] header
                f.write(section + '\n')

                if section == '[column names]' and self.column_names is not None:
                    f.write(' '.join(self.column_names) + '\n')
                    # Add exactly one blank line after [column names]
                    f.write('\n')
                elif section == '[header]' and self.header_columns is not None:
                    for line in self.header_columns:
                        f.write(line + '\n')
                    f.write('\n')
                else:
                    for line in lines:
                        f.write(line + '\n')
                    if section != '[data]':
                        f.write('\n')

    def __move_section(self, section_to_move, after_section):
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

    def __get_column_value(self, line, column_name):
        """
        Get the value of a specific column from a data line.
        """
        columns = line.split()
        if column_name in self.column_names:
            index = self.column_names.index(column_name)
            return columns[index] if index < len(columns) else None
        return None

    def add_avi_section(self, name, format, number, start_sync_time):
        if '[avi]' not in self.sections:
            self.sections['[avi]'] = []
            self.sections['[avi]'].append(f'{name}')
            self.sections['[avi]'].append(f'{format}')

        # Add 'avifileindex' to [header] section if not present
        if 'avifileindex' not in [h.strip() for h in self.header_columns]:
            self.header_columns.append('avifileindex')

        # Add 'avifileindex' to [column names] section if not present
        if 'avifileindex' not in self.column_names:
            self.column_names.append('avifileindex')

            # Add 'avifileindex' column to data
            number_str = pad_with_zeros(number, 4)
            self.add_constant_column('avifileindex', 'avifileindex', str(number_str))

        # Add 'avitime' to [header] section if not present
        if 'avisynctime' not in [h.strip() for h in self.header_columns]:
            self.header_columns.append('avisynctime')

        # Add 'avitime' to [column names] section if not present
        if 'avitime' not in self.column_names:
            self.column_names.append('avitime')

            # Add 'avitime' column to data
            i = 0
            prev_time = None
            for line in self.sections['[data]']:
                time_value_ms = hhmmsscc_to_milliseconds(self.__get_column_value(line, 'time'))
                if prev_time is not None:
                    avitime += time_value_ms - prev_time
                else:
                    avitime = start_sync_time
                avitime_str = pad_with_zeros(avitime, 9)
                new_line = f"{line} {avitime_str}"
                self.sections['[data]'][i] = new_line
                i += 1
                prev_time = time_value_ms


        self.__move_section('[avi]', '[laptiming]')

    def remove_column(self, header_column_name, data_column_name):
        """
        Remove a column from the data section and update relevant metadata.
        """
        if data_column_name in self.column_names:
            self.column_names.remove(data_column_name)

        if header_column_name in [h.strip() for h in self.header_columns]:
            self.header_columns.remove(header_column_name)

        # Remove the column from the data section
        for i, line in enumerate(self.sections['[data]']):
            columns = line.split()
            if data_column_name in self.column_names:
                index = self.column_names.index(data_column_name)
                if index < len(columns):
                    columns.pop(index)
            self.sections['[data]'][i] = ' '.join(columns)

    def add_constant_column(self, header_column_name, data_column_name, constant_value):
        """
        Add a constant column to the data section.
        """
        if header_column_name not in [h.strip() for h in self.header_columns]:
            self.header_columns.append(header_column_name)

        if data_column_name not in self.column_names:
            self.column_names.append(data_column_name)

        # Add the constant value to each line in the data section
        for i, line in enumerate(self.sections['[data]']):
            self.sections['[data]'][i] = f"{line} {constant_value}"

def pad_with_zeros(number, total_length):
    return str(number).zfill(total_length)

def hhmmsscc_to_milliseconds(timestr):
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