import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import swisseph as swe

app = Flask(__name__)
# This allows your HTML file to request data from this server
CORS(app)

# -------------------------------------------------
# PATHS & SWISS EPHEMERIS SETUP
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EPHE_PATH = os.path.join(BASE_DIR, "ephe")
swe.set_ephe_path(EPHE_PATH)

FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

AYANAMSHA_MAP = {
    "Lahiri": swe.SIDM_LAHIRI,
    "KP New": swe.SIDM_KRISHNAMURTI,
    "Raman": swe.SIDM_RAMAN
}

PLANETS = {
    "Surya": swe.SUN, "Chandra": swe.MOON, "Mangala": swe.MARS,
    "Budha": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS,
    "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE, "Rahu_true": swe.TRUE_NODE,
    "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO
}

# -------------------------------------------------
# MATH FUNCTIONS (DIRECTLY FROM YOUR CODE)
# -------------------------------------------------
def get_planet_lon_and_retro(jd, code, flags):
    calc_result = swe.calc_ut(jd, code, flags)[0]
    lon_today = calc_result[0] % 360
    speed = calc_result[3]
    is_retro = speed < 0
    return lon_today, is_retro

def horary_to_longitude(num):
    num = int(num)
    DASHA = [7, 20, 6, 10, 7, 18, 16, 19, 17]
    subs = []
    current_val = 0
    for nak in range(27):
        start_index = nak % 9
        for i in range(9):
            lord_index = (start_index + i) % 9
            years = DASHA[lord_index]
            end_val = current_val + years
            sign_start = current_val // 270
            sign_end = (end_val - 1) // 270
            if sign_start != sign_end:
                boundary_val = sign_end * 270
                subs.append(current_val / 9.0)
                subs.append(boundary_val / 9.0)
            else:
                subs.append(current_val / 9.0)
            current_val = end_val
    return subs[num - 1]

def calculate_all_ayanamshas(jd, lat, lon):
    results = {}
    for name, sid_mode in AYANAMSHA_MAP.items():
        swe.set_sid_mode(sid_mode)
        ayan = swe.get_ayanamsa(jd)
        houses, _ = swe.houses(jd, lat, lon, b'P')
        cusps = {str(i + 1): (houses[i] - ayan) % 360 for i in range(12)}
        
        planets = {}
        planets_retro = {}
        for p, code in PLANETS.items():
            lon_p, is_retro = get_planet_lon_and_retro(jd, code, FLAGS)
            planets[p] = lon_p
            planets_retro[p] = is_retro
            
        planets["Ketu"] = (planets["Rahu"] + 180) % 360
        planets["Ketu_true"] = (planets["Rahu_true"] + 180) % 360
        planets_retro["Ketu"] = True
        planets_retro["Ketu_true"] = True

        results[name] = {
            "ayanamsha_value": ayan,
            "lagna": cusps["1"],
            "planets": planets,
            "planets_retro": planets_retro,
            "cusps": cusps
        }
    return results

def calculate_sayana(jd, lat, lon):
    planets = {}
    planets_retro = {}
    
    # ADDED: FLG_SPEED must be included here as well
    flags_sayana = swe.FLG_SWIEPH | swe.FLG_SPEED 
    
    for p, code in PLANETS.items():
        # FIXED: Remove [0:2] and grab the correct indexes
        calc_result = swe.calc_ut(jd, code, flags_sayana)[0]
        lon_p = calc_result[0] % 360
        speed = calc_result[3] # Index 3 is the actual speed
        
        planets[p] = lon_p
        planets_retro[p] = speed < 0
        
    # ADDED: Don't forget to generate Ketu for the Sayana output as well!
    planets["Ketu"] = (planets["Rahu"] + 180) % 360
    planets["Ketu_true"] = (planets["Rahu_true"] + 180) % 360
    planets_retro["Ketu"] = True
    planets_retro["Ketu_true"] = planets_retro["Rahu_true"]

    houses, _ = swe.houses(jd, lat, lon, b'P')
    cusps = {str(i + 1): houses[i] % 360 for i in range(12)}
    
    return {
        "ayanamsha_value": 0.0,
        "lagna": cusps["1"],
        "planets": planets,
        "planets_retro": planets_retro,
        "cusps": cusps
    }

def calculate_horary(jd, lat, lon, number):
    target_lon = horary_to_longitude(number)
    results = {}
    for name, sid_mode in AYANAMSHA_MAP.items():
        swe.set_sid_mode(sid_mode)
        temp_jd = jd
        for _ in range(10):
            ayan = swe.get_ayanamsa(temp_jd)
            houses, _ = swe.houses(temp_jd, lat, lon, b'P')
            current_lagna = (houses[0] - ayan) % 360
            diff = (target_lon - current_lagna) % 360
            if diff > 180: diff -= 360
            if abs(diff) < 0.0001: break
            temp_jd += (diff / 360.0) * 0.99726957 
        
        ayan = swe.get_ayanamsa(temp_jd)
        houses, _ = swe.houses(temp_jd, lat, lon, b'P')
        cusps = {str(i + 1): (houses[i] - ayan) % 360 for i in range(12)}
        
        planets = {}
        planets_retro = {}
        for p, code in PLANETS.items():
            lon_p, is_retro = get_planet_lon_and_retro(jd, code, FLAGS)
            planets[p] = lon_p
            planets_retro[p] = is_retro
            
        planets["Ketu"] = (planets["Rahu"] + 180) % 360
        planets["Ketu_true"] = (planets["Rahu_true"] + 180) % 360
        planets_retro["Ketu"] = True
        planets_retro["Ketu_true"] = True

        results[name] = {
            "ayanamsha_value": ayan,
            "lagna": target_lon,
            "planets": planets,
            "planets_retro": planets_retro,
            "cusps": cusps
        }
    return results



# -------------------------------------------------
# TRANSIT SEARCH LOGIC & ENDPOINT
# -------------------------------------------------
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Moola", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

RASIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

def get_pada_info(degree):
    degree = degree % 360
    pada_index = int(degree / (360.0 / 108.0))
    if pada_index == 108: pada_index = 107 # Edge case clamp
    nak_index = pada_index // 4
    pada_num = (pada_index % 4) + 1
    rasi_index = pada_index // 9
    return {
        "nakshatra": NAKSHATRAS[nak_index],
        "pada": pada_num,
        "rasi": RASIS[rasi_index],
        "pada_index": pada_index
    }

@app.route('/transit-search', methods=['POST'])
def transit_search():
    try:
        data = request.json
        year = int(data['year'])
        planet_name = data['planet']
        
        # Lock to major planets to protect server resources
        allowed = ["Saturn", "Jupiter", "Rahu", "Ketu", "Rahu_true", "Ketu_true"]
        if planet_name not in allowed:
            return jsonify({"status": "error", "message": "Planet not supported for deep transit search."}), 400
            
        is_ketu = "Ketu" in planet_name
        # Resolve the base planet to query Swiss Ephemeris
        if planet_name == "Ketu_true": swe_planet = PLANETS["Rahu_true"]
        elif is_ketu: swe_planet = PLANETS["Rahu"]
        else: swe_planet = PLANETS[planet_name]
        
        swe.set_sid_mode(AYANAMSHA_MAP["Lahiri"]) # Default to Lahiri for transits
        
        start_jd = swe.julday(year, 1, 1, 0.0)
        end_jd = swe.julday(year + 1, 1, 1, 0.0)
        
        events = []
        step = 1.0 # Scan day by day
        current_jd = start_jd
        
        while current_jd < end_jd:
            lon1, retro1 = get_planet_lon_and_retro(current_jd, swe_planet, FLAGS)
            lon2, retro2 = get_planet_lon_and_retro(current_jd + step, swe_planet, FLAGS)
            
            if is_ketu:
                lon1 = (lon1 + 180) % 360
                lon2 = (lon2 + 180) % 360
                
            info1 = get_pada_info(lon1)
            info2 = get_pada_info(lon2)
            
            # Boundary Crossed!
            if info1['pada_index'] != info2['pada_index']:
                jd_left = current_jd
                jd_right = current_jd + step
                
                # Determine direction to find the correct boundary line
                diff = lon2 - lon1
                if diff > 180: diff -= 360
                elif diff < -180: diff += 360
                moving_forward = diff > 0
                
                if moving_forward:
                    boundary_index = info2['pada_index']
                    if info1['pada_index'] == 107 and info2['pada_index'] == 0: boundary_index = 0
                else:
                    boundary_index = info1['pada_index']
                    if info1['pada_index'] == 0 and info2['pada_index'] == 107: boundary_index = 0
                    
                boundary_lon = boundary_index * (360.0 / 108.0)
                
                # Binary Search to pinpoint exact minute
                exact_jd = jd_left
                for _ in range(15): 
                    mid = (jd_left + jd_right) / 2.0
                    lon_mid, _ = get_planet_lon_and_retro(mid, swe_planet, FLAGS)
                    if is_ketu: lon_mid = (lon_mid + 180) % 360
                    
                    d_mid = lon_mid - boundary_lon
                    if d_mid > 180: d_mid -= 360
                    elif d_mid < -180: d_mid += 360
                    
                    if moving_forward:
                        if d_mid > 0: jd_right = mid
                        else: jd_left = mid
                    else:
                        if d_mid < 0: jd_right = mid
                        else: jd_left = mid
                        
                    exact_jd = (jd_left + jd_right) / 2.0
                
                # Convert exact Julian Day to UTC Date
                y, m, d, h_float = swe.revjul(exact_jd)
                h = int(h_float)
                mn = int((h_float - h) * 60)
                s = int((((h_float - h) * 60) - mn) * 60)
                
                # Handle edge case where seconds round up to 60
                if s == 60: s = 59 
                
                dt_utc = datetime(y, m, d, h, mn, s)
                
                events.append({
                    "datetime_utc": dt_utc.isoformat() + "Z",
                    "planet": planet_name,
                    "entered_rasi": info2['rasi'],
                    "entered_nakshatra": info2['nakshatra'],
                    "entered_pada": info2['pada'],
                    "is_retrograde": not moving_forward,
                    "degree_crossed": round(boundary_lon, 4)
                })
            
            current_jd += step

        return jsonify({"status": "success", "data": events})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400








# -------------------------------------------------
# API ENDPOINT
# -------------------------------------------------
@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Get the JSON data sent from your HTML file
        data = request.json
        
        dt = datetime(
            int(data['year']), int(data['month']), int(data['day']), 
            int(data['hour']), int(data['minute']), int(data['second'])
        )
        
        # Apply the timezone offset (e.g., 330 for India +5:30)
        offset = int(data.get('timezone_offset', 330))
        utc = dt - timedelta(minutes=offset)
        
        jd = swe.julday(
            utc.year, utc.month, utc.day,
            utc.hour + utc.minute / 60 + utc.second / 3600.0
        )
        
        lat = float(data['lat'])
        lon = float(data['lon'])

        if data.get('horary_mode'):
            results = calculate_horary(jd, lat, lon, int(data['horary_number']))
        else:
            results = calculate_all_ayanamshas(jd, lat, lon)

        results["Sayana"] = calculate_sayana(jd, lat, lon)

        # Return the exact JSON structure your old script was saving
        return jsonify({
            "status": "success", 
            "data": {
                "ayanamsha": "Lahiri",
                "lagna": results["Lahiri"]["lagna"],
                "planets": results["Lahiri"]["planets"],
                "planets_retro": results["Lahiri"]["planets_retro"],
                "cusps": results["Lahiri"]["cusps"],
                "ayanamshas": results
            }
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
