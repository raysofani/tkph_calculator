import numpy as np

# Terrain adjustment factors (based on terrain type)
TERRAIN_FACTORS = {
    "Flat": 1.0,
    "Inclined": 0.9,
    "Rocky": 0.8,
    "Muddy": 0.7
}

# Tire wear damage adjustment factors
def get_tire_damage_factor(wear_percentage):
    if wear_percentage <= 10:
        return 1.0  # Minimal Wear
    elif 10 < wear_percentage <= 25:
        return 0.95  # Light Wear
    elif 25 < wear_percentage <= 50:
        return 0.85  # Moderate Wear
    elif 50 < wear_percentage <= 75:
        return 0.7   # Severe Wear
    elif 75 < wear_percentage <= 100:
        return 0.5   # Critical Wear

# Function to calculate mean tire load
def calculate_mean_tyre_load(tyre_load_empty, tyre_load_fully_loaded):
    return (tyre_load_empty + tyre_load_fully_loaded) / 2

# Function to calculate average speed
def calculate_average_speed(round_trip_distances, cycles_per_shift, total_shift_hours):
    # Remove outliers from round trip distances
    round_trip_distances = remove_outliers(round_trip_distances)
    
    # Calculate mean of round trip distances
    mean_distance = np.mean(round_trip_distances)
    
    # Calculate average speed
    average_speed = (mean_distance * cycles_per_shift) / total_shift_hours
    return average_speed

# Function to remove outliers using the Interquartile Range (IQR) method
def remove_outliers(data):
    Q1 = np.percentile(data, 25)
    Q3 = np.percentile(data, 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return [x for x in data if lower_bound <= x <= upper_bound]

# Function to calculate TKPH
def calculate_tkph(payload_loaded, distance_loaded, cycle_time, terrain_type, tire_wear_percentage):
    # Calculate mean tire load
    tyre_load_empty = float(input("Enter tire load (empty): "))
    tyre_load_fully_loaded = float(input("Enter tire load (fully loaded): "))
    mean_tyre_load = calculate_mean_tyre_load(tyre_load_empty, tyre_load_fully_loaded)
    
    # Calculate average speed
    round_trip_distances = list(map(float, input("Enter round trip distances (comma-separated): ").split(',')))
    cycles_per_shift = int(input("Enter number of cycles per shift: "))
    total_shift_hours = float(input("Enter total shift hours: "))
    average_speed = calculate_average_speed(round_trip_distances, cycles_per_shift, total_shift_hours)
    
    # Get terrain adjustment factor
    terrain_factor = TERRAIN_FACTORS.get(terrain_type, 1.0)
    
    # Get tire wear damage factor
    tire_damage_factor = get_tire_damage_factor(tire_wear_percentage)
    
    # Calculate Base TKPH
    tkph_base = (mean_tyre_load * distance_loaded) / cycle_time
    
    # Apply terrain adjustment
    tkph_terrain_adjusted = tkph_base * terrain_factor
    
    # Apply tire wear damage adjustment
    tkph_wear_adjusted = tkph_terrain_adjusted * tire_damage_factor
    
    # Final TKPH (including average speed influence)
    tkph_final = tkph_wear_adjusted * (1 + (average_speed * 0.1))  # Adjusting by a factor for speed influence
    
    # Calculate suitable TKPH (without terrain and damage adjustments)
    suitable_tkph = tkph_base * (1 + (average_speed * 0.1))  # Adjusting by speed
    
    return tkph_final, suitable_tkph

# Main code execution
def main():
    # User inputs
    payload_loaded = float(input("Enter payload (fully loaded) in tons: "))
    distance_loaded = float(input("Enter distance traveled (loaded) in km: "))
    cycle_time = float(input("Enter cycle time in hours: "))
    terrain_type = input("Enter terrain type (Flat, Inclined, Rocky, Muddy): ")
    tire_wear_percentage = float(input("Enter tire wear percentage (0-100): "))
    
    # Calculate TKPH and suitable TKPH
    tkph_final, suitable_tkph = calculate_tkph(payload_loaded, distance_loaded, cycle_time, terrain_type, tire_wear_percentage)
    
    # Display results
    print(f"Calculated TKPH: {tkph_final:.2f}")
    print(f"Suitable TKPH (Ideal conditions): {suitable_tkph:.2f}")

# Run the script
if __name__ == "__main__":
    main()
