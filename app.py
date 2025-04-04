# app.py
from flask import Flask, request, jsonify, render_template, send_from_directory
from collections import deque, Counter
import threading
import datetime
import os
import time # For rate limiting and timestamping
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

app = Flask(__name__, static_folder='static', template_folder='templates')

# --- Geocoding Setup ---
# Use a custom user agent for Nominatim
geolocator = Nominatim(user_agent="web_traffic_visualizer_assignment/1.0 (nikita.levinskiy@tum.de)")
# Rate limit reverse geocoding calls to once per second max (Nominatim policy)
reverse_geocode = RateLimiter(geolocator.reverse, min_delay_seconds=1)
# Cache for geocoding results: {(lat, lon): country_code}
geocode_cache = {}
# Limit cache size to avoid excessive memory use
MAX_CACHE_SIZE = 10000
# ------------------------

# --- Data Storage ---
MAX_POINTS = 5000 # Max points on the globe
MAX_ACTIVITY_SECONDS = 60 # How many seconds of activity data to track/send
traffic_data = deque(maxlen=MAX_POINTS) # Stores individual points for visualization
request_timestamps = deque() # Store recent request timestamps (unix epoch seconds)
country_counts = Counter() # Stores counts per country code {country_code: count}
data_lock = threading.Lock()
TOP_N_COUNTRIES = 10
# ------------------

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serves static files (JS, CSS, images)."""
    return send_from_directory('static', path)

def get_country_from_coords(lat, lon):
    """Performs reverse geocoding with caching and error handling."""
    # Round coordinates for effective caching
    cache_key = (round(lat, 2), round(lon, 2))

    if cache_key in geocode_cache:
        return geocode_cache[cache_key]

    # Check cache size before adding new entries
    if len(geocode_cache) > MAX_CACHE_SIZE:
         # Simple eviction: remove the oldest entry (requires ordered dict or similar for perfect LRU)
         # For simplicity here, just clear a portion if too large
         items_to_remove = MAX_CACHE_SIZE // 10
         for i, key in enumerate(list(geocode_cache.keys())):
             if i >= items_to_remove:
                 break
             del geocode_cache[key]
         # print(f"Geocode cache size exceeded {MAX_CACHE_SIZE}. Cleared {items_to_remove} entries.")


    try:
        # Use the rate-limited function
        location = reverse_geocode(f"{lat}, {lon}", language='en', exactly_one=True)
        if location and location.raw and 'address' in location.raw:
            country_code = location.raw['address'].get('country_code')
            if country_code:
                 country_code = country_code.upper()
                 geocode_cache[cache_key] = country_code # Add to cache
                 return country_code
        geocode_cache[cache_key] = None # Cache negative results too
        return None
    except GeocoderTimedOut:
        # print(f"Warning: Geocoding timed out for ({lat}, {lon}). Retrying might be needed.")
        return None
    except GeocoderServiceError as e:
        # print(f"Warning: Geocoding service error for ({lat}, {lon}): {e}")
        return None
    except Exception as e:
        # print(f"Warning: Unexpected error during geocoding for ({lat}, {lon}): {e}")
        return None


@app.route('/data', methods=['POST'])
def receive_data():
    """Receives traffic data, performs geocoding, updates counts, and logs timestamp."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    required_keys = ['latitude', 'longitude', 'timestamp', 'suspicious', 'ip_address']
    if not all(key in data for key in required_keys):
        return jsonify({"error": "Missing required keys"}), 400

    try:
        lat = float(data['latitude'])
        lon = float(data['longitude'])
        suspicious = int(float(data['suspicious']))
        current_time_sec = int(time.time()) # Timestamp for activity log

        # Get country (using cache/rate-limiter)
        country_code = get_country_from_coords(lat, lon)

        with data_lock:
            # Log timestamp for activity plot
            request_timestamps.append(current_time_sec)
            # Remove old timestamps (older than MAX_ACTIVITY_SECONDS + buffer)
            cutoff_time = current_time_sec - (MAX_ACTIVITY_SECONDS + 10)
            while request_timestamps and request_timestamps[0] < cutoff_time:
                request_timestamps.popleft()

            # Add point data (for globe visualization)
            traffic_data.append({
                'lat': lat,
                'lon': lon,
                'suspicious': suspicious,
                'timestamp': data['timestamp'],
                'ip': data['ip_address'],
                'country': country_code
            })

            # Update country counts
            if country_code:
                country_counts[country_code] += 1

        return jsonify({"status": "success", "country_found": country_code}), 201

    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid data format: {e}"}), 400
    except Exception as e:
        print(f"Error processing data: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/get_traffic', methods=['GET'])
def get_traffic():
    """Provides stored traffic points, top country data, and recent activity."""
    with data_lock:
        current_points = list(traffic_data)
        top_countries_data = country_counts.most_common(TOP_N_COUNTRIES)
        current_top_countries = [{"country": country, "count": count}
                                for country, count in top_countries_data]

        # Calculate activity data (requests per second for the last MAX_ACTIVITY_SECONDS)
        current_time_sec = int(time.time())
        start_time_sec = current_time_sec - MAX_ACTIVITY_SECONDS + 1
        # Count occurrences of each timestamp in the relevant window
        activity_counts = Counter(ts for ts in request_timestamps if ts >= start_time_sec)

        # Create a list of (timestamp, count) for the last MAX_ACTIVITY_SECONDS
        activity_data = []
        for i in range(MAX_ACTIVITY_SECONDS):
            ts = start_time_sec + i
            count = activity_counts.get(ts, 0)
            activity_data.append({"timestamp": ts, "count": count})

    return jsonify({
        "points": current_points,
        "top_countries": current_top_countries,
        "activity": activity_data # Added activity data
        })

if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    # Disable debug mode if using geopy rate limiter effectively in production
    # Set debug=False if deploying, keep True for local dev if needed
    app.run(host=host, port=port, debug=False) 