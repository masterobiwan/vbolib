from vbox_file import VboxFile


# Parse the VBOX file
filepath = r'C:\Users\Benoît\Documents\vbox\2025-08-22\RaceBox Track Sessionon 22-08-2025 10-45.vbo'
vbox_file = VboxFile(filepath)

# Add avi file section
vbox_file.add_avi_section('video_', 'mp4', 1, 3355)

# Remove column
# vbox_file.remove_column('VertAcc', 'VertAcc')
# vbox_file.add_constant_column('NewHeaderCol', 'NewDataCol', '42')

# Write back (overwrites original file)
filepath_new = r'C:\Users\Benoît\Documents\vbox\2025-08-22\RaceBox Track Sessionon 22-08-2025 10-45_modified.vbo'
vbox_file.write(filepath_new)