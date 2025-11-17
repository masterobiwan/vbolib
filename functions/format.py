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