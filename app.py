import numpy as np
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import io
import base64
import os
import winsound  # Sound alerts for Windows

app = Flask(__name__)

# Terrain adjustment factors (based on terrain type)
TERRAIN_FACTORS = {
    "Flat": 1.0,
    "Inclined": 0.9,
    "Rocky": 0.8,
    "Muddy": 0.7
}

# Function to evaluate TKPH conditions
def evaluate_conditions(tkph_final, suitable_tkph):
    if tkph_final >= suitable_tkph * 0.90:
        return "Normal Condition"
    elif tkph_final >= suitable_tkph * 0.80:
        return "Warning Condition"
    elif tkph_final >= suitable_tkph * 0.70:
        return "Danger Condition"
    else:
        return "Critical Condition"

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
def calculate_tkph(distance_loaded, cycle_time, terrain_type, tire_wear_percentage,
                   tyre_load_empty, tyre_load_fully_loaded, round_trip_distances, 
                   cycles_per_shift, total_shift_hours):
    # Calculate mean tire load
    mean_tyre_load = calculate_mean_tyre_load(tyre_load_empty, tyre_load_fully_loaded)
    
    # Calculate average speed
    average_speed = calculate_average_speed(round_trip_distances, cycles_per_shift, total_shift_hours)
    
    # Terrain and wear adjustments
    terrain_factor = TERRAIN_FACTORS.get(terrain_type, 1.0)
    tire_damage_factor = get_tire_damage_factor(min(tire_wear_percentage, 100))  # Cap wear percentage at 100
    
    # Base TKPH
    tkph_base = (mean_tyre_load * distance_loaded) / cycle_time
    
    # Adjust for terrain and wear
    tkph_adjusted = tkph_base * terrain_factor * tire_damage_factor
    
    # Final TKPH (without unnecessary speed multiplier)
    tkph_final = tkph_adjusted
    
    # Suitable TKPH (base calculation without terrain and wear adjustments)
    suitable_tkph = tkph_base
    
    return tkph_final, suitable_tkph

# Function to save TKPH data to Excel
def save_tkph_data(dumper_id, tyre_position, tkph_final, suitable_tkph):
    file_path = 'tkph_tracking.xlsx'
    
    try:
        # Check if the file exists
        if os.path.exists(file_path):
            # Read existing data
            df = pd.read_excel(file_path, engine='openpyxl')
        else:
            # Create a new DataFrame with appropriate columns
            df = pd.DataFrame(columns=['Timestamp', 'Dumper ID', 'Tyre Position', 'TKPH Final', 'Suitable TKPH'])
    
    except Exception as e:
        # If any error occurs while reading, create a new DataFrame
        print(f"Error reading the Excel file: {e}")
        df = pd.DataFrame(columns=['Timestamp', 'Dumper ID', 'Tyre Position', 'TKPH Final', 'Suitable TKPH'])
    
    # Add new row with a more formatted timestamp
    new_row = {
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # More readable format
        'Dumper ID': dumper_id,
        'Tyre Position': tyre_position,
        'TKPH Final': tkph_final,
        'Suitable TKPH': suitable_tkph
    }
    
    # Append the new row to the DataFrame
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    # Save updated data back to the Excel file
    df.to_excel(file_path, index=False, engine='openpyxl')

# Function to generate TKPH trend chart
def generate_tkph_trend_chart(dumper_id, tyre_position):
    try:
        # Ensure the Excel file exists and has the correct path
        file_path = 'tkph_tracking.xlsx'
        if not os.path.exists(file_path):
            # If no tracking file exists, return None
            return None
        
        # Read the Excel file
        df = pd.read_excel(file_path, engine='openpyxl')
        
        # Convert Timestamp column to datetime if not already
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        
        # Filter data for specific dumper and tyre position
        filtered_df = df[(df['Dumper ID'] == dumper_id) & 
                         (df['Tyre Position'] == tyre_position)]
        
        # Check if filtered DataFrame is empty
        if filtered_df.empty:
            return None
        
        # Sort by timestamp to ensure chronological order
        filtered_df = filtered_df.sort_values('Timestamp')
        
        # Create figure with improved styling
        plt.figure(figsize=(12, 6))
        plt.style.use('seaborn')
        
        # Plot TKPH Final as a line graph
        plt.plot(filtered_df['Timestamp'], filtered_df['TKPH Final'], 
                 label='TKPH Final', color='blue', marker='o', linewidth=2)
        
        # Plot Suitable TKPH as a line graph
        plt.plot(filtered_df['Timestamp'], filtered_df['Suitable TKPH'], 
                 label='Suitable TKPH', color='green', marker='s', linewidth=2)
        
        # Improved title and labels
        plt.title(f'TKPH Trend for Dumper {dumper_id} - {tyre_position}', fontsize=15)
        plt.xlabel('Timestamp', fontsize=12)
        plt.ylabel('TKPH Value', fontsize=12)
        
        # Rotate and align the tick labels
        plt.gcf().autofmt_xdate()
        
        # Add grid for better readability
        plt.grid(True, linestyle='--', linewidth=0.5)
        
        # Add legend
        plt.legend()
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert plot to base64 string
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300)
        buffer.seek(0)
        plot_data = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return plot_data
    except Exception as e:
        print(f"Error generating trend chart: {e}")
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
                distance_loaded, cycle_time, terrain_type, tire_wear_percentage,
                tyre_load_empty, tyre_load_fully_loaded, round_trip_distances, 
                cycles_per_shift, total_shift_hours
            )
            
            # Evaluate TKPH conditions
            condition_status = evaluate_conditions(tkph_final, suitable_tkph)
            
            # Sound alert for critical conditions
            if condition_status == "Critical Condition":
                # Use winsound to play a repetitive alarm sound
                # Frequency of 2500, duration of 1000 ms (1 second)
                for _ in range(3):  # Repeat 3 times
                    winsound.Beep(2500, 1000)
            
            # Save TKPH data
            save_tkph_data(dumper_id, tyre_position, tkph_final, suitable_tkph)
            
            # Generate trend chart
            trend_chart = generate_tkph_trend_chart(dumper_id, tyre_position)
            
            return render_template('result.html', 
                                   tkph_final=round(tkph_final, 2), 
                                   suitable_tkph=round(suitable_tkph, 2),
                                   condition_status=condition_status,
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