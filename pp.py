import numpy as np
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

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
    else:  # 75 < wear_percentage <= 100
        return 0.5   # Critical Wear

# Function to remove outliers using the Interquartile Range (IQR) method
def remove_outliers(data):
    Q1 = np.percentile(data, 25)
    Q3 = np.percentile(data, 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return [x for x in data if lower_bound <= x <= upper_bound]

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

# Function to calculate TKPH
def calculate_tkph(payload_loaded, distance_loaded, cycle_time, terrain_type, tire_wear_percentage, 
                   tyre_load_empty, tyre_load_fully_loaded, round_trip_distances, 
                   cycles_per_shift, total_shift_hours):
    # Calculate mean tire load
    mean_tyre_load = calculate_mean_tyre_load(tyre_load_empty, tyre_load_fully_loaded)
    
    # Calculate average speed
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
    tkph_final = tkph_wear_adjusted * (1 + (average_speed * 0.1))
    
    # Calculate suitable TKPH (without terrain and damage adjustments)
    suitable_tkph = tkph_base * (1 + (average_speed * 0.1))
    
    return tkph_final, suitable_tkph

# Function to save TKPH data to Excel
def save_tkph_data(dumper_id, tyre_position, tkph_final, suitable_tkph):
    try:
        # Check if file exists
        if not os.path.exists('tkph_tracking.xlsx'):
            # Create a new DataFrame and save it
            df = pd.DataFrame(columns=['Timestamp', 'Dumper ID', 'Tyre Position', 'TKPH Final', 'Suitable TKPH'])
            df.to_excel('tkph_tracking.xlsx', index=False, engine='openpyxl')
        
        # Read existing data
        df = pd.read_excel('tkph_tracking.xlsx', engine='openpyxl')
    except Exception as e:
        # If any error occurs, create a fresh DataFrame
        df = pd.DataFrame(columns=['Timestamp', 'Dumper ID', 'Tyre Position', 'TKPH Final', 'Suitable TKPH'])
    
    # Add new row with properly formatted timestamp
    new_row = pd.DataFrame({
        'Timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        'Dumper ID': [dumper_id],
        'Tyre Position': [tyre_position],
        'TKPH Final': [tkph_final],
        'Suitable TKPH': [suitable_tkph]
    })
    
    # Concatenate existing and new data
    df = pd.concat([df, new_row], ignore_index=True)
    
    # Save to Excel
    df.to_excel('tkph_tracking.xlsx', index=False, engine='openpyxl')

# Function to generate TKPH trend bar chart
def generate_tkph_trend_chart(dumper_id, tyre_position):
    try:
        df = pd.read_excel('tkph_tracking.xlsx')
        
        # Filter data for specific dumper and tyre position
        filtered_df = df[(df['Dumper ID'] == dumper_id) & 
                         (df['Tyre Position'] == tyre_position)]
        
        if filtered_df.empty:
            return None
        
        # Create bar chart
        plt.figure(figsize=(10, 6))
        plt.bar(filtered_df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M'), 
                filtered_df['TKPH Final'], 
                label='TKPH Final', color='blue', alpha=0.7)
        plt.bar(filtered_df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M'), 
                filtered_df['Suitable TKPH'], 
                label='Suitable TKPH', color='green', alpha=0.7)
        
        plt.title(f'TKPH Trend for Dumper {dumper_id} - {tyre_position}')
        plt.xlabel('Timestamp')
        plt.ylabel('TKPH')
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        
        # Convert plot to base64 string
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plot_data = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return plot_data
    except Exception:
        return None

# Main route for dumper and tyre selection
@app.route('/')
def index():
    return render_template('dumper_id.html')

@app.route('/tyre-selection')
def tyre_selection():
    dumper_id = request.args.get('dumper_id')
    return render_template('tyre_selection.html', dumper_id=dumper_id)
@app.route('/tkph-calculator', methods=['GET', 'POST'])
def tkph_calculator():
    dumper_id = request.args.get('dumper_id')
    tyre_position = request.args.get('tyre_position')
    
    if request.method == 'POST':
        try:
            # Collect input values
            payload_loaded = float(request.form['payload_loaded'])
            distance_loaded = float(request.form['distance_loaded'])
            cycle_time = float(request.form['cycle_time'])
            terrain_type = request.form['terrain_type']
            tire_wear_percentage = float(request.form['tire_wear_percentage'])
            tyre_load_empty = float(request.form['tyre_load_empty'])
            tyre_load_fully_loaded = float(request.form['tyre_load_fully_loaded'])
            
            # Process round trip distances
            round_trip_distances = [float(x.strip()) for x in request.form['round_trip_distances'].split(',')]
            cycles_per_shift = int(request.form['cycles_per_shift'])
            total_shift_hours = float(request.form['total_shift_hours'])
            
            # Calculate TKPH
            tkph_final, suitable_tkph = calculate_tkph(
                payload_loaded, distance_loaded, cycle_time, terrain_type, tire_wear_percentage,
                tyre_load_empty, tyre_load_fully_loaded, round_trip_distances, 
                cycles_per_shift, total_shift_hours
            )
            
            # Save TKPH data
            save_tkph_data(dumper_id, tyre_position, tkph_final, suitable_tkph)
            
            # Generate trend chart
            trend_chart = generate_tkph_trend_chart(dumper_id, tyre_position)
            
            return render_template('result.html', 
                                   tkph_final=round(tkph_final, 2), 
                                   suitable_tkph=round(suitable_tkph, 2),
                                   trend_chart=trend_chart,
                                   dumper_id=dumper_id,
                                   tyre_position=tyre_position)
        
        except ValueError as e:
            error_message = f"Invalid input: {str(e)}. Please check your entries."
            return render_template('tkph_calculator.html', 
                                   error=error_message, 
                                   dumper_id=dumper_id, 
                                   tyre_position=tyre_position)
    
    return render_template('tkph_calculator.html', 
                           dumper_id=dumper_id, 
                           tyre_position=tyre_position)

if __name__ == '__main__':
    app.run(debug=True)