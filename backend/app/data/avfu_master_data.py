"""AVFU organisational master data, transcribed from the client submissions.

Sources (all dated July-August 2026):
  * Oragnogram_Hierarchy.png              — apex reporting chain
  * HRMS_CVSc_AVFU(K)_General_Ofiice.pdf  — Faculty of Veterinary Science, Khanapara
  * HRMS_CVSc_AVFU(K)_Clinical_Complex.pdf— Veterinary Clinical Complex
  * HRMS data of LCVSC 6.8.2026.pdf       — Lakhimpur College of Vety. Science
  * HRMS_Fishery.pdf                      — Faculty of Fisheries Science, Raha
  * HRMS_CVSc_AVFU(K)_Directorate of Research.pdf
  * HRMS-LRS- Mandira.pdf                 — Livestock Research Station, Mandira
  * AVFU-GOAT RESEARCH STATION.pdf        — Goat Research Station, Burnihat
  * HRMS_CVSc_AVFU(K)_ DPGS,.pdf          — Directorate of Post Graduate Studies
  * HRMS_CVSc_AVFU(K)_Extension_Education.pdf
  * HRMS_CVSc_AVFU(K)_Physical_Plant.pdf  — Directorate of Physical Plant
  * HRMS_AVFU_Office of Comptroller.pdf
  * HRMS_CVSc_AVFU(K)_ Library.PDF        — Office of the Librarian

This module is *initial* master data only.  It is imported into the database
by ``seed.py``; nothing here is read at runtime, and Admin/HR can change any
of it afterwards through the web interface.
"""

# ---------------------------------------------------------------------------
# Campuses / locations
# ---------------------------------------------------------------------------
LOCATIONS = [
    {
        "key": "khanapara",
        "name": "Khanapara, Guwahati",
        "code": "KHP",
        "address": "Assam Veterinary and Fishery University, Khanapara",
        "city": "Guwahati",
        "district": "Kamrup (Metro)",
        "pincode": "781022",
    },
    {
        "key": "raha",
        "name": "Raha, Nagaon",
        "code": "RAH",
        "address": "Faculty of Fisheries Science, AVFU, Raha",
        "city": "Raha",
        "district": "Nagaon",
        "pincode": "782103",
    },
    {
        "key": "joyhing",
        "name": "Joyhing, North Lakhimpur",
        "code": "JOY",
        "address": "Lakhimpur College of Veterinary Science, Joyhing",
        "city": "North Lakhimpur",
        "district": "Lakhimpur",
        "pincode": "787051",
    },
    {
        "key": "mandira",
        "name": "Mandira",
        "code": "MND",
        "address": "Livestock Research Station, Mandira",
        "city": "Mandira",
        "district": "Kamrup",
        "pincode": "781101",
    },
    {
        "key": "burnihat",
        "name": "Burnihat",
        "code": "BRN",
        "address": "AVFU Goat Research Station, Burnihat",
        "city": "Burnihat",
        "district": "Kamrup (Metro)",
        "pincode": "781023",
    },
]

# ---------------------------------------------------------------------------
# Organisational hierarchy
# ---------------------------------------------------------------------------
# (key, name, short_name, org_type, parent_key, location_key, reports_to_key,
#  contact_email, contact_phone)
ORGANIZATIONS = [
    # ---- Apex Apex Node ---------------------------------------------------
    ("chancellor", "Chancellor (Governor of Assam)", "Chancellor", "establishment",
     None, "khanapara", None, "", ""),

    # ---- Executive Head ----------------------------------------------------
    ("avfu", "Vice-Chancellor", "VC", "university",
     "chancellor", "khanapara", "chancellor", "", ""),

    # ---- Advisory / Governance Bodies (Under Vice-Chancellor) ------------
    ("board_of_mgmt", "Board of Management", "BoM", "establishment",
     "avfu", "khanapara", "avfu", "", ""),
    ("academic_council", "Academic Council", "AC", "establishment",
     "avfu", "khanapara", "avfu", "", ""),

    # ---- Principal Officers (Under Vice-Chancellor) ------------------------
    ("registrar", "Office of the Registrar", "Registrar", "establishment",
     "avfu", "khanapara", "avfu", "", ""),
    ("comptroller", "Office of the Financial Officer / Comptroller", "Financial Officer", "establishment",
     "avfu", "khanapara", "avfu", "", ""),
    ("coe", "Office of the Controller of Examination", "CoE", "establishment",
     "avfu", "khanapara", "avfu", "", ""),
    ("library", "Office of the Librarian", "Librarian", "establishment",
     "avfu", "khanapara", "avfu", "", ""),

    # ---- Deans Division ----------------------------------------------------
    ("deans_group", "Deans", "Deans", "establishment",
     "avfu", "khanapara", "avfu", "", ""),
    ("fvsc", "Dean, Faculty of Veterinary Science, Khanapara", "Dean CVSc", "college",
     "deans_group", "khanapara", "deans_group", "", ""),
    ("lcvsc", "Associate Dean, Lakhimpur College of Veterinary Science, Joyhing", "Assoc Dean LCVSc", "college",
     "fvsc", "joyhing", "fvsc", "", ""),
    ("ffsc", "Dean, Faculty of Fisheries Science, Raha", "Dean CFSc", "college",
     "deans_group", "raha", "deans_group", "", ""),

    # ---- Directors Division ------------------------------------------------
    ("directors_group", "Directors", "Directors", "establishment",
     "avfu", "khanapara", "avfu", "", ""),

    # 1. Directorate of Research & Subordinates
    ("dor", "Director of Research", "DoR", "establishment",
     "directors_group", "khanapara", "directors_group", "", ""),
    ("ddr", "Deputy Director of Research", "DDR", "establishment",
     "dor", "khanapara", "dor", "", ""),
    ("lrs_mandira", "Chief Scientists LRS, Mandira", "LRS Mandira", "establishment",
     "dor", "mandira", "dor", "", ""),
    ("grs_burnihat", "Chief Scientists GRS, Burnihat", "GRS Burnihat", "establishment",
     "dor", "burnihat", "dor", "", ""),

    # 2. Directorate of Post-Graduate Studies
    ("dpgs", "Director of Post-Graduate Studies", "DPGS", "establishment",
     "directors_group", "khanapara", "directors_group", "", ""),

    # 3. Directorate of Extension Education & Subordinates
    ("doee", "Director of Extension Education", "DoEE", "establishment",
     "directors_group", "khanapara", "directors_group", "", ""),
    ("adee", "Associate Director of Extension Education", "ADEE", "establishment",
     "doee", "khanapara", "doee", "", ""),

    # 4. Directorate of Student Welfare & Subordinates
    ("dsw", "Director of Student Welfare", "DSW", "establishment",
     "directors_group", "khanapara", "directors_group", "", ""),
    ("ddsw", "Deputy Director of Student Welfare", "DDSW", "establishment",
     "dsw", "khanapara", "dsw", "", ""),

    # 5. Directorate of Physical Plant & Subordinates
    ("dopp", "Director of Physical Plant", "DoPP", "establishment",
     "directors_group", "khanapara", "directors_group", "", ""),
    ("engineers_dopp", "Engineers (Civil, Electrical, Architect)", "DoPP Engineers", "establishment",
     "dopp", "khanapara", "dopp", "", ""),

    # ---- CVSc Establishments -----------------------------------------------
    ("dean_cvsc", "Office of the Dean (CVSc)", "Dean CVSc Office", "establishment",
     "fvsc", "khanapara", "fvsc", "", ""),
    ("vcc", "Veterinary Clinical Complex", "VCC", "establishment",
     "fvsc", "khanapara", "dean_cvsc", "", ""),
    ("ac_ug_cvsc", "Academic Cell (UG) (CVSc)", "AC UG CVSc", "establishment",
     "fvsc", "khanapara", "dean_cvsc", "", ""),
    ("ac_pg_cvsc", "Academic Cell (PG) (CVSc)", "AC PG CVSc", "establishment",
     "fvsc", "khanapara", "dean_cvsc", "", ""),
    ("lib_cvsc", "Office of the Deputy Librarian (CVSc)", "Lib CVSc", "establishment",
     "fvsc", "khanapara", "dean_cvsc", "", ""),

    # ---- CFSc Establishments -----------------------------------------------
    ("dean_cfsc", "Office of the Dean (CFSc)", "Dean CFSc Office", "establishment",
     "ffsc", "raha", "ffsc", "", ""),
    ("lib_cfsc", "Office of the Deputy Librarian (CFSc)", "Lib CFSc", "establishment",
     "ffsc", "raha", "dean_cfsc", "", ""),
    ("fish_farm_cfsc", "Fish Farm (CFSc)", "Fish Farm", "establishment",
     "ffsc", "raha", "dean_cfsc", "", ""),
    ("med_cfsc", "Medical Unit (CFSc)", "Med CFSc", "establishment",
     "ffsc", "raha", "dean_cfsc", "", ""),
    ("dopp_cfsc", "Directorate of Physical Plant (Fishery Unit)", "DoPP CFSc", "establishment",
     "ffsc", "raha", "dean_cfsc", "", ""),
    ("ddsw_cfsc", "Deputy Directorate of Student Welfare (CFSc)", "DDSW CFSc", "establishment",
     "ffsc", "raha", "dean_cfsc", "", ""),
    ("ac_ug_cfsc", "Academic Cell (UG) (CFSc)", "AC UG CFSc", "establishment",
     "ffsc", "raha", "dean_cfsc", "", ""),
    ("ac_pg_cfsc", "Academic Cell (PG) (CFSc)", "AC PG CFSc", "establishment",
     "ffsc", "raha", "dean_cfsc", "", ""),

    # ---- LCVSc Establishments ----------------------------------------------
    ("adean_lcvsc", "Office of the Associate Dean (LCVSc)", "Assoc Dean LCVSc", "establishment",
     "lcvsc", "joyhing", "lcvsc", "", ""),
    ("ddsw_lcvsc", "Deputy Directorate of Students Welfare (LCVSc)", "DDSW LCVSc", "establishment",
     "lcvsc", "joyhing", "adean_lcvsc", "", ""),
]

# ---------------------------------------------------------------------------
# Department vs Establishment — the only two categories
# ---------------------------------------------------------------------------
# There is no third "organisation" bucket. Every real AVFU unit is either:
#
#   Department (academic)      — a College, or a named teaching Department
#                                 under one (see ACADEMIC_DEPARTMENTS below).
#   Establishment (administrative) — a Directorate, Office or Research
#                                 Station, and the Sections/Units/Cells
#                                 under it.
#
# The three Colleges (FVSc, LCVSc, FFSc) and the Veterinary Clinical
# Complex are academic -> Department. Every other top-level office listed
# in ORGANIZATIONS is administrative -> Establishment; that Establishment
# set is provisional pending the client's own definitive Establishment
# list and will be refreshed here the moment it is supplied — nothing
# about the *screens* or *Employee ID logic* needs to change when it is,
# only this classification data.
ORG_CATEGORY = {
    "fvsc": "department",
    "lcvsc": "department",
    "ffsc": "department",
    "vcc": "department",
    # -- administrative (provisional, pending the client's Establishment list) --
    "vc_office": "establishment",
    "registrar": "establishment",
    "comptroller": "establishment",
    "coe": "establishment",
    "library": "establishment",
    "dsw": "establishment",
    "dor": "establishment",
    "lrs": "establishment",
    "grs": "establishment",
    "dpgs": "establishment",
    "dee": "establishment",
    "dopp": "establishment",
}

# A clean, ID-safe "Short Form" for every College/Establishment that needs
# one — used to build Employee IDs as AVFU/<short form>/<seq>. Configurable
# afterwards by Admin/HR through the Departments/Establishments screens.
ORG_SHORT_FORMS = {
    "fvsc": "FVSC",
    "vcc": "VCC",
    "lcvsc": "LCVSC",
    "ffsc": "FFSC",
    "dor": "DOR",
    "lrs": "LRSM",
    "grs": "GRSB",
    "dpgs": "DPGS",
    "dee": "DOEE",
    "dopp": "DOPP",
    "comptroller": "COMPT",
    "library": "LIB",
}

# ---------------------------------------------------------------------------
# Academic Departments — the real AVFU list, supplied directly by the client
# ---------------------------------------------------------------------------
# (parent_college_key, department name). Each becomes a Department-category
# node under its College. VCC is handled separately above (it already has
# its own ORGANIZATIONS entry with real Part-B/Part-C submission data) and
# is deliberately not repeated here, even though LCVSc's own list names one
# too — see the LCVSc "Veterinary Clinical Complex" rename in SECTIONS below,
# which keeps the two distinct units from ever being confused.
ACADEMIC_DEPARTMENTS = [
    # -- College of Veterinary Science (fvsc) --
    ("fvsc", "Department of Animal Biotechnology"),
    ("fvsc", "Department of Anatomy & Histology"),
    ("fvsc", "Department of Animal Genetics & Breeding"),
    ("fvsc", "Department of Animal Nutrition"),
    ("fvsc", "Department of Animal Reproduction, Gynaecology & Obstetrics"),
    ("fvsc", "Department of Extension Education"),
    ("fvsc", "Department of Livestock Farm Complex"),
    ("fvsc", "Department of Instructional Poultry Farm"),
    ("fvsc", "Department of Livestock Production & Management"),
    ("fvsc", "Department of Livestock Products Technology"),
    ("fvsc", "Department of Poultry Science"),
    ("fvsc", "Department of Veterinary Biochemistry"),
    ("fvsc", "Department of Veterinary Clinical Medicine, Ethics & Jurisprudence"),
    ("fvsc", "Department of Veterinary Epidemiology & Preventive Medicine"),
    ("fvsc", "Department of Veterinary Microbiology"),
    ("fvsc", "Department of Veterinary Parasitology"),
    ("fvsc", "Department of Veterinary Pathology"),
    ("fvsc", "Department of Veterinary Pharmacology & Toxicology"),
    ("fvsc", "Department of Veterinary Physiology"),
    ("fvsc", "Department of Veterinary Public Health"),
    ("fvsc", "Department of Veterinary Surgery & Radiology"),
    # -- College of Fishery Science (ffsc) --
    ("ffsc", "Department of Aquaculture"),
    ("ffsc", "Department of Aquatic Animal Health Management"),
    ("ffsc", "Department of Aquatic Environment Management"),
    ("ffsc", "Department of Fish Processing Technology"),
    ("ffsc", "Department of Fisheries Engineering"),
    ("ffsc", "Department of Fishery Extension, Economics & Statistics"),
    ("ffsc", "Department of Fishery Resource Management"),
    # -- Lakhimpur College of Veterinary Science (lcvsc) --
    ("lcvsc", "Department of Anatomy & Histology"),
    ("lcvsc", "Department of Animal Genetics & Breeding"),
    ("lcvsc", "Department of Animal Nutrition"),
    ("lcvsc", "Department of Animal Reproduction, Gynaecology & Obstetrics"),
    ("lcvsc", "Department of Extension Education"),
    ("lcvsc", "Department of Livestock Farm Complex"),
    ("lcvsc", "Department of Livestock Production & Management"),
    ("lcvsc", "Department of Livestock Products Technology"),
    ("lcvsc", "Department of Veterinary Physiology and Biochemistry"),
    ("lcvsc", "Department of Veterinary Clinical Medicine, Ethics & Jurisprudence"),
    ("lcvsc", "Department of Veterinary Epidemiology & Preventive Medicine"),
    ("lcvsc", "Department of Veterinary Microbiology"),
    ("lcvsc", "Department of Veterinary Parasitology"),
    ("lcvsc", "Department of Veterinary Pathology"),
    ("lcvsc", "Department of Veterinary Pharmacology & Toxicology"),
    ("lcvsc", "Department of Veterinary Public Health"),
    ("lcvsc", "Department of Veterinary Surgery & Radiology"),
]

# ---------------------------------------------------------------------------
# Explicit Colleges & Establishments Data
# ---------------------------------------------------------------------------
COLLEGES_DATA = [
    {
        "key": "avfu",
        "code": "AVFU",
        "name": "Assam Veterinary and Fishery University",
        "short_name": "AVFU",
        "location_key": "khanapara",
    },
    {
        "key": "fvsc",
        "code": "CVSc",
        "name": "College of Veterinary Science (CVSc), Khanapara",
        "short_name": "CVSc",
        "location_key": "khanapara",
    },
    {
        "key": "ffsc",
        "code": "CFSc",
        "name": "College of Fishery Science (CFSc), Raha",
        "short_name": "CFSc",
        "location_key": "raha",
    },
    {
        "key": "lcvsc",
        "code": "LCVSc",
        "name": "Lakhimpur College of Veterinary Science (LCVSc), Joyhing",
        "short_name": "LCVSc",
        "location_key": "joyhing",
    },
]


# ---------------------------------------------------------------------------
# Establishments Data
# ---------------------------------------------------------------------------
# (college_key, key, name, short_name, code, location_key)
#   college_key: "avfu" = AVFU-level, "fvsc" = CVSc, "ffsc" = CFSc, "lcvsc" = LCVSc
ESTABLISHMENTS_DATA = [
    # ---- AVFU-level Establishments ----------------------------------------
    ("avfu", "vc_office",   "Office of the Vice Chancellor",             "VC Office",  "VC",      "khanapara"),
    ("avfu", "registrar",   "Office of the Registrar",                   "Registrar",  "REG",     "khanapara"),
    ("avfu", "comptroller", "Office of the Comptroller",                 "Comptroller","COMPT",   "khanapara"),
    ("avfu", "dor",         "Directorate of Research",                   "DoR",        "DOR",     "khanapara"),
    ("avfu", "doee",        "Directorate of Extension Education",        "DoEE",       "DOEE",    "khanapara"),
    ("avfu", "dopp",        "Directorate of Physical Plant",             "DoPP",       "DOPP",    "khanapara"),
    ("avfu", "dsw",         "Directorate of Students Welfare",           "DSW",        "DSW",     "khanapara"),
    ("avfu", "dpgs",        "Directorate of Post Graduate Studies",      "DPGS",       "DPGS",    "khanapara"),
    ("avfu", "coe",         "Office of the Controller of Examination",   "CoE",        "COE",     "khanapara"),
    ("avfu", "library",     "Office of the Librarian",                   "Library",    "LIB",     "khanapara"),
    ("avfu", "lrs_mandira", "Livestock Research Station, Mandira",       "LRS Mandira","LRSM",    "mandira"),
    ("avfu", "grs_burnihat","Goat Research Station, Burnihat",           "GRS Burnihat","GRSB",   "burnihat"),

    # ---- CVSc (College of Veterinary Science, Khanapara) Establishments ---
    ("fvsc", "dean_cvsc",   "Office of the Dean",                        "Dean CVSc",  "DEAN-KHP","khanapara"),
    ("fvsc", "vcc",         "Veterinary Clinical Complex",               "VCC",        "VCC",     "khanapara"),
    ("fvsc", "ac_ug_cvsc",  "Academic Cell (UG)",                        "AC UG CVSc", "ACUG-KHP","khanapara"),
    ("fvsc", "ac_pg_cvsc",  "Academic Cell (PG)",                        "AC PG CVSc", "ACPG-KHP","khanapara"),
    ("fvsc", "lib_cvsc",    "Office of the Deputy Librarian",            "Lib CVSc",   "LIB-KHP", "khanapara"),

    # ---- CFSc (College of Fishery Science, Raha) Establishments -----------
    ("ffsc", "dean_cfsc",   "Office of the Dean",                        "Dean CFSc",  "DEAN-RAH","raha"),
    ("ffsc", "lib_cfsc",    "Office of the Deputy Librarian",            "Lib CFSc",   "LIB-RAH", "raha"),
    ("ffsc", "fish_farm",   "Fish Farm",                                 "Fish Farm",  "FARM-RAH","raha"),
    ("ffsc", "med_cfsc",    "Medical Unit",                              "Med CFSc",   "MED-RAH", "raha"),
    ("ffsc", "dopp_cfsc",   "Directorate of Physical Plant (Fishery Unit)","DoPP CFSc","DOPP-RAH","raha"),
    ("ffsc", "ddsw_cfsc",   "Deputy Directorate of Student Welfare",     "DDSW CFSc",  "DDSW-RAH","raha"),
    ("ffsc", "ac_ug_cfsc",  "Academic Cell (UG)",                        "AC UG CFSc", "ACUG-RAH","raha"),
    ("ffsc", "ac_pg_cfsc",  "Academic Cell (PG)",                        "AC PG CFSc", "ACPG-RAH","raha"),

    # ---- LCVSc (Lakhimpur College of Veterinary Science) Establishments ---
    ("lcvsc","adean_lcvsc", "Office of the Associate Dean",              "Assoc Dean", "ADEAN-JOY","joyhing"),
    ("lcvsc","ddsw_lcvsc",  "Deputy Directorate of Students Welfare",    "DDSW LCVSc", "DDSW-JOY","joyhing"),
]


# ---------------------------------------------------------------------------
# Designations
# ---------------------------------------------------------------------------
# (name, short_name, category, rank_level) — lower rank = more senior
DESIGNATIONS = [
    ("Vice-Chancellor", "VC", "officer", 2),
    ("Registrar", "", "officer", 5),
    ("Financial Officer", "FO", "officer", 5),
    ("Controller of Examination", "CoE", "officer", 6),
    ("Librarian", "", "officer", 6),
    ("Dean", "", "officer", 8),
    ("Director of Research", "DR", "officer", 8),
    ("Director of Post Graduate Studies", "DPGS", "officer", 8),
    ("Director of Extension Education", "DoEE", "officer", 8),
    ("Director of Student Welfare", "DSW", "officer", 8),
    ("Director of Physical Plant", "DoPP", "officer", 8),
    ("Associate Dean", "", "officer", 9),
    ("Deputy Director of Research", "DDR", "officer", 10),
    ("Associate Director of Extension Education", "ADEE", "officer", 10),
    ("Deputy Director of Student Welfare", "DDSW", "officer", 10),
    ("Deputy Comptroller", "", "officer", 10),
    ("Chief Scientist", "", "scientific", 12),
    ("Assistant Comptroller", "", "accounts", 12),
    ("Deputy Librarian", "", "administrative", 13),
    ("In-charge Academic Cell (PG)", "", "teaching", 14),

    ("Professor", "", "teaching", 15),
    ("Associate Professor", "", "teaching", 16),
    ("Assistant Professor", "", "teaching", 17),

    ("Senior Scientist", "Sr. Scientist", "scientific", 17),
    ("Scientist", "", "scientific", 18),

    ("Senior Extension Specialist", "Sr. Ext. Specialist", "scientific", 17),
    ("Extension Specialist", "", "scientific", 18),

    ("Finance Officer", "FO", "officer", 5),
    ("Administrative Officer", "AO", "administrative", 20),
    ("Executive Engineer", "EE", "technical", 20),
    ("Medical Officer", "MO", "technical", 20),
    ("Deputy Manager", "", "administrative", 21),
    ("Finance & Accounts Officer", "FAO", "accounts", 21),
    ("Accounts Officer", "", "accounts", 21),
    ("Assistant Engineer (Civil)", "AE (C)", "technical", 21),
    ("Assistant Engineer (Electrical)", "AE (E)", "technical", 21),
    ("Instrumentation Engineer", "", "technical", 21),
    ("Section Officer", "SO", "administrative", 22),
    ("Superintendent of Accounts", "SoA", "accounts", 22),
    ("Assistant Librarian", "", "administrative", 22),
    ("Subordinate Engineer", "Sub-Eng", "technical", 22),
    ("Assistant Section Officer", "ASO", "administrative", 23),
    ("Documentation Officer", "", "administrative", 23),
    ("Technical Supervisor-I", "", "technical", 23),
    ("Technical Supervisor-II", "", "technical", 23),
    ("Executive Assistant to Dean", "", "administrative", 24),
    ("Executive Assistant to Director", "", "administrative", 24),
    ("Senior Accountant", "Sr. Actt.", "accounts", 24),
    ("Senior Technical Assistant", "", "technical", 24),
    ("Technical Assistant", "", "technical", 24),
    ("Scientific Supervisor-II", "", "technical", 24),
    ("Lab. Assistant-II (Scientific Supervisor-II)", "", "technical", 24),
    ("Veterinary Technical Supervisor-II", "", "technical", 24),
    ("Field Assistant-II (Technical Supervisor-II)", "FA II", "technical", 24),
    ("Senior Administrative Assistant", "SAA", "administrative", 25),
    ("Farm Manager", "", "technical", 25),
    ("Scientific Assistant", "", "technical", 25),
    ("Lab. Assistant-III (Scientific Assistant)", "", "technical", 25),
    ("Laboratory Assistant", "", "technical", 25),
    ("Veterinary Technical Assistant", "", "technical", 25),
    ("Veterinary Field Assistant", "", "technical", 25),
    ("Veterinary Field Assistant-II", "", "technical", 25),
    ("Veterinary Technical/Scientific Assistant", "", "technical", 25),
    ("Field Assistant-III (Technical Assistant)", "", "technical", 25),
    ("Section Assistant", "", "technical", 25),
    ("Library Maintenance Assistant", "", "technical", 25),
    ("Radiographer", "", "technical", 25),
    ("Nurse-II", "", "technical", 25),
    ("Pharmacist-III", "", "technical", 25),
    ("Assistant Security Officer", "", "support", 25),
    ("Junior Accountant", "Jr. Actt.", "accounts", 26),
    ("Junior Administrative Assistant", "JAA", "administrative", 26),
    ("Computer Assistant", "", "administrative", 26),
    ("Junior Library Assistant", "", "administrative", 26),
    ("Store Keeper", "", "support", 26),
    ("Photographer cum Media Technician", "", "technical", 26),
    ("Security Supervisor", "", "support", 26),
    ("Nurse-III", "", "technical", 26),
    ("Dresser", "", "technical", 26),
    ("Typist", "", "administrative", 27),
    ("Classifier", "", "administrative", 27),
    ("Cataloguer", "", "administrative", 27),
    ("Xerox Operator", "", "support", 27),
    ("Gestetner Operator", "", "support", 27),
    ("Driver", "", "support", 27),
    ("Driver cum Mechanic", "", "support", 27),
    ("Tractor Driver", "", "support", 27),
    ("Tractor cum Powertiller Operator", "", "support", 27),
    ("Mechanic cum Machine Man-II", "", "support", 27),
    ("Mechanic cum Machine Man-III", "", "support", 28),
    ("Electrician", "", "support", 28),
    ("Electrician Helper", "", "support", 28),
    ("Plumber", "", "support", 28),
    ("Plumber Helper", "", "support", 28),
    ("Tractor Helper", "", "support", 28),
    ("Animal Attendant", "", "support", 28),
    ("Milk Recorder", "", "support", 28),
    ("Milk Man", "", "support", 28),
    ("Cook Man", "", "support", 28),
    ("Guest House Attendant", "", "support", 28),
    ("Chowkidar", "", "support", 28),
    ("Messenger", "", "support", 28),
    ("Resident Veterinary Doctor", "", "technical", 28),
    ("Young Professional-II (Vety. Doctor)", "", "technical", 28),
    ("Multitasking Staff-I (Grade-IV Sr.)", "MTS I", "support", 29),
    ("Multitasking Staff-II (Grade-IV Jr.)", "MTS II", "support", 30),
    ("Multi-Tasking Staff (I & II)", "MTS", "support", 30),
    ("Peon", "", "support", 30),
    ("Sweeper", "", "support", 30),
    ("Muster Roll Worker", "MR Worker", "support", 30),
    ("Contractual Employee", "", "support", 30),
]

# ---------------------------------------------------------------------------
# Sanctioned posts (Part B of every submission)
# ---------------------------------------------------------------------------
# (org_key, designation, sanctioned, reported_vacant, level, reports_to_note, remarks)
POSTS = [
    # ---- Faculty of Veterinary Science, Khanapara -------------------------
    ("fvsc", "Dean", 1, 0, "1", "Registrar / Financial Officer / Vice-Chancellor", ""),
    ("fvsc", "Professor", 35, 0, "2", "HOD / Dean / Registrar", ""),
    ("fvsc", "Associate Professor", 57, 0, "2", "HOD / Dean / Registrar", ""),
    ("fvsc", "Assistant Professor", 123, 0, "2", "HOD / Dean / Registrar", ""),
    ("fvsc", "Deputy Manager", 1, 0, "3", "I/c AKMIT Cell / Dean / Registrar", ""),
    ("fvsc", "Administrative Officer", 1, 0, "3", "Dean / Registrar", ""),
    ("fvsc", "Assistant Comptroller", 1, 0, "3", "Dean / Financial Officer", ""),
    ("fvsc", "Farm Manager", 1, 0, "3", "HOD / Dean / Registrar", ""),
    ("fvsc", "Finance & Accounts Officer", 1, 0, "3",
     "Asstt. Comptroller / Dean / Financial Officer", ""),
    ("fvsc", "Instrumentation Engineer", 1, 0, "4",
     "Administrative Officer / Dean / Registrar", ""),
    ("fvsc", "Section Officer", 1, 0, "4",
     "Administrative Officer / Dean / Registrar", ""),
    ("fvsc", "Superintendent of Accounts", 1, 0, "4",
     "Asstt. Comptroller / Dean / Financial Officer", ""),
    ("fvsc", "Assistant Section Officer", 2, 0, "4",
     "Administrative Officer / Dean / Registrar", ""),
    ("fvsc", "Executive Assistant to Dean", 1, 0, "4",
     "Administrative Officer / Dean / Registrar", ""),
    ("fvsc", "Senior Accountant", 2, 0, "5",
     "Asstt. Comptroller / Dean / Financial Officer", ""),
    ("fvsc", "Senior Administrative Assistant", 3, 0, "5",
     "Administrative Officer / Dean / Registrar", ""),
    ("fvsc", "Junior Accountant", 6, 0, "5",
     "Asstt. Comptroller / Dean / Financial Officer", ""),
    ("fvsc", "Junior Administrative Assistant", 24, 0, "5",
     "HOD / Administrative Officer / Dean / Registrar", ""),
    ("fvsc", "Computer Assistant", 24, 0, "5",
     "HOD / Administrative Officer / Dean / Registrar", ""),
    ("fvsc", "Driver cum Mechanic", 10, 0, "5",
     "In-charge Vehicle / Dean / Registrar", ""),
    ("fvsc", "Lab. Assistant-II (Scientific Supervisor-II)", 31, 0, "5",
     "HOD / Dean / Registrar", ""),
    ("fvsc", "Lab. Assistant-III (Scientific Assistant)", 53, 0, "5",
     "HOD / Dean / Registrar", ""),
    ("fvsc", "Mechanic cum Machine Man-II", 1, 0, "5",
     "In-charge Vehicle / HOD / Dean / Registrar", ""),
    ("fvsc", "Veterinary Technical Supervisor-II", 4, 0, "5",
     "HOD / Dean / Registrar", ""),
    ("fvsc", "Mechanic cum Machine Man-III", 2, 0, "5",
     "In-charge Vehicle / HOD / Dean / Registrar", ""),
    ("fvsc", "Veterinary Technical Assistant", 6, 0, "5",
     "HOD / Dean / Registrar", ""),
    ("fvsc", "Tractor cum Powertiller Operator", 2, 0, "5",
     "In-charge Vehicle / HOD / Dean / Registrar", ""),
    ("fvsc", "Field Assistant-II (Technical Supervisor-II)", 1, 0, "5",
     "HOD / Dean / Registrar", ""),
    ("fvsc", "Field Assistant-III (Technical Assistant)", 1, 0, "5",
     "HOD / Dean / Registrar", ""),
    ("fvsc", "Assistant Security Officer", 1, 0, "5", "Dean / Registrar", ""),
    ("fvsc", "Security Supervisor", 1, 0, "6",
     "Assistant Security Officer / Dean / Registrar", ""),
    ("fvsc", "Photographer cum Media Technician", 1, 0, "5",
     "HOD / Dean / Registrar", ""),
    ("fvsc", "Radiographer", 2, 0, "5", "HOD / Dean / Registrar", ""),
    ("fvsc", "Dresser", 3, 0, "6", "SMO / Dean / Registrar", ""),
    ("fvsc", "Medical Officer", 2, 0, "5", "SMO / Dean / Registrar", ""),
    ("fvsc", "Nurse-II", 1, 0, "5", "SMO / Dean / Registrar", ""),
    ("fvsc", "Nurse-III", 1, 0, "6", "SMO / Dean / Registrar", ""),
    ("fvsc", "Pharmacist-III", 1, 0, "6", "SMO / Dean / Registrar", ""),
    ("fvsc", "Multitasking Staff-I (Grade-IV Sr.)", 62, 0, "6",
     "Administrative Officer / HOD / Dean / Registrar", ""),
    ("fvsc", "Multitasking Staff-II (Grade-IV Jr.)", 118, 0, "6",
     "Administrative Officer / HOD / Dean / Registrar", ""),
    ("fvsc", "Sweeper", 9, 0, "6",
     "Administrative Officer / SMO / Dean / Registrar", ""),

    # ---- Veterinary Clinical Complex --------------------------------------
    ("vcc", "Professor", 1, 0, "1", "Dean, FVSc, AVFU", ""),
    ("vcc", "Associate Professor", 3, 0, "2", "Professor, VCC", ""),
    ("vcc", "Assistant Professor", 5, 0, "3", "Professor, VCC", ""),
    ("vcc", "Junior Administrative Assistant", 1, 1, "4",
     "Professor, VCC", "Nil in position"),
    ("vcc", "Field Assistant-II (Technical Supervisor-II)", 0, 0, "5",
     "Professor, VCC",
     "Looking after all office administration and accounts work in place of JAA"),
    ("vcc", "Veterinary Field Assistant-II", 0, 0, "6", "Assistant Professor", ""),
    ("vcc", "Resident Veterinary Doctor", 0, 0, "7",
     "Professor, VCC", "1 in contractual position"),
    ("vcc", "Young Professional-II (Vety. Doctor)", 0, 0, "8",
     "Professor, VCC", "1 in contractual position"),
    ("vcc", "Computer Assistant", 1, 0, "9", "Professor, VCC",
     "1 in contractual position working in registration counter"),
    ("vcc", "Scientific Supervisor-II", 2, 2, "10", "Assistant Professor", "Nil"),
    ("vcc", "Scientific Assistant", 3, 0, "11", "Assistant Professor",
     "2 are in contractual position"),
    ("vcc", "Multitasking Staff-I (Grade-IV Sr.)", 2, 2, "12",
     "Assistant Professor", "Nil"),
    ("vcc", "Multitasking Staff-II (Grade-IV Jr.)", 2, 0, "13", "Assistant Professor",
     "14 numbers of contractual workers are working"),

    # ---- Lakhimpur College of Veterinary Science --------------------------
    ("lcvsc", "Associate Dean", 1, 0, "1", "Registrar, AVFU", ""),
    ("lcvsc", "Assistant Professor", 45, 0, "2", "Associate Dean, LCVSc",
     "All faculties (45 sanctioned across teaching cadre)"),
    ("lcvsc", "Assistant Section Officer", 1, 0, "2", "Associate Dean, LCVSc",
     "HQ: AAU, Jorhat"),
    ("lcvsc", "Senior Accountant", 1, 0, "3", "Associate Dean, LCVSc", ""),
    ("lcvsc", "Senior Administrative Assistant", 2, 0, "3",
     "Assistant Section Officer", ""),
    ("lcvsc", "Multitasking Staff-II (Grade-IV Jr.)", 1, 0, "4",
     "Assistant Section Officer", "Gr. IV"),

    # ---- Faculty of Fisheries Science, Raha -------------------------------
    ("ffsc", "Dean", 1, 0, "1", "Vice-Chancellor / Registrar", "Head of the institution"),
    ("ffsc", "Professor", 5, 0, "2", "HoD / Dean", "Faculties"),
    ("ffsc", "Associate Professor", 2, 0, "3", "HoD / Dean", "Faculties"),
    ("ffsc", "Assistant Professor", 20, 0, "4", "HoD / Dean", "Faculties"),
    ("ffsc", "Assistant Comptroller", 1, 0, "5", "Dean", "DDO"),
    ("ffsc", "Administrative Officer", 1, 0, "6", "Dean", "Establishment Section"),
    ("ffsc", "Farm Manager", 1, 0, "7", "Dean", "College Fish Farm"),
    ("ffsc", "Accounts Officer", 1, 0, "9", "Assistant Comptroller / Dean",
     "Accounts Section"),
    ("ffsc", "Section Officer", 1, 0, "10", "Administrative Officer / Dean",
     "Establishment Section"),
    ("ffsc", "Superintendent of Accounts", 1, 0, "11", "Assistant Comptroller / Dean",
     "Accounts Section"),
    ("ffsc", "Assistant Section Officer", 1, 0, "12", "Administrative Officer / Dean",
     "Establishment Section"),
    ("ffsc", "Senior Accountant", 2, 0, "13", "Accounts Officer / SoA / Dean",
     "Accounts Section"),
    ("ffsc", "Senior Administrative Assistant", 2, 0, "14",
     "Administrative Officer / ASO / Dean", "Establishment Section"),
    ("ffsc", "Junior Accountant", 3, 0, "15", "Assistant Comptroller / Dean",
     "Accounts Section"),
    ("ffsc", "Driver", 3, 0, "16", "Dean", "Establishment Section"),
    ("ffsc", "Dresser", 1, 0, "17", "Medical Officer / Dean", "Medical Unit"),
    ("ffsc", "Junior Library Assistant", 1, 0, "18", "Chief Librarian / Dean",
     "Library Section"),
    ("ffsc", "Multi-Tasking Staff (I & II)", 72, 0, "19", "Dean",
     "Establishment section"),

    # ---- Directorate of Research ------------------------------------------
    ("dor", "Director of Research", 1, 0, "1", "Vice Chancellor", ""),
    ("dor", "Deputy Director of Research", 1, 0, "2", "Director of Research", ""),
    ("dor", "Chief Scientist", 2, 0, "2", "Director of Research",
     "Chief Scientist / Professor"),
    ("dor", "Associate Professor", 1, 1, "2", "Director of Research", "Vacant"),
    ("dor", "Assistant Professor", 7, 5, "2", "Director of Research", "5 vacant"),
    ("dor", "Administrative Officer", 1, 1, "3", "DR / DDR", "Vacant"),
    ("dor", "Assistant Comptroller", 1, 1, "3", "DR / DDR", "Vacant"),
    ("dor", "Section Officer", 1, 1, "4", "Administrative Officer", "Vacant"),
    ("dor", "Superintendent of Accounts", 1, 1, "4", "Assistant Comptroller", "Vacant"),
    ("dor", "Senior Administrative Assistant", 1, 0, "5", "Section Officer", ""),
    ("dor", "Junior Administrative Assistant", 3, 2, "5", "Section Officer", "2 vacant"),
    ("dor", "Executive Assistant to Director", 1, 1, "5", "Director of Research",
     "Vacant"),
    ("dor", "Senior Accountant", 1, 0, "5", "Superintendent of Accounts",
     "3 in position"),
    ("dor", "Junior Accountant", 2, 0, "5", "Superintendent of Accounts", "Promoted"),
    ("dor", "Technical Supervisor-II", 2, 2, "5", "Section Officer", "Vacant"),
    ("dor", "Technical Assistant", 2, 1, "5", "Section Officer", "1 vacant"),
    ("dor", "Driver cum Mechanic", 2, 1, "5", "Director of Research", "1 vacant"),
    ("dor", "Computer Assistant", 1, 1, "5", "Section Officer", "Vacant"),
    ("dor", "Multitasking Staff-I (Grade-IV Sr.)", 2, 0, "6", "Section Officer", ""),
    ("dor", "Multitasking Staff-II (Grade-IV Jr.)", 4, 3, "6", "Section Officer",
     "3 vacant"),
    ("dor", "Sweeper", 1, 0, "6", "Section Officer", ""),

    # ---- Livestock Research Station, Mandira ------------------------------
    ("lrs_mandira", "Chief Scientist", 1, 0, "1", "Director of Research", ""),
    ("lrs_mandira", "Senior Scientist", 2, 0, "2/3", "Chief Scientist", ""),
    ("lrs_mandira", "Scientist", 7, 2, "4", "Chief Scientist", "2 vacant"),
    ("lrs_mandira", "Field Assistant-II (Technical Supervisor-II)", 1, 0, "5",
     "Chief Scientist", "FA II"),
    ("lrs_mandira", "Junior Accountant", 2, 2, "6", "Chief Scientist", "2 vacant"),
    ("lrs_mandira", "Junior Administrative Assistant", 1, 0, "7", "Chief Scientist", ""),
    ("lrs_mandira", "Veterinary Field Assistant", 5, 5, "8", "Chief Scientist", "5 vacant"),
    ("lrs_mandira", "Driver cum Mechanic", 1, 0, "9", "Chief Scientist", ""),
    ("lrs_mandira", "Section Assistant", 1, 1, "10", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Animal Attendant", 5, 4, "11", "Chief Scientist", "4 vacant"),
    ("lrs_mandira", "Milk Recorder", 1, 1, "12", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Typist", 1, 1, "13", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Messenger", 1, 1, "14", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Chowkidar", 3, 3, "15", "Chief Scientist", "3 vacant"),
    ("lrs_mandira", "Guest House Attendant", 1, 1, "16", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Milk Man", 1, 1, "17", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Cook Man", 1, 1, "18", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Electrician Helper", 1, 1, "19", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Tractor Driver", 1, 1, "20", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Tractor Helper", 1, 1, "21", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Store Keeper", 1, 1, "22", "Chief Scientist", "1 vacant"),
    ("lrs_mandira", "Laboratory Assistant", 1, 1, "23", "Chief Scientist", "1 vacant"),

    # ---- Goat Research Station, Burnihat ----------------------------------
    ("grs_burnihat", "Chief Scientist", 1, 0, "1", "Director of Research", ""),
    ("grs_burnihat", "Senior Scientist", 1, 0, "2", "Chief Scientist", ""),
    ("grs_burnihat", "Scientist", 3, 1, "3", "Chief Scientist", "1 vacant"),
    ("grs_burnihat", "Veterinary Technical/Scientific Assistant", 3, 2, "4", "Chief Scientist",
     "2 vacant and 1 working as Field Assistant-II"),
    ("grs_burnihat", "Junior Administrative Assistant", 1, 0, "5", "Chief Scientist", ""),
    ("grs_burnihat", "Driver cum Mechanic", 1, 1, "6", "Chief Scientist", "Vacant"),
    ("grs_burnihat", "Electrician", 1, 1, "7", "Chief Scientist", "Vacant"),
    ("grs_burnihat", "Plumber", 1, 1, "8", "Chief Scientist", "Vacant"),
    ("grs_burnihat", "Multitasking Staff-I (Grade-IV Sr.)", 6, 4, "9", "Chief Scientist",
     "4 vacant"),
    ("grs_burnihat", "Multitasking Staff-II (Grade-IV Jr.)", 2, 1, "10", "Chief Scientist",
     "1 vacant"),

    # ---- Directorate of Post Graduate Studies -----------------------------
    ("dpgs", "Director of Post Graduate Studies", 1, 0, "1", "Vice Chancellor", ""),
    ("dpgs", "In-charge Academic Cell (PG)", 1, 0, "2", "DPGS", ""),
    ("dpgs", "Senior Accountant", 1, 0, "3", "DPGS / Academic Cell (PG)", ""),
    ("dpgs", "Senior Administrative Assistant", 1, 0, "4",
     "DPGS / Academic Cell (PG)", ""),
    ("dpgs", "Computer Assistant", 1, 0, "5", "DPGS / Academic Cell (PG)", ""),
    ("dpgs", "Junior Accountant", 1, 0, "6", "DPGS / Academic Cell (PG)", ""),
    ("dpgs", "Junior Administrative Assistant", 2, 0, "7",
     "DPGS / Academic Cell (PG)", ""),
    ("dpgs", "Multitasking Staff-II (Grade-IV Jr.)", 2, 0, "8",
     "DPGS / Academic Cell (PG)", ""),
    ("dpgs", "Contractual Employee", 0, 0, "9", "DPGS / Academic Cell (PG)",
     "2 contractual employees engaged"),

    # ---- Directorate of Extension Education -------------------------------
    ("doee", "Director of Extension Education", 1, 0, "1", "Vice Chancellor", ""),
    ("doee", "Associate Director of Extension Education", 1, 0, "2", "DoEE", ""),
    ("doee", "Associate Professor", 2, 0, "3", "ADEE / DoEE", ""),
    ("doee", "Assistant Professor", 2, 0, "4", "ADEE / DoEE", ""),
    ("doee", "Administrative Officer", 1, 0, "5", "DoEE", ""),
    ("doee", "Assistant Comptroller", 1, 0, "6", "DoEE", ""),
    ("doee", "Senior Accountant", 1, 0, "7", "Assistant Comptroller / ADEE / DoEE", ""),
    ("doee", "Senior Administrative Assistant", 1, 0, "8", "AO / ADEE / DoEE", ""),
    ("doee", "Computer Assistant", 1, 0, "9",
     "SAA / Sr. Actt. / Asstt. Comptroller / AO / ADEE / DoEE", ""),
    ("doee", "Technical Supervisor-II", 1, 0, "10",
     "Asstt. Prof. / Assoc. Prof. / ADEE / DoEE", ""),
    ("doee", "Junior Accountant", 1, 0, "11", "Sr. Actt. / Asstt. Comptroller", ""),
    ("doee", "Junior Administrative Assistant", 2, 0, "12", "SAA / AO", ""),
    ("doee", "Technical Assistant", 1, 0, "13", "Technical Supervisor-II", ""),
    ("doee", "Driver cum Mechanic", 1, 0, "14", "Technical Supervisor-II", ""),
    ("doee", "Multi-Tasking Staff (I & II)", 6, 0, "15", "JAA", ""),
    ("doee", "Sweeper", 1, 0, "16", "Multitasking staff-I and II (MTS)", ""),

    # ---- Directorate of Physical Plant ------------------------------------
    # The submission left the sanctioned column blank and stated present
    # strength in Remarks; those figures are recorded here.
    ("dopp", "Director of Physical Plant", 1, 0, "2", "Registrar, AVFU",
     "Present strength: 1 Director"),
    ("dopp", "Executive Engineer", 1, 0, "3", "Director, DoPP",
     "Present strength: 1 EE"),
    ("dopp", "Assistant Engineer (Civil)", 3, 0, "4", "Executive Engineer, DoPP",
     "Present strength: 3 AE (C)"),
    ("dopp", "Assistant Engineer (Electrical)", 1, 0, "5", "Executive Engineer, DoPP",
     "Present strength: 1 AE (E)"),
    ("dopp", "Subordinate Engineer", 1, 0, "6", "Executive Engineer, DoPP",
     "Present strength: 1 Sub-Eng"),
    ("dopp", "Senior Accountant", 1, 0, "7", "Executive Engineer, DoPP",
     "Present strength: 1 Sr. Acctt"),
    ("dopp", "Senior Administrative Assistant", 1, 0, "8", "Executive Engineer, DoPP",
     "Present strength: 1 SAA"),
    ("dopp", "Junior Administrative Assistant", 1, 0, "9", "Executive Engineer, DoPP",
     "Present strength: 1 JAA"),
    ("dopp", "Plumber", 1, 0, "10", "Executive Engineer, DoPP",
     "Present strength: 1 Plumber"),
    ("dopp", "Plumber Helper", 1, 0, "11", "Executive Engineer, DoPP",
     "Present strength: 1 Plumber Helper"),
    ("dopp", "Muster Roll Worker", 16, 0, "12", "Executive Engineer, DoPP",
     "16 MR workers (water supply, electricity, carpenter, general worker)"),
    ("dopp", "Contractual Employee", 15, 0, "13", "Executive Engineer, DoPP",
     "15 contractual workers engaged in different official works"),

    # ---- Office of the Comptroller ----------------------------------------
    ("comptroller", "Financial Officer", 1, 0, "1", "Vice Chancellor", ""),
    ("comptroller", "Deputy Comptroller", 1, 0, "2", "Comptroller", ""),
    ("comptroller", "Assistant Comptroller", 1, 0, "3", "Deputy Comptroller", ""),
    ("comptroller", "Finance & Accounts Officer", 1, 0, "4", "Assistant Comptroller", ""),
    ("comptroller", "Superintendent of Accounts", 2, 0, "5",
     "Finance & Accounts Officer", ""),
    ("comptroller", "Senior Accountant", 3, 0, "6", "Superintendent of Accounts", ""),
    ("comptroller", "Junior Accountant", 7, 0, "7", "Superintendent of Accounts", ""),
    ("comptroller", "Junior Administrative Assistant", 1, 0, "8",
     "Superintendent of Accounts", ""),
    ("comptroller", "Computer Assistant", 2, 0, "9", "Superintendent of Accounts", ""),
    ("comptroller", "Multitasking Staff-I (Grade-IV Sr.)", 2, 0, "10",
     "Superintendent of Accounts", ""),
    ("comptroller", "Multitasking Staff-II (Grade-IV Jr.)", 2, 0, "11",
     "Superintendent of Accounts", ""),

    # ---- Office of the Librarian ------------------------------------------
    # Sanctioned strength follows the Rationalisation report; the 2007
    # Functional Study Committee figure is preserved in Remarks.
    ("library", "Librarian", 1, 0, "1", "Vice Chancellor, AVFU",
     "Post created by the AVFU Act"),
    ("library", "Deputy Librarian", 1, 0, "2", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Assistant Librarian", 1, 0, "3", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Documentation Officer", 0, 0, "4", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Senior Administrative Assistant", 2, 0, "5", "Librarian",
     "Functional Study Committee 2007: 0"),
    ("library", "Senior Accountant", 0, 0, "6", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Senior Technical Assistant", 0, 0, "7", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Junior Administrative Assistant", 3, 0, "8", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Junior Accountant", 1, 0, "9", "Librarian",
     "Additional charge held w.e.f. 13.07.2023"),
    ("library", "Classifier", 0, 0, "10", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Cataloguer", 0, 0, "11", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Technical Assistant", 0, 0, "12", "Librarian",
     "Functional Study Committee 2007: 2"),
    ("library", "Junior Library Assistant", 0, 0, "13", "Librarian",
     "Functional Study Committee 2007: 7"),
    ("library", "Computer Assistant", 2, 0, "14", "Librarian",
     "Functional Study Committee 2007: 0"),
    ("library", "Typist", 0, 0, "15", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Library Maintenance Assistant", 0, 0, "16", "Librarian",
     "Functional Study Committee 2007: 5"),
    ("library", "Multitasking Staff-I (Grade-IV Sr.)", 7, 0, "17", "Librarian",
     "Functional Study Committee 2007: 0"),
    ("library", "Multitasking Staff-II (Grade-IV Jr.)", 3, 0, "18", "Librarian",
     "Functional Study Committee 2007: 0"),
    ("library", "Xerox Operator", 0, 0, "19", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Gestetner Operator", 0, 0, "20", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Peon", 0, 0, "21", "Librarian",
     "Functional Study Committee 2007: 1"),
    ("library", "Sweeper", 1, 0, "22", "Librarian",
     "Functional Study Committee 2007: 0"),
]

# Sections/Units/Cells default to Establishment (administrative) even when
# they sit under a College — most are (Grievance Redressal, NSS, Transport,
# IQAC, ...). The one exception, keyed by (parent_key, name), is academic
# and category-overridden to Department below.
SECTION_CATEGORY_OVERRIDES = {
    ("lcvsc", "Veterinary Clinical Complex (LCVSc)"): "department",
}

# ---------------------------------------------------------------------------
# Sections / units / cells (Part C of every submission)
# ---------------------------------------------------------------------------
# (parent_key, name, org_type, officer_in_charge_name, employee_count)
SECTIONS = [
    # ---- Faculty of Veterinary Science ------------------------------------
    ("fvsc", "Academic Cell (UG)", "cell", "Dr. Jadav Sarma", 2),
    ("fvsc", "AKMIT Cell", "cell", "Dr. Shantanu Tamuly", 1),
    ("fvsc", "Transport Cell", "cell", "Dr. Raj Jyoti Deka", 1),
    ("fvsc", "Training & Placement Cell", "cell", "Dr. Devojyoti Dutta", 1),
    ("fvsc", "Central Instruments Facility", "unit", "Dr. Biswajit Dutta", 1),
    ("fvsc", "Estate Office", "section", "Dr. Anil Deka", 3),
    ("fvsc", "Security Cell", "cell", "Dr. Sadananda Payeng", 2),
    ("fvsc", "Health Centre", "unit", "Dr. Yogiraj Das", 1),

    # ---- Veterinary Clinical Complex --------------------------------------
    ("vcc", "Medicine", "unit", "Dr. Dwijen Kalita", 8),
    ("vcc", "Surgery", "unit", "Dr. Dwijen Kalita", 6),
    ("vcc", "Gynecology", "unit", "Dr. Dwijen Kalita", 3),
    ("vcc", "Laboratory", "unit", "Dr. Dwijen Kalita", 8),
    ("vcc", "Office Administration cum Accounts", "section", "Dr. Dwijen Kalita", 2),
    ("vcc", "Registration Counter", "unit", "Dr. Dwijen Kalita", 2),

    # ---- Lakhimpur College of Veterinary Science --------------------------
    ("lcvsc", "Academic Cell", "cell", "Dr. Himangshu Baruah", 0),
    ("lcvsc", "College Level Grievance Redressal Cell", "cell", "Dr. Pranjal Borah", 0),
    ("lcvsc", "Internal Committee for Prevention of Sexual Harassment of Women at Workplace",
     "cell", "Dr. Monjula Regon", 0),
    ("lcvsc", "Anti-Ragging Cell", "cell", "Dr. Himangshu Baruah", 0),
    ("lcvsc", "Training and Placement Cell", "cell", "Dr. Snigdha Hazarika", 0),
    ("lcvsc", "Security Cell", "cell", "Dr. Jitumoni Das", 0),
    ("lcvsc", "IQAC (Internal Quality Assurance Cell)", "cell", "Dr. Himangshu Baruah", 0),
    ("lcvsc", "Guest House", "unit", "Dr. Manoj Kumar Kalita", 0),
    ("lcvsc", "NSS Unit", "unit", "Dr. Aditya Baruah", 0),
    ("lcvsc", "Planning and Monitoring Unit", "unit", "Dr. Suraksha Subedi Deka", 0),
    ("lcvsc", "Vehicle and Transport Cell", "cell", "Dr. Prasanta Chabukdhara", 1),
    ("lcvsc", "Educational Technology Cell", "cell", "Dr. Gautam Bordoloi", 0),
    ("lcvsc", "IPR Cell", "cell", "Dr. Sanjib Borah", 0),
    ("lcvsc", "ARIS Cell", "cell", "Dr. L. Sanathoi Khuman", 0),
    ("lcvsc", "Library", "unit", "Dr. Priyanka Konwar", 1),
    ("lcvsc", "Women Cell", "cell", "Dr. Monjula Regon", 0),
    ("lcvsc", "Institute Level Nasha Mukti Co-ordinator", "cell", "Dr. AM Ferdoci", 0),
    ("lcvsc", "Estate Office", "section", "Dr. Arunoday Das", 0),
    ("lcvsc", "Technical Cell", "cell", "Dr. Donna Phangchopi", 0),
    ("lcvsc", "Computer Lab", "unit", "Dr. Donna Phangchopi", 0),
    ("lcvsc", "CIF", "unit", "Dr. Himangshu Baruah", 0),
    ("lcvsc", "Office of DDSW", "section", "Dr. Sanjib Khargharia", 0),
    ("lcvsc", "ILFC", "unit", "Dr. Sanjib Khargharia", 2),
    # Renamed to avoid confusion with the separate, real Veterinary Clinical
    # Complex Establishment under FVSc (own Part-B/Part-C submission). Both
    # are academic (Department category) per the client's own department list.
    ("lcvsc", "Veterinary Clinical Complex (LCVSc)", "unit", "Dr. Pranjal Borah", 1),
    ("lcvsc", "Auditorium", "unit", "Dr. Nayanjyoti Pathak", 0),

    # ---- Faculty of Fisheries Science, Raha -------------------------------
    ("ffsc", "Internal Quality Assurance Cell (IQAC)", "cell", "Dr. Pradip Ch. Bhuyan", 12),
    ("ffsc", "Board of Studies", "cell", "Dr. Pradip Ch. Bhuyan", 5),
    ("ffsc", "Accreditation Cell", "cell", "Dr. Sarada K. Bhagabati", 7),
    ("ffsc", "Institutional Development Plan (IDP) Committee", "cell",
     "Dr. Pradip Ch. Bhuyan", 7),
    ("ffsc", "Placement Cell", "cell", "Dr. M. P. Dutta", 1),
    ("ffsc", "Academic Cell (UG)", "cell", "Dr. A. N. Patowary", 1),
    ("ffsc", "Academic Cell (PG & Ph.D.)", "cell", "Dr. Bipul Kakoti", 1),
    ("ffsc", "Student Welfare", "section", "Dr. Rajdeep Dutta", 1),
    ("ffsc", "Director of Physical Plant (DPP) Section", "section",
     "Dr. Pradip Ch. Bhuyan", 1),
    ("ffsc", "Institutional Animal Ethics Committee (IAEC)", "cell",
     "Dr. Pradip Ch. Bhuyan", 4),
    ("ffsc", "Women's Cell", "cell", "Mrs. K. Mili", 5),
    ("ffsc", "Internal Committee (IC)", "cell", "Dr. Nazrin Sultana Ahmed", 7),
    ("ffsc", "Grievance Redressal Cell", "cell", "Dr. P. J. Sharma", 7),
    ("ffsc", "Anti-Ragging Committee", "cell", "Dr. Pradip Ch. Bhuyan", 13),
    ("ffsc", "Anti-Ragging Squad", "cell", "Dr. Dipak K. Sarma", 9),
    ("ffsc", "Library Unit", "unit", "Dr. Jiten Sharma", 2),
    ("ffsc", "Alumni Association of COF-Raha (AACOF-R)", "cell", "Dr. Rajdeep Dutta", 8),
    ("ffsc", "Hostel Management Committee", "cell", "Dr. Dipak K. Sarma", 4),
    ("ffsc", "Farm Management Committee", "cell", "Dr. Pradip Ch. Bhuyan", 5),
    ("ffsc", "College Level Travel Agency Selection Committee", "cell",
     "Dr. P. J. Sharma", 4),
    ("ffsc", "Faculty Level Screening Committee (FLSC)", "cell",
     "Dr. Pradip Ch. Bhuyan", 5),
    ("ffsc", "Price Fixation Committee (PFC)", "cell", "Dr. Dipak K. Sarma", 4),
    ("ffsc", "National Cadet Corps (NCC) Cell", "cell", "Dr. Rajdeep Dutta", 1),
    ("ffsc", "National Service Scheme (NSS) Unit", "unit", "Dr. Bipul Phukan", 1),
    ("ffsc", "Students Feedback Committee", "cell", "Dr. Pradip Ch. Bhuyan", 7),
    ("ffsc", "AAUTA (Teachers Association)", "cell", "Dr. Sarada K. Bhagabati", 7),
    ("ffsc", "Faculty Level Research Paper Evaluating and Monitoring Cell", "cell",
     "Dr. Sarifuddin Ahmed", 7),
    ("ffsc", "Faculty Level Project Monitoring Cell", "cell", "Dr. Dipak K. Sarma", 7),
    ("ffsc", "Faculty Level Revolving Fund Monitoring Cell", "cell",
     "Dr. P. J. Sharma", 5),
    ("ffsc", "Nasha Mukti Bharat Abhiyan (NMBA) — Residential Campus", "cell",
     "Dr. Dipak K. Sarma", 3),
    ("ffsc", "Nasha Mukti Bharat Abhiyan (NMBA) — Department Level", "cell",
     "Dr. Pradip Ch. Bhuyan", 10),
    ("ffsc", "Vehicle Unit", "unit", "Dr. Utpal K. Das", 1),
    ("ffsc", "Language Lab Unit", "unit", "Dr. Rinku Gogoi", 2),
    ("ffsc", "Medical Unit", "unit", "Dr. Akash Deka", 1),
    ("ffsc", "Establishment Section", "section", "Dr. Pradip Ch. Bhuyan", 10),
    ("ffsc", "Guest House Management Committee", "cell", "Dr. Pradip Ch. Bhuyan", 3),
    ("ffsc", "Accounts Section", "section", "Mr. Utpal Das", 1),

    # ---- Directorate of Research ------------------------------------------
    ("dor", "Administrative Section", "section", "Dr. Probodh Borah", 2),
    ("dor", "Account Section", "section", "Dr. Probodh Borah", 3),
    ("dor", "Technical Cell", "cell", "Dr. Probodh Borah", 4),

    # ---- Research stations -------------------------------------------------
    ("lrs_mandira", "Establishment", "section", "Dr. Dipankar Bharali", 1),
    ("lrs_mandira", "Accounts", "section", "Dr. Dipankar Bharali", 0),

    # ---- Directorate of Post Graduate Studies -----------------------------
    ("dpgs", "Academic Cell (PG)", "cell", "Dr. Rita Nath", 0),

    # ---- Directorate of Extension Education -------------------------------
    ("doee", "Administration", "section", "Dr. Hiranya Kr. Bhattacharyya", 6),
    ("doee", "Account", "section", "", 0),

    # ---- Office of the Comptroller ----------------------------------------
    ("comptroller", "Accounts", "section", "", 2),
    ("comptroller", "Establishment", "section", "", 1),

    # ---- Office of the Librarian ------------------------------------------
    ("library", "Administrative / Establishment", "section", "Dr. Pritam Mohan", 2),
    ("library", "Accounts", "section", "Dr. Pritam Mohan", 1),
    ("library", "Library Maintenance / Technical Section", "section",
     "Dr. Pritam Mohan", 1),
]

# ---------------------------------------------------------------------------
# Named individuals appearing in the submissions
# ---------------------------------------------------------------------------
# (full_name, designation, org_key, email, phone, is_head_of_office)
# Only names, designations, offices and contact details that appear in the
# client documents are recorded. Nothing personal is invented.
PEOPLE = []

REPORTING = []

SYSTEM_SETTINGS = [
    ("university.name", "Assam Veterinary and Fishery University",
     "Name shown across the HRMS"),
    ("university.short_name", "AVFU", "Short name / abbreviation"),
    ("hrms.employee_id_prefix", "AVFU", "Prefix for generated HRMS Employee IDs"),
    ("kyc.require_before_directory_listing", "false",
     "Require verified KYC before an employee appears in the directory"),
    ("password.min_length", "8", "Minimum password length"),
]


# ===========================================================================
# Derived org-unit structure (College -> Establishment | Department -> Section)
# ---------------------------------------------------------------------------
# Built from the lists above so the seed has one flat, ordered source.
# ===========================================================================

# The university itself — the one true root of the tree.
#   (key, name, short_code, location_key)
ORG_UNIVERSITY = [
    ("avfu_univ", "Assam Veterinary and Fishery University", "AVFU", "khanapara"),
]

# The three constituent colleges, each parented to the university.
#   (key, name, short_code, parent_key|None, location_key)
ORG_COLLEGES = [
    ("cvsc", "College of Veterinary Science, Khanapara", "CVSC", "avfu_univ", "khanapara"),
    ("cfsc", "College of Fishery Science, Raha", "CFSC", "avfu_univ", "raha"),
    ("lcvsc", "Lakhimpur College of Veterinary Science, Joyhing", "LCVSC", "avfu_univ", "joyhing"),
]

# Establishments (administrative offices). Parent is a college key, or the
# university itself for central offices that report straight to AVFU.
#   (key, name, short_code, college_key, location_key)
# college_key "avfu" attaches the central university offices (VC Office,
# Registrar, Comptroller, the Directorates, etc.) directly to the
# university node — they are not any one college's establishments.
_EST_COLLEGE = {"avfu": "avfu_univ", "fvsc": "cvsc", "ffsc": "cfsc", "lcvsc": "lcvsc"}
ORG_ESTABLISHMENTS = [
    (key, name, short, _EST_COLLEGE[ck], loc)
    for (ck, key, name, _sn, short, loc) in ESTABLISHMENTS_DATA
]

# Academic teaching departments. Parent is a college key.
#   (key, name, short_code, college_key)
def _dept_short(name: str) -> str:
    import re as _re
    core = _re.sub(r"^Department of\s+", "", name)
    core = _re.sub(r"[^A-Za-z0-9 ]+", "", core)
    words = [w for w in core.split() if w.lower() not in {"of", "and", "the", "&"}]
    return ("".join(w[:4] for w in words[:2]) or core[:8]).upper()[:12]

_DEPT_COLLEGE = {"fvsc": "cvsc", "ffsc": "cfsc", "lcvsc": "lcvsc"}
ORG_DEPARTMENTS = [
    (
        f"dept_{_DEPT_COLLEGE[ck]}_{i}",
        name,
        _dept_short(name),
        _DEPT_COLLEGE[ck],
    )
    for i, (ck, name) in enumerate(ACADEMIC_DEPARTMENTS)
]
# name -> key, so POSTS/SECTIONS that reference a college key can be ignored
# and demo data can target a department by (college, name) if needed.

# Sections / units / cells. Parent is an establishment key (or a college key,
# which the seed resolves to that college's Dean office when one exists).
#   (key, name, sub_kind, parent_key, officer_name, headcount_note)
ORG_SECTIONS = [
    (f"sec_{i}", name, sub_kind, parent_key, officer or "", str(headcount) if headcount else "")
    for i, (parent_key, name, sub_kind, officer, headcount) in enumerate(SECTIONS)
]

# Part B sanctioned posts, keyed by establishment/college key.
#   (parent_key, designation_name, level_no, sanctioned, reported_vacant, reports_to_note, remarks)
def _level_no(raw) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return 0

ORG_POSTS = [
    (parent_key, desig, _level_no(level), sanctioned, vacant, note, remarks)
    for (parent_key, desig, sanctioned, vacant, level, note, remarks) in POSTS
]

# When a POSTS/SECTIONS row targets a college key rather than an establishment,
# attach it to that college's Dean office.
COLLEGE_KEY_TO_DEAN_EST = {
    "fvsc": "dean_cvsc",
    "ffsc": "dean_cfsc",
    "lcvsc": "adean_lcvsc",
}
