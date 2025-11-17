def estimate_instant_fuel_consumption(
    rpm: float,
    throttle: float,
    intake_temp: float,
    engine_displacement_cc: int,
    ve: float,
    lambda_value: float
) -> float:
    """
    Estimate instantaneous fuel consumption based on engine parameters.

    Parameters:
        rpm (float): Engine speed in revolutions per minute.
        throttle (float): Throttle position (0-100).
        intake_temp (float): Intake air temperature in Celsius.
        engine_displacement_cc (int): Engine displacement in cubic centimeters.
        ve (float): Volumetric efficiency (range 0.7-0.95).
        lambda_value (float): Air-fuel ratio (1.0 for stoichiometric).

    Returns:
        float: Instantaneous fuel consumption in liters per minute.
    """
    if rpm == 0:
        return 0.0
    
    standard_air_density = 1.225  # kg/m³ at 15°C and sea level
    kelvin_conversion = 273.15
    reference_temp_celsius = 15.0
    rpm_to_firings_factor = 120.0  # 4-stroke engine: 2 revolutions per power stroke
    gasoline_density = 745.0  # g/L
    
    # Air density correction for temperature (g/L) using Ideal Gas Law
    air_density = standard_air_density * ((reference_temp_celsius + kelvin_conversion) / (kelvin_conversion + intake_temp))

    # Air mass entering cylinders per revolution (g)
    displacement_liters = engine_displacement_cc / 1000
    throttle_ratio = throttle / 100
    
    # Total intake volume available
    total_intake_volume = ve * displacement_liters * throttle_ratio
    
    # Fuel volume is negligible compared to air volume, so we approximate:
    air_mass_per_rev = total_intake_volume * air_density
    
    # Fuel mass entering cylinders per revolution (g)
    fuel_mass_per_rev = air_mass_per_rev / (14.7 * lambda_value)
    
    # Fuel consumption per second (g/s)
    fuel_consumption_g_per_sec = fuel_mass_per_rev * (rpm / rpm_to_firings_factor)

    return fuel_consumption_g_per_sec / gasoline_density * 60  # Convert to liters per minute