"""
knowledge_base.py
-----------------
Static knowledge used by the AI engine: canonical skill taxonomy,
education rank map, section header synonyms, job roles, departments,
and fields of study used during parsing and matching.
Keeping this centralized makes the "expert system" rules auditable
and easy to extend without touching parsing/matching logic.
"""

# Canonical skill taxonomy grouped by category.
# Extend this dictionary to widen the system's vocabulary.
SKILL_TAXONOMY = {
    "Programming Languages": [
        "python", "java", "c++", "c#", "javascript", "typescript", "go", "golang",
        "rust", "r", "matlab", "scala", "kotlin", "swift", "php", "ruby", "c",
        "perl", "dart", "julia", "solidity", "lua",
    ],
    "Web Development": [
        "html", "css", "react", "reactjs", "angular", "vue", "vuejs", "node.js",
        "nodejs", "express", "django", "flask", "fastapi", "next.js", "nextjs",
        "bootstrap", "tailwind", "jquery", "rest api", "graphql", "webpack",
        "sass", "less", "redux", "typescript",
    ],
    "Data Science & ML": [
        "machine learning", "deep learning", "nlp", "natural language processing",
        "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn",
        "sklearn", "pandas", "numpy", "matplotlib", "seaborn", "opencv",
        "data analysis", "data science", "statistics", "regression",
        "classification", "clustering", "neural networks", "xgboost",
        "reinforcement learning", "generative ai", "llm", "transformers",
        "artificial intelligence", "data mining", "big data", "tableau",
    ],
    "Databases": [
        "sql", "mysql", "postgresql", "postgres", "mongodb", "sqlite", "oracle",
        "redis", "cassandra", "dynamodb", "nosql", "elasticsearch", "firebase",
        "mariadb", "couchdb", "neo4j",
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "jenkins",
        "ci/cd", "terraform", "ansible", "linux", "git", "github", "gitlab",
        "devops", "microservices", "cloud computing", "bitbucket",
        "kubernetes", "prometheus", "grafana",
    ],
    "Tools & Platforms": [
        "excel", "power bi", "tableau", "jira", "figma", "postman", "vs code",
        "spark", "hadoop", "airflow", "kafka", "unity", "android studio",
        "xcode", "intellij", "eclipse", "vim", "docker", "jenkins",
    ],
    "Soft & Domain Skills": [
        "project management", "agile", "scrum", "communication", "leadership",
        "problem solving", "teamwork", "business analysis", "product management",
        "ui/ux", "ui design", "ux design", "critical thinking", "time management",
        "adaptability", "creativity", "collaboration", "decision making",
        "presentation", "negotiation", "conflict resolution",
    ],
}

# Flat lookup set for fast membership testing.
ALL_SKILLS = sorted({s for group in SKILL_TAXONOMY.values() for s in group})

# Common aliases mapped to a canonical skill name.
SKILL_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "nodejs": "node.js",
    "node": "node.js",
    "ml": "machine learning",
    "dl": "deep learning",
    "cv": "computer vision",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "gcp": "google cloud",
    "sklearn": "scikit-learn",
    "py": "python",
    "power-bi": "power bi",
    "nextjs": "next.js",
    "next.js": "next.js",
    "ai": "artificial intelligence",
    "generative ai": "generative ai",
    "gen ai": "generative ai",
}

# Education level ranking used for education-match scoring.
EDUCATION_RANK = {
    "phd": 5,
    "ph.d": 5,
    "doctorate": 5,
    "master": 4,
    "masters": 4,
    "master's degree": 4,
    "m.tech": 4,
    "mtech": 4,
    "mba": 4,
    "msc": 4,
    "m.sc": 4,
    "m.s": 4,
    "m.a": 4,
    "postgraduate": 4,
    "post-graduate": 4,
    "bachelor": 3,
    "bachelors": 3,
    "bachelor's degree": 3,
    "b.tech": 3,
    "btech": 3,
    "b.e": 3,
    "be": 3,
    "bsc": 3,
    "b.sc": 3,
    "b.s": 3,
    "b.a": 3,
    "bca": 3,
    "undergraduate": 3,
    "graduate": 3,
    "diploma": 2,
    "associate": 2,
    "high school": 1,
    "high school diploma": 1,
    "hsc": 1,
    "ssc": 1,
}

DEGREE_KEYWORDS = list(EDUCATION_RANK.keys())

# Fields of study / specializations / branches
FIELDS_OF_STUDY = [
    "computer science", "computer engineering", "information technology",
    "software engineering", "electronics", "electrical engineering",
    "mechanical engineering", "civil engineering", "chemical engineering",
    "data science", "mathematics", "physics", "statistics",
    "business administration", "finance", "accounting", "marketing",
    "human resources", "artificial intelligence", "machine learning",
    "cyber security", "network engineering", "telecommunications",
    "biotechnology", "bioinformatics", "environmental engineering",
    "industrial engineering", "aerospace engineering", "automobile engineering",
    "instrumentation", "robotics", "automation",
]

# Common job roles / titles
JOB_ROLES = [
    "software engineer", "senior software engineer", "software developer",
    "full stack developer", "frontend developer", "backend developer",
    "devops engineer", "data scientist", "data analyst", "data engineer",
    "machine learning engineer", "ai engineer", "python developer",
    "java developer", "web developer", "mobile developer",
    "product manager", "project manager", "business analyst",
    "system analyst", "quality analyst", "qa engineer", "test engineer",
    "network engineer", "system administrator", "cloud engineer",
    "security analyst", "cyber security analyst",
    "database administrator", "dba",
    "technical lead", "tech lead", "team lead",
    "architect", "solution architect",
    "hr manager", "recruiter", "talent acquisition",
    "marketing manager", "digital marketing",
    "sales manager", "account manager",
    "finance manager", "accountant",
]

# Departments
DEPARTMENTS = [
    "information technology", "it", "engineering", "r&d", "research and development",
    "product", "design", "marketing", "sales", "finance", "accounting",
    "human resources", "hr", "operations", "administration",
    "customer support", "quality assurance", "qa",
    "data science", "machine learning", "analytics",
    "cyber security", "network", "infrastructure",
    "management", "executive", "consulting",
]

# Department hierarchy — maps sub-departments / related departments
# to their broader parent department. This enables smart matching
# so e.g. "IT" → "Engineering", "Data Science" → "Engineering", etc.
DEPARTMENT_HIERARCHY = {
    # Engineering & Technology
    "engineering": "engineering",
    "software engineering": "engineering",
    "it": "engineering",
    "information technology": "engineering",
    "data science": "engineering",
    "machine learning": "engineering",
    "analytics": "engineering",
    "cyber security": "engineering",
    "network": "engineering",
    "infrastructure": "engineering",
    "cloud": "engineering",
    "devops": "engineering",
    "quality assurance": "engineering",
    "qa": "engineering",
    "r&d": "engineering",
    "research and development": "engineering",
    "product development": "engineering",
    "software development": "engineering",
    "web development": "engineering",
    "mobile development": "engineering",
    
    # Product & Design
    "product": "product",
    "product management": "product",
    "design": "design",
    "ui/ux": "design",
    "ux": "design",
    "ui design": "design",
    
    # Marketing
    "marketing": "marketing",
    "digital marketing": "marketing",
    "content": "marketing",
    "brand": "marketing",
    "communications": "marketing",
    
    # Sales
    "sales": "sales",
    "business development": "sales",
    "account management": "sales",
    
    # Finance & Accounting
    "finance": "finance",
    "accounting": "finance",
    "audit": "finance",
    
    # Human Resources
    "human resources": "human resources",
    "hr": "human resources",
    "talent acquisition": "human resources",
    "recruiting": "human resources",
    
    # Operations
    "operations": "operations",
    "administration": "operations",
    "customer support": "operations",
    "logistics": "operations",
    "supply chain": "operations",
    
    # Legal & Compliance
    "legal": "legal",
    "compliance": "legal",
}

DEPARTMENT_PARENTS = {
    "engineering": "Engineering & Technology",
    "product": "Product & Design",
    "design": "Product & Design",
    "marketing": "Marketing & Communications",
    "sales": "Sales & Business Development",
    "finance": "Finance & Accounting",
    "human resources": "Human Resources",
    "operations": "Operations & Administration",
    "legal": "Legal & Compliance",
}

def get_parent_department(dept: str) -> str:
    """
    Given a department name, return its normalized parent department.
    If not found in hierarchy, returns the original input.
    This enables:
      - 'IT' → 'engineering'
      - 'Data Science' → 'engineering'
      - 'Talent Acquisition' → 'human resources'
      - 'Engineering' → 'engineering'
    """
    if not dept:
        return dept
    dept_lower = dept.strip().lower()
    if dept_lower in DEPARTMENT_HIERARCHY:
        return DEPARTMENT_HIERARCHY[dept_lower]
    # Try partial match
    for key, parent in DEPARTMENT_HIERARCHY.items():
        if key in dept_lower or dept_lower in key:
            return parent
    return dept_lower


def departments_match(job_dept: str, candidate_dept: str) -> bool:
    """
    Smart department matching using hierarchy.
    Returns True if both departments belong to the same parent category.
    
    Examples:
      departments_match("Engineering", "IT") → True
      departments_match("Engineering", "Data Science") → True
      departments_match("Marketing", "Engineering") → False
      departments_match("HR", "Talent Acquisition") → True
    """
    if not job_dept or not candidate_dept:
        return True  # If either is empty, consider it matched (no constraint)
    
    job_parent = get_parent_department(job_dept)
    candidate_parent = get_parent_department(candidate_dept)
    
    # Direct match
    if job_parent == candidate_parent:
        return True
    
    # If candidate's department is "Not Found", it's a mismatch
    if candidate_dept == "not found":
        return False
    
    return False

SECTION_HEADERS = {
    "experience": ["experience", "work experience", "professional experience",
                   "employment history", "work history", "career history"],
    "education": ["education", "academic background", "academic qualification",
                  "qualifications", "educational background"],
    "skills": ["skills", "technical skills", "core competencies", "key skills",
               "skill set", "expertise", "competencies"],
    "projects": ["projects", "academic projects", "personal projects",
                 "key projects", "professional projects"],
    "certifications": ["certifications", "certificates", "licenses",
                        "certifications & training", "credentials"],
    "summary": ["summary", "professional summary", "objective", "career objective",
                 "profile summary", "about me"],
}

# Common Indian cities for location extraction (extensible)
INDIAN_CITIES = sorted({
    "ahmedabad", "surat", "vadodara", "rajkot", "bhavnagar", "jamnagar",
    "mumbai", "pune", "nagpur", "thane", "navi mumbai", "nasik", "aurangabad",
    "delhi", "new delhi", "gurgaon", "gurugram", "noida", "ghaziabad", "faridabad",
    "bangalore", "bengaluru", "mysore", "hubli", "mangalore",
    "hyderabad", "secunderabad",
    "chennai", "coimbatore", "madurai", "trichy", "salem",
    "kolkata", "howrah", "durgapur", "asansol", "siliguri",
    "jaipur", "jodhpur", "udaipur", "kota", "ajmer",
    "lucknow", "kanpur", "agra", "varanasi", "allahabad", "prayagraj",
    "chandigarh", "mohali", "panchkula",
    "bhopal", "indore", "gwalior", "jabalpur", "ujjain",
    "patna", "gaya", "muzaffarpur",
    "guwahati", "shillong",
    "bhubaneswar", "cuttack", "rourkela",
    "kochi", "kochin", "thiruvananthapuram", "trivandrum", "kozhikode", "calicut",
    "dehradun", "rishikesh", "haridwar",
    "raipur", "bilaspur",
    "ranchi", "jamshedpur",
    "shimla", "manali",
    "srinagar", "jammu",
    "panaji", "goa",
    "gangtok", "itanagar", "imphal", "aizawl", "kohima", "dimapur", "agartala",
    "pondicherry", "port blair", "daman", "diu", "silvassa",
    # International cities
    "new york", "san francisco", "los angeles", "chicago", "seattle", "boston",
    "london", "manchester", "birmingham",
    "toronto", "vancouver", "montreal",
    "sydney", "melbourne", "brisbane", "perth",
    "dubai", "abu dhabi",
    "singapore",
    "berlin", "munich", "hamburg", "frankfurt",
    "paris", "lyon",
    "tokyo", "osaka", "kyoto",
    "shanghai", "beijing", "shenzhen",
    "amsterdam", "rotterdam",
    "zurich", "geneva",
    "stockholm", "oslo", "copenhagen", "helsinki",
    "dublin", "brussels", "vienna",
    "milan", "rome",
    "madrid", "barcelona",
    "lisbon", "warsaw", "prague", "budapest",
})

# Mandatory requirement fields for strict ATS matching
MANDATORY_FIELDS = ["skills", "experience", "education", "location", "role", "department"]
OPTIONAL_FIELDS = ["certifications", "projects", "additional_skills", "languages"]

# Technical skills (subset of ALL_SKILLS that are technical)
TECHNICAL_SKILLS = sorted({
    # Programming Languages
    "python", "java", "c++", "c#", "javascript", "typescript", "go", "golang",
    "rust", "r", "matlab", "scala", "kotlin", "swift", "php", "ruby", "c",
    "perl", "dart", "julia", "solidity", "lua",
    # Web Development
    "html", "css", "react", "reactjs", "angular", "vue", "vuejs", "node.js",
    "nodejs", "express", "django", "flask", "fastapi", "next.js", "nextjs",
    "bootstrap", "tailwind", "jquery", "rest api", "graphql", "webpack",
    "sass", "less", "redux",
    # Data Science & ML
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn",
    "sklearn", "pandas", "numpy", "matplotlib", "seaborn", "opencv",
    "data analysis", "data science", "statistics", "regression",
    "classification", "clustering", "neural networks", "xgboost",
    "reinforcement learning", "generative ai", "llm", "transformers",
    "artificial intelligence", "data mining", "big data", "tableau",
    # Databases
    "sql", "mysql", "postgresql", "postgres", "mongodb", "sqlite", "oracle",
    "redis", "cassandra", "dynamodb", "nosql", "elasticsearch", "firebase",
    "mariadb", "couchdb", "neo4j",
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "jenkins",
    "ci/cd", "terraform", "ansible", "linux", "git", "github", "gitlab",
    "devops", "microservices", "cloud computing", "bitbucket",
    "prometheus", "grafana",
    # Tools & Platforms
    "excel", "power bi", "tableau", "jira", "figma", "postman", "vs code",
    "spark", "hadoop", "airflow", "kafka", "unity", "android studio",
    "xcode", "intellij", "eclipse", "vim",
})

# Soft skills
SOFT_SKILLS = sorted({
    "project management", "agile", "scrum", "communication", "leadership",
    "problem solving", "teamwork", "business analysis", "product management",
    "ui/ux", "ui design", "ux design", "critical thinking", "time management",
    "adaptability", "creativity", "collaboration", "decision making",
    "presentation", "negotiation", "conflict resolution",
    "analytical", "organizational", "interpersonal", "multitasking",
    "attention to detail", "self-motivated", "fast learner", "mentoring",
    "strategic planning", "customer service", "public speaking",
    "writing", "research", "problem-solving", "team player",
})
