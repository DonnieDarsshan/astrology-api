# OFFLINE SWISS EPHEMERIS – TANTRIC DARK MODE (FINAL STABLE)
# =========================================================
import os, json, re
import sys

import swisseph as swe
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# -------------------------------------------------
# PATHS
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
def get_ephe_path():
    if hasattr(sys, "_MEIPASS"):
        # Looks directly in the root of the extracted .exe
        return sys._MEIPASS  
    # Looks directly in the same folder as calculate.py for normal runs
    return os.path.dirname(os.path.abspath(__file__))

import sys
EPHE_PATH = get_ephe_path()

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")





# -------------------------------------------------
# AYANAMSHA (SAFE – VERSION COMPATIBLE & FUTURE PROOF)
# -------------------------------------------------
AYANAMSHA_MAP = {
    "Lahiri": swe.SIDM_LAHIRI,
    "KP New": swe.SIDM_KRISHNAMURTI,
    "Raman": swe.SIDM_RAMAN
}

# --- Optional / Less common but REAL Swiss Ephemeris ayanamshas ---

if hasattr(swe, "SIDM_YUKTESHWAR"):
    AYANAMSHA_MAP["Yukteshwar"] = swe.SIDM_YUKTESHWAR

if hasattr(swe, "SIDM_TRUE_REVATI"):
    AYANAMSHA_MAP["True Revati"] = swe.SIDM_TRUE_REVATI

if hasattr(swe, "SIDM_USHASHASHI"):
    AYANAMSHA_MAP["Usha–Shashi"] = swe.SIDM_USHASHASHI







# -------------------------------------------------
# SWISS EPHEMERIS
# -------------------------------------------------
swe.set_ephe_path(EPHE_PATH)
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
# SETTINGS
# -------------------------------------------------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            return json.load(open(SETTINGS_FILE, "r", encoding="utf-8"))
        except:
            pass
    return {"output_dir": ""}

def save_settings():
    json.dump(settings, open(SETTINGS_FILE, "w", encoding="utf-8"), indent=2)

settings = load_settings()





# -------------------------------------------------
# SAFE AUTO-JUMP (SHIFT+TAB SAFE)
# -------------------------------------------------
_last_len = {}

def jump_if_complete(var, widget, size, key):
    cur = var.get()
    prev = _last_len.get(key, 0)
    _last_len[key] = len(cur)
    if cur.isdigit() and len(cur) == size and prev < size:
        widget.focus()


def smart_day_month_jump(event, var, next_widget):
    # Do not auto-jump when Shift+Tab is used
    if event.state & 0x1:
        return

    val = var.get()
    if not val.isdigit():
        return

    if len(val) == 1 and val[0] in "456789":
        next_widget.focus()
    elif len(val) >= 2:
        next_widget.focus()


def smart_month_jump(event, var, next_widget):
    # Do not interfere with Shift+Tab
    if event.state & 0x1:
        return

    val = var.get()
    if not val.isdigit():
        return

    # Month rules:
    # 0 → wait (01–09)
    # 1 → wait (10–12)
    # 2–9 → jump immediately
    if len(val) == 1:
        if val[0] in "23456789":
            next_widget.focus()
    elif len(val) >= 2:
        next_widget.focus()


def smart_hour_jump(event, var, next_widget):
    if event.state & 0x1:
        return

    val = var.get()
    if not val.isdigit():
        return

    if len(val) == 1 and val[0] in "3456789":
        next_widget.focus()
    elif len(val) >= 2:
        next_widget.focus()












def smart_minute_jump(event, var, next_widget):
    if event.state & 0x1:
        return

    val = var.get()
    if not val.isdigit():
        return

    if len(val) == 1 and val[0] in "6789":
        next_widget.focus()
    elif len(val) >= 2:
        next_widget.focus()

    
    
    
    
    
    
    
    
    


# -------------------------------------------------
# HELPERS
# -------------------------------------------------


def get_planet_lon_and_retro(jd, code, flags):
    """
    MATHEMATICALLY PERFECT RETROGRADE
    Using instantaneous longitudinal speed from Swiss Ephemeris.
    """
    # swe.calc_ut returns: ((lon, lat, dist, speed_lon, speed_lat, speed_dist), ret_flag)
    calc_result = swe.calc_ut(jd, code, flags)[0]
    
    lon_today = calc_result[0] % 360
    speed = calc_result[3]  # Instantaneous speed in longitude
    
    # True Vakri is when instantaneous speed is negative
    is_retro = speed < 0
    
    return lon_today, is_retro



def sanitize_filename(name):
    # allow letters, numbers, dash, space and ~
    return re.sub(r"[^\w\-\~ ]+", "", name.strip()) or "kundali"
    
    
# -------------------------------------------------
# COORDINATE CONVERSION HELPERS
# -------------------------------------------------
def dms_to_decimal(deg, minute, sec, direction):
    try:
        d = float(deg)
        m = float(minute)
        s = float(sec)
    except:
        raise ValueError("Invalid DMS numeric value")

    if not (0 <= m < 60 and 0 <= s < 60):
        raise ValueError("Minutes/Seconds must be 0–59")

    val = d + (m / 60.0) + (s / 3600.0)

    if direction in ("S", "W"):
        val = -val

    return round(val, 6)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
# -------------------------------------------------
# HORARY HELPERS (FIXED KP ENGINE)
# -------------------------------------------------
def horary_to_longitude(num):
    """
    True KP Horary (1–249)
    Fixes the 243 vs 249 bug by precisely splitting subs that cross 30° sign boundaries
    using exact integer math (eliminating floating-point precision errors).
    """
    num = int(num)
    if not (1 <= num <= 249):
        raise ValueError("Horary number must be between 1 and 249")

    # Dasha years in exact Vimshottari order starting from Ketu
    DASHA = [7, 20, 6, 10, 7, 18, 16, 19, 17]
    
    subs = []
    current_val = 0  # We calculate in units of 1/9th of a degree
    
    for nak in range(27):
        start_index = nak % 9
        for i in range(9):
            lord_index = (start_index + i) % 9
            years = DASHA[lord_index]
            
            end_val = current_val + years
            
            # Sign boundaries occur every 30 degrees. 
            # In 1/9th degree units, 30° * 9 = 270
            sign_start = current_val // 270
            sign_end = (end_val - 1) // 270
            
            if sign_start != sign_end:
                # Sub crosses a sign boundary -> Split it into two!
                boundary_val = sign_end * 270
                subs.append(current_val / 9.0)       # First part
                subs.append(boundary_val / 9.0)      # Second part
            else:
                # Fits entirely within the current sign
                subs.append(current_val / 9.0)
                
            current_val = end_val

    # Return the starting longitude of the requested sub (0-indexed)
    return subs[num - 1]







def decimal_to_dms(val, is_lat=True):
    sign = "N" if is_lat else "E"
    if val < 0:
        sign = "S" if is_lat else "W"
        val = abs(val)

    d = int(val)
    rem = (val - d) * 60
    m = int(rem)
    s = (rem - m) * 60

    s = int(round(s))

    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        d += 1

    return str(d), sign, f"{m:02d}", f"{s:02d}"

    
    

def choose_output_folder():
    folder = filedialog.askdirectory()
    if folder:
        settings["output_dir"] = folder
        save_settings()
        out_label.config(text=f"Output folder: {folder}")


def open_output_folder():
    folder = settings.get("output_dir")
    if not folder or not os.path.isdir(folder):
        messagebox.showwarning("Output Folder", "Output folder is not set or does not exist.")
        return
    os.startfile(folder)
















# -------------------------------------------------
# AYANAMSHA CHECKBOX CONTROL
# -------------------------------------------------
def select_ayanamsha(name):
    for k in ayan_vars:
        ayan_vars[k].set(1 if k == name else 0)

def get_ayanamsha():
    for k in ayan_vars:
        if ayan_vars[k].get():
            return k
    return "Lahiri"

# -------------------------------------------------
# CALCULATION
# -------------------------------------------------










def calculate_all_ayanamshas(jd, lat, lon):

    results = {}






    for name, sid_mode in AYANAMSHA_MAP.items():

        swe.set_sid_mode(sid_mode)

        ayan = swe.get_ayanamsa(jd)

        houses, _ = swe.houses(jd, lat, lon, b'P')

        cusps = {}
        for i in range(12):
            cusps[str(i + 1)] = (houses[i] - ayan) % 360
                    
                    
            
            
            

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
    
    # Require speed flag for Sayana calculations
    flags_sayana = swe.FLG_SWIEPH | swe.FLG_SPEED 

    for p, code in PLANETS.items():
        calc_result = swe.calc_ut(jd, code, flags_sayana)[0]
        lon_p = calc_result[0] % 360
        speed = calc_result[3]  # Speed is at index 3, not index 1

        planets[p] = lon_p
        planets_retro[p] = speed < 0

    # Ensure Sayana Ketu is populated properly 
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














# -------------------------------------------------
# HORARY CALCULATION (TRUE PLACIDUS SOLVER)
# -------------------------------------------------
def calculate_horary(jd, lat, lon, number):
    # Get the target starting longitude for the horary number
    target_lon = horary_to_longitude(number)
    
    results = {}

    for name, sid_mode in AYANAMSHA_MAP.items():
        swe.set_sid_mode(sid_mode)
        
        # --- ITERATIVE SOLVER FOR HORARY ASCENDANT ---
        # We must find the exact time (JD) today when the target_lon rises.
        temp_jd = jd
        
        for _ in range(10):  # Usually converges in 3-4 iterations
            ayan = swe.get_ayanamsa(temp_jd)
            houses, _ = swe.houses(temp_jd, lat, lon, b'P')
            current_lagna = (houses[0] - ayan) % 360
            
            # Calculate distance to target
            diff = (target_lon - current_lagna) % 360
            if diff > 180:
                diff -= 360  # Take the shortest path
                
            # If accuracy is within ~0.36 arc-seconds, we found the exact time
            if abs(diff) < 0.0001:
                break
                
            # Shift the time. 1 degree of Ascendant shift ≈ 4 minutes (1/360 of a sidereal day)
            temp_jd += (diff / 360.0) * 0.99726957 
        
        # Now that temp_jd is locked onto the exact rising time, grab True Placidus cusps
        ayan = swe.get_ayanamsa(temp_jd)
        houses, _ = swe.houses(temp_jd, lat, lon, b'P')
        cusps = {str(i + 1): (houses[i] - ayan) % 360 for i in range(12)}
        
        # --- PLANETS (CAST FOR MOMENT OF JUDGMENT) ---
        # KP Rule: Cusps change to horary time, but Planets remain at current time (jd)
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






def calculate_and_save():
    try:
        
        # -------------------------------------------------
        # AUTO NAME IF EMPTY
        # -------------------------------------------------
        if not name_var.get().strip():
            auto_name = datetime.now().strftime("%Y-%m-%d ~~ %H-%M-%S")
            name_var.set(auto_name)
                
        

        if not settings.get("output_dir"):
            folder = filedialog.askdirectory()
            if not folder:
                return
            settings["output_dir"] = folder
            save_settings()
            out_label.config(text=f"Output folder:\n{folder}")

        filename = sanitize_filename(name_var.get()) + ".json"
        save_path = os.path.join(settings["output_dir"], filename)

        
        # -------------------------------------------------
        # DATETIME (NATAL OR HORARY)
        # -------------------------------------------------
        if horary_mode.get():
            dt = datetime.now().replace(microsecond=0)
        else:
            dt = datetime(
                int(yyyy_var.get()),
                int(mm_var.get()),
                int(dd_var.get()),
                int(hh_var.get()),
                int(min_var.get()),
                int(sec_var.get())
            )
        
        

        sign = -1 if tz_sign.get() == "-" else 1
        offset = sign * (int(tz_h.get()) * 60 + int(tz_m.get()))
        offset += int(dst_var.get()) * 60
        utc = dt - timedelta(minutes=offset)

        jd = swe.julday(
            utc.year, utc.month, utc.day,
            utc.hour + utc.minute / 60 + utc.second / 3600
        )

        # -------------------------------------------------
        # DMS → DECIMAL (ALWAYS ACTIVE, RUNTIME ONLY)
        # -------------------------------------------------
        lat_val = dms_to_decimal(
            lat_dms_deg.get(),
            lat_dms_min.get(),
            lat_dms_sec.get(),
            lat_dms_dir.get()
        )

        lon_val = dms_to_decimal(
            lon_dms_deg.get(),
            lon_dms_min.get(),
            lon_dms_sec.get(),
            lon_dms_dir.get()
        )

        lat_sign.set("-" if lat_val < 0 else "+")
        lon_sign.set("-" if lon_val < 0 else "+")

        lat_val = abs(lat_val)
        lon_val = abs(lon_val)

        lat_deg.set(str(int(lat_val)))
        lat_frac.set(f"{lat_val % 1:.6f}".split(".")[1])

        lon_deg.set(str(int(lon_val)))
        lon_frac.set(f"{lon_val % 1:.6f}".split(".")[1])



        
        # GOOGLE MAPS FORMAT LATITUDE
        lat = float(f"{lat_deg.get()}.{lat_frac.get() or '0'}")
        if lat_sign.get() == "-":
            lat = -lat

        # GOOGLE MAPS FORMAT LONGITUDE
        lon = float(f"{lon_deg.get()}.{lon_frac.get() or '0'}")
        if lon_sign.get() == "-":
            lon = -lon





        # Check if we are in Horary Mode or Natal Mode
        if horary_mode.get():
            try:
                h_num = int(horary_number.get())
                # Use the specialized horary calculator
                ayanamsha_results = calculate_horary(jd, lat, lon, h_num)
            except ValueError:
                raise ValueError("Please enter a valid Horary Number (1-249)")
        else:
            # Standard Natal calculation
            ayanamsha_results = calculate_all_ayanamshas(jd, lat, lon)

        # Sayana (Tropical) is always calculated for reference
        ayanamsha_results["Sayana"] = calculate_sayana(jd, lat, lon)
        
        

        data = {
            "meta": {
                "name": name_var.get().strip(),
                "latitude": lat,
                "longitude": lon,
                "datetime_utc": utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            },

            "ayanamsha": "Lahiri",
            "lagna": ayanamsha_results["Lahiri"]["lagna"],
            "planets": ayanamsha_results["Lahiri"]["planets"],
            "planets_retro": ayanamsha_results["Lahiri"]["planets_retro"],
            "cusps": ayanamsha_results["Lahiri"]["cusps"],

            "ayanamshas": ayanamsha_results
        }

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    except Exception as e:
        messagebox.showerror("Error", str(e))

        
        



def clear_basic_fields():
    name_var.set("")
    dd_var.set("")
    mm_var.set("")
    yyyy_var.set("")
    hh_var.set("")
    min_var.set("")
    sec_var.set("00")
    e_name.focus()




# -------------------------------------------------
# UI – FINAL FIXED SCALE & FONTS
# -------------------------------------------------
root = tk.Tk()
root.title("Offline Swiss Ephemeris")
root.geometry("820x700")
root.configure(bg="#120404")
root.resizable(True, True)

# ✅ MODERATE scaling (not extreme)
root.tk.call("tk", "scaling", 1.15)

style = ttk.Style(root)
style.theme_use("clam")

# ✅ ONE UNIFORM FONT FOR EVERYTHING
APP_FONT = ("Segoe UI Semibold", 15)
# 🔥 FORCE SAME FONT INSIDE ENTRY BOXES (CRITICAL FIX)
root.option_add("*Font", APP_FONT)

TITLE_FONT = ("Segoe UI Semibold", 20)

style.configure(".", background="#120404", foreground="#f5eaea", font=APP_FONT)
style.configure("TEntry", fieldbackground="#1a0606", foreground="#f5eaea", insertcolor="#ff4d4d", font=APP_FONT)
style.configure("TButton", background="#5c0a0a", foreground="#ffecec", padding=8, font=APP_FONT)
style.map("TButton", background=[("active", "#8b0f0f")])
style.configure("TLabel", background="#120404", foreground="#f5eaea", font=APP_FONT)

style.configure(
    "TCheckbutton",
    background="#120404",
    foreground="#f5eaea",
    font=APP_FONT,
    indicatorcolor="#5c0a0a",
    indicatordiameter=14
)

style.map(
    "TCheckbutton",
    background=[("active", "#120404"), ("selected", "#120404")],
    foreground=[("active", "#f5eaea")]
)

style.configure("TSeparator", background="#5c0a0a")





# -------------------------------------------------
# MAIN 2-COLUMN LAYOUT (LEFT = INPUTS, RIGHT = ACTIONS)
# -------------------------------------------------
main_frame = ttk.Frame(root, padding=12)
main_frame.pack(fill="both", expand=True)

left_frame = ttk.Frame(main_frame)
right_frame = ttk.Frame(main_frame)

left_frame.pack(side="left", fill="both", expand=True, padx=(0,12))
right_frame.pack(side="right", fill="y", padx=(12,0))

# -------------------------------------------------
# COMPATIBILITY ALIAS (DO NOT REMOVE)
# -------------------------------------------------
# This makes all existing ttk.Label(frame, ...)
# ttk.Entry(frame, ...) etc work without changes
frame = left_frame










# VARIABLES
name_var = tk.StringVar()

# -------------------------------------------------
# HORARY MODE
# -------------------------------------------------
horary_mode = tk.IntVar(value=0)
horary_number = tk.StringVar(value="1")

# DATE
dd_var = tk.StringVar()
mm_var = tk.StringVar()
yyyy_var = tk.StringVar()

# TIME
hh_var = tk.StringVar()
min_var = tk.StringVar()
sec_var = tk.StringVar(value="00")



# GOOGLE MAPS FRIENDLY LATITUDE
# Default: +13.319070
lat_sign = tk.StringVar(value="+")
lat_deg  = tk.StringVar(value="13")
lat_frac = tk.StringVar(value="319070")




# GOOGLE MAPS FRIENDLY LONGITUDE
# Default: +77.132645
lon_sign = tk.StringVar(value="+")
lon_deg  = tk.StringVar(value="77")
lon_frac = tk.StringVar(value="132645")

















# -------------------------------------------------
# COORDINATE INPUT MODULE SELECTOR
# -------------------------------------------------

# -------------------------------------------------
# MODULE 2 – DMS VARIABLES (LAT)
# -------------------------------------------------

lat_dms_deg = tk.StringVar(value="13")
lat_dms_dir = tk.StringVar(value="N")
lat_dms_min = tk.StringVar(value="19")
lat_dms_sec = tk.StringVar(value="08")  # derived from 13.319070









# -------------------------------------------------
# MODULE 2 – DMS VARIABLES (LON)
# -------------------------------------------------
lon_dms_deg = tk.StringVar(value="77")
lon_dms_dir = tk.StringVar(value="E")
lon_dms_min = tk.StringVar(value="07")
lon_dms_sec = tk.StringVar(value="57")  # derived from 77.132645





















# -------------------------------------------------
# INTERNAL SYNC LOCK (PREVENT FEEDBACK LOOPS)
# -------------------------------------------------
_sync_lock = {"active": False}





# -------------------------------------------------
# LIVE SYNC: MODULE 1 ⇄ MODULE 2
# -------------------------------------------------
def sync_from_decimal(*args):
    if _sync_lock["active"]:
        return
    try:
        _sync_lock["active"] = True

        lat_val = float(f"{lat_deg.get()}.{lat_frac.get() or '0'}")
        if lat_sign.get() == "-":
            lat_val = -lat_val

        lon_val = float(f"{lon_deg.get()}.{lon_frac.get() or '0'}")
        if lon_sign.get() == "-":
            lon_val = -lon_val

        d, s, m, sec = decimal_to_dms(lat_val, is_lat=True)
        lat_dms_deg.set(d)
        lat_dms_dir.set(s)
        lat_dms_min.set(m)
        lat_dms_sec.set(sec)

        d, s, m, sec = decimal_to_dms(lon_val, is_lat=False)
        lon_dms_deg.set(d)
        lon_dms_dir.set(s)
        lon_dms_min.set(m)
        lon_dms_sec.set(sec)

    finally:
        _sync_lock["active"] = False


def sync_from_dms(*args):
    if _sync_lock["active"]:
        return
    try:
        _sync_lock["active"] = True

        lat_val = dms_to_decimal(
            lat_dms_deg.get(), lat_dms_min.get(), lat_dms_sec.get(), lat_dms_dir.get()
        )
        lon_val = dms_to_decimal(
            lon_dms_deg.get(), lon_dms_min.get(), lon_dms_sec.get(), lon_dms_dir.get()
        )

        lat_sign.set("-" if lat_val < 0 else "+")
        lon_sign.set("-" if lon_val < 0 else "+")

        lat_val = abs(lat_val)
        lon_val = abs(lon_val)

        lat_deg.set(str(int(lat_val)))
        lat_frac.set(f"{lat_val % 1:.6f}".split(".")[1])

        lon_deg.set(str(int(lon_val)))
        lon_frac.set(f"{lon_val % 1:.6f}".split(".")[1])

    finally:
        _sync_lock["active"] = False











# TIME ZONE
tz_sign = tk.StringVar(value="+")
tz_h = tk.StringVar(value="05")
tz_m = tk.StringVar(value="30")
dst_var = tk.StringVar(value="0")






ayan_vars = {
    "Lahiri": tk.IntVar(value=1),
    "KP New": tk.IntVar(value=0),
    "Raman": tk.IntVar(value=0)
}






















# HEADER
ttk.Label(left_frame, text="OFFLINE SWISS EPHEMERIS", font=TITLE_FONT).pack(pady=8)


# NAME
# NAME
ttk.Label(left_frame, text="NAME").pack(anchor="w")
e_name = ttk.Entry(left_frame, textvariable=name_var)

def force_uppercase_name(*args):
    name_var.set(name_var.get().upper())

name_var.trace_add("write", force_uppercase_name)

e_name.pack(fill="x", pady=4)



# -------------------------------------------------
# HORARY INPUT
# -------------------------------------------------
ttk.Checkbutton(
    left_frame,
    text="Horary Mode (KP 1–249)",
    variable=horary_mode
).pack(anchor="w", pady=(8,2))

hf = ttk.Frame(left_frame)
hf.pack(anchor="w")

ttk.Label(hf, text="Horary Number").pack(side="left", padx=(0,6))

e_horary = ttk.Entry(hf, width=8, textvariable=horary_number)
e_horary.pack(side="left")



# initially disabled
e_horary.configure(state="disabled")

def toggle_horary_mode():

    if horary_mode.get():

        e_horary.configure(state="normal")

        # ---------------------------------
        # AUTO SYNC CURRENT LOCAL DATE/TIME
        # ---------------------------------
        now = datetime.now()

        dd_var.set(f"{now.day:02d}")
        mm_var.set(f"{now.month:02d}")
        yyyy_var.set(str(now.year))

        hh_var.set(f"{now.hour:02d}")
        min_var.set(f"{now.minute:02d}")
        sec_var.set(f"{now.second:02d}")

    else:
        e_horary.configure(state="disabled")

horary_mode.trace_add("write", lambda *a: toggle_horary_mode())



# AUTO FOCUS ON APP START
root.after(200, lambda: e_name.focus())

# ENTER → JUMP TO DATE (DD)
def focus_dd(event=None):
    e_dd.focus()

e_name.bind("<Return>", focus_dd)





# DATE
ttk.Label(frame, text="Date (DD  MM  YYYY)").pack(anchor="w", pady=(6,4))
df = ttk.Frame(frame); df.pack(anchor="w")
e_dd = ttk.Entry(df, width=6, textvariable=dd_var)
e_mm = ttk.Entry(df, width=6, textvariable=mm_var)
e_yy = ttk.Entry(df, width=10, textvariable=yyyy_var)
e_dd.pack(side="left", padx=4)
e_mm.pack(side="left", padx=4)
e_yy.pack(side="left", padx=4)






# TIME
ttk.Label(frame, text="Time (HH  MM  SS)").pack(anchor="w", pady=(10,4))
tf = ttk.Frame(frame); tf.pack(anchor="w")
e_hh = ttk.Entry(tf, width=6, textvariable=hh_var)
e_mn = ttk.Entry(tf, width=6, textvariable=min_var)
e_sc = ttk.Entry(tf, width=6, textvariable=sec_var)
e_hh.pack(side="left", padx=4)
e_mn.pack(side="left", padx=4)
e_sc.pack(side="left", padx=4)



# -------------------------------
# SAFE KEY BINDINGS (AFTER WIDGET CREATION)
# -------------------------------
e_dd.bind("<KeyRelease>", lambda e: smart_day_month_jump(e, dd_var, e_mm))
e_mm.bind("<KeyRelease>", lambda e: smart_month_jump(e, mm_var, e_yy))
e_yy.bind("<KeyRelease>", lambda e: jump_if_complete(yyyy_var, e_hh, 4, "yy"))

e_hh.bind("<KeyRelease>", lambda e: smart_hour_jump(e, hh_var, e_mn))




# UTC OFFSET
ttk.Label(frame, text="UTC Offset (+ / −  HH  MM  DST)").pack(anchor="w", pady=(10,4))
uf = ttk.Frame(frame); uf.pack(anchor="w")
ttk.Entry(uf, width=4, textvariable=tz_sign).pack(side="left", padx=4)
ttk.Entry(uf, width=6, textvariable=tz_h).pack(side="left", padx=4)
ttk.Entry(uf, width=6, textvariable=tz_m).pack(side="left", padx=4)
ttk.Label(uf, text="DST").pack(side="left", padx=6)
ttk.Entry(uf, width=6, textvariable=dst_var).pack(side="left")










# -------------------------------------------------
# LATITUDE / LONGITUDE — GOOGLE MAPS FORMAT
# (+ / −  DEG  FRACTION)
# Example:
# + | 13 | 318833  → 13.318833
# - | 77 | 13      → -77.13
# -------------------------------------------------








































# =================================================
# DECIMAL COORDINATES
# =================================================
module1 = ttk.Frame(frame)
module1.pack(anchor="w", fill="x", pady=(4,6))

# Latitude (Module 1)
ttk.Label(module1, text="Latitude (+ / −   Deg   Fraction)").pack(anchor="w")
m1_lat = ttk.Frame(module1)
m1_lat.pack(anchor="w")



e_lat_sign = ttk.Entry(m1_lat, width=4, textvariable=lat_sign, justify="center")
e_lat_deg  = ttk.Entry(m1_lat, width=8, textvariable=lat_deg)
e_lat_frac = ttk.Entry(m1_lat, width=12, textvariable=lat_frac)

e_lat_sign.pack(side="left", padx=4)
e_lat_deg.pack(side="left", padx=4)
e_lat_frac.pack(side="left", padx=4)








# Longitude (Module 1)
ttk.Label(module1, text="Longitude (+ / −   Deg   Fraction)").pack(anchor="w", pady=(6,0))
m1_lon = ttk.Frame(module1)
m1_lon.pack(anchor="w")




e_lon_sign = ttk.Entry(m1_lon, width=4, textvariable=lon_sign, justify="center")
e_lon_deg  = ttk.Entry(m1_lon, width=8, textvariable=lon_deg)
e_lon_frac = ttk.Entry(m1_lon, width=12, textvariable=lon_frac)

e_lon_sign.pack(side="left", padx=4)
e_lon_deg.pack(side="left", padx=4)
e_lon_frac.pack(side="left", padx=4)

















# =================================================
# DEGREE / DIRECTION / MIN / SEC
# =================================================
module2 = ttk.Frame(frame)
module2.pack(anchor="w", fill="x", pady=(4,6))

# Latitude (Module 2)
ttk.Label(module2, text="Latitude (Deg  Dir  Min  Sec)").pack(anchor="w")
m2_lat = ttk.Frame(module2)
m2_lat.pack(anchor="w")





lat2_deg = ttk.Entry(m2_lat, width=8, textvariable=lat_dms_deg)
lat2_dir = ttk.Entry(m2_lat, width=4, textvariable=lat_dms_dir, justify="center")
lat2_min = ttk.Entry(m2_lat, width=6, textvariable=lat_dms_min)
lat2_sec = ttk.Entry(m2_lat, width=6, textvariable=lat_dms_sec)

lat2_deg.pack(side="left", padx=4)
lat2_dir.pack(side="left", padx=4)
lat2_min.pack(side="left", padx=4)
lat2_sec.pack(side="left", padx=4)











# Longitude (Module 2)
ttk.Label(module2, text="Longitude (Deg  Dir  Min  Sec)").pack(anchor="w", pady=(6,0))
m2_lon = ttk.Frame(module2)
m2_lon.pack(anchor="w")





lon2_deg = ttk.Entry(m2_lon, width=8, textvariable=lon_dms_deg)
lon2_dir = ttk.Entry(m2_lon, width=4, textvariable=lon_dms_dir, justify="center")
lon2_min = ttk.Entry(m2_lon, width=6, textvariable=lon_dms_min)
lon2_sec = ttk.Entry(m2_lon, width=6, textvariable=lon_dms_sec)

lon2_deg.pack(side="left", padx=4)
lon2_dir.pack(side="left", padx=4)
lon2_min.pack(side="left", padx=4)
lon2_sec.pack(side="left", padx=4)







































# -------------------------------------------------
# RIGHT PANEL – ACTIONS (ALWAYS VISIBLE)
# -------------------------------------------------
ttk.Label(
    right_frame,
    text="Actions",
    font=("Segoe UI Semibold", 18)
).pack(pady=(4,10))

ttk.Button(
    right_frame,
    text="Set Output Folder",
    command=choose_output_folder,
    width=22
).pack(pady=8)

out_label = ttk.Label(
    right_frame,
    text=f"Output folder:\n{settings['output_dir'] or 'Not set'}",
    wraplength=260,
    justify="left"
)
out_label.pack(pady=8)

ttk.Separator(right_frame).pack(fill="x", pady=10)


ttk.Button(
    right_frame,
    text="Calculate & Save",
    command=calculate_and_save,
    width=22
).pack(pady=12)




ttk.Button(
    right_frame,
    text="Clear Name / Date / Time",
    command=clear_basic_fields,
    width=22
).pack(pady=6)
    


ttk.Button(
    right_frame,
    text="Open Output Folder",
    command=open_output_folder,
    width=22
).pack(pady=6)


# -------------------------------------------------
# FILL CURRENT TIME (HORARY)
# -------------------------------------------------
def fill_current_time():

    now = datetime.now()

    dd_var.set(f"{now.day:02d}")
    mm_var.set(f"{now.month:02d}")
    yyyy_var.set(str(now.year))

    hh_var.set(f"{now.hour:02d}")
    min_var.set(f"{now.minute:02d}")
    sec_var.set(f"{now.second:02d}")

    # auto name if empty
    if not name_var.get().strip():
        name_var.set(now.strftime("%Y-%m-%d ~~ %H-%M-%S"))

ttk.Button(
    right_frame,
    text="Fill Current Time",
    command=fill_current_time,
    width=22
).pack(pady=6)













# -------------------------------------------------
# ACTIVATE LIVE SYNC (AFTER UI IS READY)
# -------------------------------------------------
for v in (lat_deg, lat_frac, lat_sign, lon_deg, lon_frac, lon_sign):
    v.trace_add("write", sync_from_decimal)

for v in (
    lat_dms_deg, lat_dms_dir, lat_dms_min, lat_dms_sec,
    lon_dms_deg, lon_dms_dir, lon_dms_min, lon_dms_sec
):
    v.trace_add("write", sync_from_dms)









root.mainloop()




