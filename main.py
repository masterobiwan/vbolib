from vbolib import VboFile, format_heading, hhmmsscc_to_milliseconds


# Parse the VBOX file
filepath = r'C:\Users\Benoît\Documents\vbox\2025-10-03\session_20251003_151644_silverstone_international.vbo'
vbo_file = VboFile(filepath)

# Add avi file section
# vbo_file.add_avi_section('video_', 'MOV', 3, -300000)

# Remove column
# vbo_file.remove_column('VertAcc', 'VertAcc')

# Add columns
# vbo_file.add_constant_column('NewHeaderCol', 'NewDataCol', '42')

vbo_file.add_oversteer_column()

# Write to new file
filepath_new = r'C:\Users\Benoît\Documents\vbox\2025-10-03\session_20251003_151644_silverstone_international_modified.vbo'
vbo_file.write(filepath_new)