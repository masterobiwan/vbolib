from vbox_file import VboFile, format_heading, hhmmsscc_to_milliseconds


# Parse the VBOX file
filepath = r'C:\Users\Benoît\Documents\vbox\2025-10-04\session_20251004_114309_silverstone_international.vbo'
vbox_file = VboFile(filepath)

# Add avi file section
# vbox_file.add_avi_section('video_', 'MOV', 3, -300000)

# Remove column
# vbox_file.remove_column('VertAcc', 'VertAcc')

# Add columns
# vbox_file.add_constant_column('NewHeaderCol', 'NewDataCol', '42')
vbox_file.add_gps_heading_column()

def rotation_speed_from_heading_gps(data):
    nval = len(data['time'])
    if 'rotation_speed_deg_per_s' not in data:
        raw_rotation_speeds = []
        for i in range(nval):
            if i == 0:
                rotation_speed = 0.0
            else:
                # Compute heading difference, accounting for wrap-around at 360°
                prev_heading = float(data['heading_gps'][i - 1])
                curr_heading = float(data['heading_gps'][i])
                delta_heading = (curr_heading - prev_heading + 540) % 360 - 180  # shortest angle diff
                # Compute time difference in seconds
                prev_time = hhmmsscc_to_milliseconds(data['time'][i - 1]) / 1000.0
                curr_time = hhmmsscc_to_milliseconds(data['time'][i]) / 1000.0
                dt = curr_time - prev_time if curr_time != prev_time else 1e-6
                rotation_speed = delta_heading / dt
            raw_rotation_speeds.append(rotation_speed)
        # Apply moving average smoothing (window size = 5)
        window = 10
        smoothed = []
        for i in range(nval):
            start = max(0, i - window // 2)
            end = min(nval, i + window // 2 + 1)
            smoothed_val = sum(raw_rotation_speeds[start:end]) / (end - start)
            smoothed.append(f"{smoothed_val:.2f}")
        data['rotation_speed_deg_per_s'] = smoothed
    return data

vbox_file.add_computed_column('rotation_speed_deg_per_s', rotation_speed_from_heading_gps)

def oversteer(data):
    nval = len(data['time'])
    if 'oversteer' not in data:
        data['oversteer'] = []
        for i in range(nval):
            if i == 0:
                oversteer = 0.0
            else:
                oversteer = float(data['rotation_speed_deg_per_s'][i]) + float(data['z_rate_of_rotation-gyro'][i])
            data['oversteer'].append(format_heading(oversteer))
        return data

vbox_file.add_computed_column('oversteer', oversteer)

# Write to new file
filepath_new = r'C:\Users\Benoît\Documents\vbox\2025-10-04\session_20251004_114309_silverstone_international_modified.vbo'
vbox_file.write(filepath_new)