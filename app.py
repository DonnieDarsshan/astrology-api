import os
import sys
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import swisseph as swe

# -------------------------------------------------
# PATHS & CONFIG
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
swe.set_ephe_path(BASE_DIR)

app = Flask(__name__)
CORS(app)

AYANAMSHA_MAP = {
    "Lahiri": swe.SIDM_LAHIRI,
    "KP New": swe.SIDM_KRISHNAMURTI,
    "Raman": swe.SIDM_RAMAN
}

if hasattr(swe, "SIDM_YUKTESHWAR"): AYANAMSHA_MAP["Yukteshwar"] = swe.SIDM_YUKTESHWAR
if hasattr(swe, "SIDM_TRUE_REVATI"): AYANAMSHA_MAP["True Revati"] = swe.SIDM_TRUE_REVATI
if hasattr(swe, "SIDM_USHASHASHI"): AYANAMSHA_MAP["Usha–Shashi"] = swe.SIDM_USHASHASHI

FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

PLANETS = {
    "Surya": swe.SUN,
    "Chandra": swe.MOON,
    "Mangala": swe.MARS,
    "Budha": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
    "Rahu_true": swe.TRUE_NODE,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO
}

# -------------------------------------------------
# MATH HELPERS
# -------------------------------------------------
def get_planet_lon_and_retro(jd, code, flags):
    calc_result = swe.calc_ut(jd, code, flags)[0]
    lon_today = calc_result[0] % 360
    speed = calc_result[3]
    is_retro = speed < 0
    return lon_today, is_retro

def get_nakshatra_transit_dates(jd, code, flags, sid_mode):
    swe.set_sid_mode(sid_mode)
    
    def get_nak(t_jd):
        ayan = swe.get_ayanamsa(t_jd)
        lon = (swe.calc_ut(t_jd, code, flags)[0][0] - ayan) % 360
        return int(lon / (360.0 / 27.0))
        
    start_nak = get_nak(jd)
    
    # Backward search for Entry
    t = jd
    while get_nak(t) == start_nak:
        t -= 1.0
        if jd - t > 4000: break # Safety limit for slow planets
    
    jd_out, jd_in = t, t + 1.0
    for _ in range(8):
        mid = (jd_out + jd_in) / 2.0
        if get_nak(mid) == start_nak: jd_in = mid
        else: jd_out = mid
    entry_jd = jd_in
    
    # Forward search for Exit
    t = jd
    while get_nak(t) == start_nak:
        t += 1.0
        if t - jd > 4000: break
        
    jd_out, jd_in = t, t - 1.0
    for _ in range(8):
        mid = (jd_out + jd_in) / 2.0
        if get_nak(mid) == start_nak: jd_in = mid
        else: jd_out = mid
    exit_jd = jd_out
    
    def format_jd(j):
        y, m, d, _ = swe.revjul(j, swe.GREG_CAL)
        return datetime(y, m, int(d)).strftime("%Y-%b-%d")
        
    return {"entry": format_jd(entry_jd), "exit": format_jd(exit_jd)}

def horary_to_longitude(num):
    num = int(num)
    if not (1 <= num <= 249):
        raise ValueError("Horary number must be between 1 and 249")

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

# -------------------------------------------------
# CALCULATION ENGINES
# -------------------------------------------------
def calculate_all_ayanamshas(jd, lat, lon):
    results = {}

    for name, sid_mode in AYANAMSHA_MAP.items():
        swe.set_sid_mode(sid_mode)
        ayan = swe.get_ayanamsa(jd)
        houses, _ = swe.houses(jd, lat, lon, b'P')
        cusps = {str(i + 1): (houses[i] - ayan) % 360 for i in range(12)}
                    
        planets = {}
        planets_retro = {}
        transit_dates = {}

        for p, code in PLANETS.items():
            lon_p, is_retro = get_planet_lon_and_retro(jd, code, FLAGS)
            planets[p] = lon_p
            planets_retro[p] = is_retro
            
            # Fetch Nakshatra Entry/Exit dates (Calculate only for Lahiri to save CPU)
            if name == "Lahiri" and p not in ["Uranus", "Neptune", "Pluto"]:
                transit_dates[p] = get_nakshatra_transit_dates(jd, code, FLAGS, sid_mode)
            
        planets["Ketu"] = (planets["Rahu"] + 180) % 360
        planets["Ketu_true"] = (planets["Rahu_true"] + 180) % 360
        planets_retro["Ketu"] = True
        planets_retro["Ketu_true"] = True
        
        if name == "Lahiri":
            transit_dates["Ketu"] = transit_dates.get("Rahu", {"entry": "N/A", "exit": "N/A"})
            transit_dates["Ketu_true"] = transit_dates.get("Rahu_true", {"entry": "N/A", "exit": "N/A"})

        results[name] = {
            "ayanamsha_value": ayan,
            "lagna": cusps["1"],
            "planets": planets,
            "planets_retro": planets_retro,
            "cusps": cusps,
            "transit_dates": transit_dates
        }

    return results

def calculate_sayana(jd, lat, lon):
    planets = {}
    planets_retro = {}
    flags_sayana = swe.FLG_SWIEPH | swe.FLG_SPEED 

    for p, code in PLANETS.items():
        calc_result = swe.calc_ut(jd, code, flags_sayana)[0]
        lon_p = calc_result[0] % 360
        speed = calc_result[3]
        planets[p] = lon_p
        planets_retro[p] = speed < 0

    planets["Ketu"] = (planets["Rahu"] + 180) % 360
    planets["Ketu_true"] = (planets["Rahu_true"] + 180) % 360
    planets_retro["Ketu"] = True
    planets_retro["Ketu_true"] = planets_retro.get("Rahu_true", True)

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
# FLASK SERVER API ROUTE
# -------------------------------------------------
@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        y = int(data['year'])
        m = int(data['month'])
        d = int(data['day'])
        hr = int(data['hour'])
        min_val = int(data['minute'])
        sec = int(data['second'])
        
        lat = float(data['lat'])
        lon = float(data['lon'])
        tz_offset = float(data.get('timezone_offset', 0))
        horary_mode = data.get('horary_mode', False)
        horary_num = data.get('horary_number', 1)

        dt = datetime(y, m, d, hr, min_val, sec)
        utc = dt - timedelta(minutes=tz_offset)
        jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60 + utc.second / 3600)

        if horary_mode:
            ayanamsha_results = calculate_horary(jd, lat, lon, horary_num)
        else:
            ayanamsha_results = calculate_all_ayanamshas(jd, lat, lon)

        ayanamsha_results["Sayana"] = calculate_sayana(jd, lat, lon)

        return jsonify({
            "status": "success",
            "data": {
                "ayanamsha": "Lahiri",
                "lagna": ayanamsha_results["Lahiri"]["lagna"],
                "planets": ayanamsha_results["Lahiri"]["planets"],
                "planets_retro": ayanamsha_results["Lahiri"]["planets_retro"],
                "cusps": ayanamsha_results["Lahiri"]["cusps"],
                "transit_dates": ayanamsha_results["Lahiri"].get("transit_dates", {}),
                "ayanamshas": ayanamsha_results
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
