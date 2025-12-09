"""Mock data generator for jobs and candidates."""

import json
import random
import uuid
from pathlib import Path
from enum import Enum

from src.models.job import Job, ExperienceLevel, LocationType
from src.models.candidate import Candidate


class PayType(str, Enum):
    """Pay frequency type."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class DataGenerator:
    """Generate mock job vacancies and candidate profiles."""
    
    # Job data pools
    COMPANIES = [
        "TechCorp", "InnovateTech", "DataDynamics", "CloudNine Systems",
        "QuantumLeap Inc", "NexGen Solutions", "CyberSecure Ltd", "AIVentures",
        "BlockchainBase", "FinTech Global", "HealthTech Solutions", "EduTech Inc",
        "GreenEnergy Systems", "SmartCity Labs", "RoboTech Industries",
        "VirtualReality Co", "IoT Innovations", "BigData Corp", "MLOps Inc",
        "DevOps Masters", "AgileWorks", "CloudFirst", "SecureNet",
        "DataLake Systems", "StreamTech"
    ]
    
    JOB_TITLES = {
        "engineering": [
            "Software Engineer", "Senior Software Engineer", "Staff Engineer",
            "Backend Developer", "Frontend Developer", "Full Stack Developer",
            "DevOps Engineer", "Site Reliability Engineer", "Platform Engineer",
            "Data Engineer", "ML Engineer", "AI Engineer", "Cloud Architect",
            "Solutions Architect", "Technical Lead", "Engineering Manager"
        ],
        "data": [
            "Data Scientist", "Senior Data Scientist", "Data Analyst",
            "Business Intelligence Analyst", "Analytics Engineer",
            "Machine Learning Scientist", "Research Scientist"
        ],
        "product": [
            "Product Manager", "Senior Product Manager", "Technical Product Manager",
            "Product Owner", "Program Manager"
        ],
        "design": [
            "UX Designer", "UI Designer", "Product Designer", "UX Researcher"
        ],
        "security": [
            "Security Engineer", "Security Analyst", "Penetration Tester",
            "Security Architect"
        ]
    }
    
    SKILLS_BY_DOMAIN = {
        "backend": ["Python", "Java", "Go", "Node.js", "PostgreSQL", "MongoDB", 
                    "Redis", "Kafka", "RabbitMQ", "Docker", "Kubernetes", "AWS",
                    "GCP", "Azure", "REST APIs", "GraphQL", "Microservices"],
        "frontend": ["JavaScript", "TypeScript", "React", "Vue.js", "Angular",
                     "HTML5", "CSS3", "Tailwind CSS", "Next.js", "Webpack"],
        "data": ["Python", "SQL", "Spark", "Hadoop", "Airflow", "dbt",
                 "Snowflake", "BigQuery", "Redshift", "Tableau", "Power BI"],
        "ml": ["Python", "TensorFlow", "PyTorch", "Scikit-learn", "MLflow",
               "Kubeflow", "Feature Engineering", "NLP", "Computer Vision"],
        "devops": ["Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins",
                   "GitHub Actions", "ArgoCD", "Prometheus", "Grafana"],
        "security": ["Network Security", "Penetration Testing", "SIEM",
                     "Incident Response", "Compliance", "IAM"]
    }
    
    INDUSTRIES = [
        "Technology", "Finance", "Healthcare", "E-commerce", "Education",
        "Energy", "Manufacturing", "Media", "Telecommunications", "Transportation"
    ]
    
    DEPARTMENTS = [
        "Engineering", "Data Science", "Product", "Security", "Infrastructure",
        "Platform", "Research", "Analytics"
    ]
    
    LOCATIONS = [
        "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
        "Boston, MA", "Chicago, IL", "Denver, CO", "Los Angeles, CA",
        "Miami, FL", "Atlanta, GA", "Portland, OR", "San Diego, CA"
    ]
    
    BENEFITS = [
        "Health Insurance", "Dental Insurance", "Vision Insurance",
        "401(k) Matching", "Stock Options", "Unlimited PTO",
        "Remote Work", "Flexible Hours", "Learning Budget",
        "Gym Membership", "Parental Leave", "Mental Health Support",
        "Home Office Stipend", "Commuter Benefits", "Free Meals"
    ]
    
    # Blue-collar companies
    BLUECOLLAR_COMPANIES = [
        "QuickDeliver Logistics", "Metro Warehouse Co", "CleanPro Services",
        "HandyFix Solutions", "SecureGuard Security", "FastFreight Transport",
        "CityMove Movers", "BuildRight Construction", "FreshClean Janitorial",
        "SafeHaul Trucking", "UrbanCourier Express", "PacknShip Fulfillment",
        "AllStar Maintenance", "SwiftDrive Delivery", "ProClean Commercial",
        "LoadMaster Warehouse", "TrustGuard Services", "RapidHaul Transport",
        "HomeFix Repairs", "PrimeLogistics Inc", "CargoKing Shipping",
        "SpotlessClean Co", "ReliableMovers", "ConstructAll Builders"
    ]
    
    # Blue-collar job titles
    BLUECOLLAR_TITLES = {
        "delivery": [
            "Delivery Driver", "Courier", "Package Handler", "Route Driver",
            "Van Driver", "Local Delivery Driver", "Express Courier"
        ],
        "warehouse": [
            "Warehouse Associate", "Forklift Operator", "Picker Packer",
            "Inventory Clerk", "Shipping Associate", "Receiving Clerk",
            "Warehouse Loader", "Stock Clerk", "Order Fulfillment Associate"
        ],
        "cleaning": [
            "Janitor", "Cleaner", "Housekeeper", "Custodian",
            "Commercial Cleaner", "Office Cleaner", "Industrial Cleaner"
        ],
        "maintenance": [
            "Handyman", "Maintenance Worker", "Building Maintenance",
            "Facilities Technician", "General Maintenance", "Repair Technician"
        ],
        "security": [
            "Security Guard", "Security Officer", "Night Watchman",
            "Patrol Officer", "Site Security", "Event Security"
        ],
        "moving": [
            "Mover", "Moving Helper", "Furniture Mover", "Load Specialist",
            "Relocation Assistant"
        ],
        "construction": [
            "Construction Worker", "Laborer", "Construction Helper",
            "Site Worker", "General Laborer", "Construction Assistant"
        ]
    }
    
    # Blue-collar requirements/skills
    BLUECOLLAR_REQUIREMENTS = {
        "licenses": [
            "Valid Driver's License", "CDL Class A", "CDL Class B",
            "Forklift Certification", "OSHA Safety Certification"
        ],
        "physical": [
            "Able to lift 25kg/55lbs", "Able to lift 50kg/110lbs",
            "Able to stand for 8+ hours", "Able to walk long distances",
            "Good physical condition", "Able to work outdoors"
        ],
        "age": [
            "Minimum age 18", "Minimum age 21", "Minimum age 25"
        ],
        "other": [
            "Height above 170cm/5'7\"", "Height above 180cm/5'11\"",
            "Clean background check", "Own transportation",
            "Available for night shifts", "Available for weekends",
            "Flexible schedule", "Reliable and punctual",
            "Basic English proficiency", "Team player",
            "Customer service skills", "Attention to detail"
        ]
    }
    
    # Blue-collar pay rates by job type
    BLUECOLLAR_PAY = {
        "delivery": {"hourly": (15, 25), "daily": (120, 200), "weekly": (600, 1000)},
        "warehouse": {"hourly": (14, 22), "daily": (110, 180), "weekly": (550, 900)},
        "cleaning": {"hourly": (12, 20), "daily": (100, 160), "weekly": (500, 800)},
        "maintenance": {"hourly": (16, 28), "daily": (130, 220), "weekly": (650, 1100)},
        "security": {"hourly": (14, 24), "daily": (110, 190), "weekly": (550, 950)},
        "moving": {"hourly": (15, 26), "daily": (120, 210), "weekly": (600, 1050)},
        "construction": {"hourly": (16, 30), "daily": (130, 240), "weekly": (650, 1200)}
    }
    
    BLUECOLLAR_INDUSTRIES = [
        "Logistics", "Warehousing", "Retail", "Hospitality", "Construction",
        "Cleaning Services", "Security Services", "Moving Services", 
        "Food Service", "Property Management"
    ]
    
    BLUECOLLAR_BENEFITS = [
        "Weekly Pay", "Daily Pay", "Health Insurance", "Overtime Available",
        "Flexible Hours", "Uniform Provided", "Training Provided",
        "Growth Opportunities", "Paid Breaks", "Transportation Allowance",
        "Meal Allowance", "Safety Equipment Provided"
    ]

    # Candidate data pools
    FIRST_NAMES = [
        "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie",
        "Quinn", "Avery", "Cameron", "Blake", "Drew", "Sage", "Parker"
    ]
    
    BLUECOLLAR_FIRST_NAMES = [
        "Mike", "Joe", "Dave", "Steve", "Tom", "Chris", "John", "Mark",
        "Dan", "Bob", "Jim", "Rick", "Tony", "Frank", "Eddie", "Sam",
        "Maria", "Rosa", "Ana", "Carmen", "Elena", "Sofia", "Linda", "Susan"
    ]
    
    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
        "Miller", "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor",
        "Thomas", "Moore", "Jackson", "Martin", "Lee", "Perez", "Chen", "Patel"
    ]
    
    CANDIDATE_SUMMARIES = [
        "Passionate software engineer with {years} years of experience building scalable systems.",
        "Results-driven developer specializing in {domain} with a track record of delivering high-impact projects.",
        "Innovative technologist with {years} years in {domain}, focused on solving complex problems.",
        "Experienced {domain} professional with strong background in agile methodologies.",
        "Detail-oriented engineer with {years} years of experience in building production systems.",
        "Creative problem solver with expertise in {domain} and modern software practices.",
        "Dedicated professional with {years} years of hands-on experience in {domain}.",
        "Tech enthusiast with deep expertise in {domain} and cloud technologies.",
    ]
    
    BLUECOLLAR_SUMMARIES = [
        "Reliable worker with {years} years of experience in {domain}. Always punctual and hardworking.",
        "Dedicated {domain} professional looking for steady work. Strong work ethic.",
        "Experienced in {domain} with {years} years on the job. Available immediately.",
        "Hardworking individual with {years} years in {domain}. Team player.",
        "Dependable worker seeking {domain} position. {years} years experience.",
        "Looking for stable employment in {domain}. {years} years of hands-on experience.",
        "Physical job experience with {years} years in {domain}. Ready to start.",
        "Motivated worker with background in {domain}. {years} years experience. Flexible schedule.",
    ]
    
    def __init__(self, seed: int = 42):
        """Initialize generator with optional seed for reproducibility."""
        random.seed(seed)
        
    def generate_job(self, job_id: str | None = None) -> Job:
        """Generate a single mock job vacancy."""
        department = random.choice(self.DEPARTMENTS)
        
        # Map department to title category
        title_category = {
            "Engineering": "engineering",
            "Data Science": "data",
            "Product": "product",
            "Security": "security",
            "Infrastructure": "engineering",
            "Platform": "engineering",
            "Research": "data",
            "Analytics": "data"
        }.get(department, "engineering")
        
        title = random.choice(self.JOB_TITLES.get(title_category, self.JOB_TITLES["engineering"]))
        
        # Determine experience level from title
        if any(word in title.lower() for word in ["senior", "staff", "lead", "manager", "architect"]):
            exp_level = random.choice([ExperienceLevel.SENIOR, ExperienceLevel.LEAD])
            min_years = random.randint(5, 10)
        elif "principal" in title.lower():
            exp_level = ExperienceLevel.PRINCIPAL
            min_years = random.randint(10, 15)
        else:
            exp_level = random.choice([ExperienceLevel.JUNIOR, ExperienceLevel.MID])
            min_years = random.randint(0, 4)
        
        # Select skills based on department/title
        skill_domain = {
            "Engineering": random.choice(["backend", "frontend", "devops"]),
            "Data Science": random.choice(["data", "ml"]),
            "Security": "security",
            "Infrastructure": "devops",
            "Platform": "devops",
        }.get(department, "backend")
        
        all_skills = self.SKILLS_BY_DOMAIN.get(skill_domain, self.SKILLS_BY_DOMAIN["backend"])
        required_skills = random.sample(all_skills, min(5, len(all_skills)))
        preferred_skills = random.sample(
            [s for s in all_skills if s not in required_skills],
            min(3, len(all_skills) - len(required_skills))
        )
        
        # Generate salary based on experience level
        salary_base = {
            ExperienceLevel.JUNIOR: (70000, 100000),
            ExperienceLevel.MID: (100000, 140000),
            ExperienceLevel.SENIOR: (140000, 180000),
            ExperienceLevel.LEAD: (170000, 220000),
            ExperienceLevel.PRINCIPAL: (200000, 280000),
        }[exp_level]
        
        salary_min = random.randint(salary_base[0], salary_base[0] + 20000)
        salary_max = random.randint(salary_min + 20000, max(salary_min + 40000, salary_base[1]))
        
        location_type = random.choice(list(LocationType))
        location = random.choice(self.LOCATIONS) if location_type != LocationType.REMOTE else None
        
        company = random.choice(self.COMPANIES)
        industry = random.choice(self.INDUSTRIES)
        
        description = self._generate_job_description(
            title, company, department, required_skills, exp_level
        )
        
        return Job(
            id=job_id or f"job-{uuid.uuid4().hex[:8]}",
            title=title,
            company=company,
            description=description,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            experience_level=exp_level,
            min_years_experience=min_years,
            location_type=location_type,
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            industry=industry,
            department=department,
            benefits=random.sample(self.BENEFITS, random.randint(4, 8))
        )
    
    def _generate_job_description(
        self, title: str, company: str, department: str,
        skills: list[str], exp_level: ExperienceLevel
    ) -> str:
        """Generate a realistic job description."""
        skills_text = ", ".join(skills[:3])
        
        descriptions = [
            f"We are seeking a talented {title} to join our {department} team at {company}. "
            f"You will work on challenging projects using {skills_text} and collaborate with "
            f"cross-functional teams to deliver innovative solutions.",
            
            f"{company} is looking for a {exp_level.value}-level {title} to help build "
            f"the next generation of our products. Experience with {skills_text} is essential. "
            f"You'll have the opportunity to make a significant impact on our technical direction.",
            
            f"Join {company}'s growing {department} team as a {title}. We're building "
            f"cutting-edge solutions and need someone skilled in {skills_text}. "
            f"This is a great opportunity to work with talented engineers and grow your career.",
            
            f"As a {title} at {company}, you'll be responsible for designing and implementing "
            f"scalable systems using {skills_text}. We value innovation, collaboration, "
            f"and continuous learning.",
        ]
        
        return random.choice(descriptions)
    
    def generate_candidate(self, candidate_id: str | None = None) -> Candidate:
        """Generate a single mock candidate profile."""
        first_name = random.choice(self.FIRST_NAMES)
        last_name = random.choice(self.LAST_NAMES)
        name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}@email.com"
        
        years_exp = random.randint(1, 15)
        
        # Select a primary domain for the candidate
        domain = random.choice(["backend", "frontend", "data", "ml", "devops"])
        domain_label = {
            "backend": "backend development",
            "frontend": "frontend development",
            "data": "data engineering",
            "ml": "machine learning",
            "devops": "DevOps and infrastructure"
        }[domain]
        
        # Generate skills from primary domain plus some cross-domain skills
        primary_skills = random.sample(
            self.SKILLS_BY_DOMAIN[domain],
            min(5, len(self.SKILLS_BY_DOMAIN[domain]))
        )
        other_domain = random.choice([d for d in self.SKILLS_BY_DOMAIN.keys() if d != domain])
        cross_skills = random.sample(
            self.SKILLS_BY_DOMAIN[other_domain],
            min(2, len(self.SKILLS_BY_DOMAIN[other_domain]))
        )
        skills = primary_skills + cross_skills
        
        # Generate summary
        summary_template = random.choice(self.CANDIDATE_SUMMARIES)
        summary = summary_template.format(years=years_exp, domain=domain_label)
        
        # Current title based on experience
        title_category = {
            "backend": "engineering",
            "frontend": "engineering",
            "data": "data",
            "ml": "data",
            "devops": "engineering"
        }[domain]
        
        possible_titles = self.JOB_TITLES[title_category]
        if years_exp < 3:
            current_title = random.choice([t for t in possible_titles if "Senior" not in t and "Lead" not in t])
        elif years_exp < 7:
            current_title = random.choice([t for t in possible_titles if "Senior" in t or "Engineer" in t])
        else:
            current_title = random.choice(possible_titles)
        
        # Preferences
        preferred_titles = random.sample(possible_titles, min(3, len(possible_titles)))
        preferred_location_types = random.sample(list(LocationType), random.randint(1, 3))
        preferred_locations = random.sample(self.LOCATIONS, random.randint(1, 3)) if LocationType.ONSITE in preferred_location_types or LocationType.HYBRID in preferred_location_types else []
        
        # Salary expectations based on experience
        base_salary = 70000 + (years_exp * 10000)
        min_salary = base_salary + random.randint(-10000, 10000)
        max_salary = min_salary + random.randint(30000, 60000)
        
        preferred_industries = random.sample(self.INDUSTRIES, random.randint(1, 4))
        
        return Candidate(
            id=candidate_id or f"candidate-{uuid.uuid4().hex[:8]}",
            name=name,
            email=email,
            summary=summary,
            skills=skills,
            years_experience=years_exp,
            current_title=current_title,
            preferred_titles=preferred_titles,
            preferred_location_types=preferred_location_types,
            preferred_locations=preferred_locations,
            min_salary=min_salary,
            max_salary=max_salary,
            preferred_industries=preferred_industries,
            declined_job_ids=[],
            accepted_job_id=None
        )
    
    def generate_bluecollar_job(self, job_id: str | None = None) -> Job:
        """Generate a single blue-collar job vacancy."""
        job_category = random.choice(list(self.BLUECOLLAR_TITLES.keys()))
        title = random.choice(self.BLUECOLLAR_TITLES[job_category])
        company = random.choice(self.BLUECOLLAR_COMPANIES)
        industry = random.choice(self.BLUECOLLAR_INDUSTRIES)
        
        # Generate requirements
        requirements = []
        
        # Add license requirement for driving jobs
        if job_category in ["delivery", "moving"]:
            requirements.append(random.choice(self.BLUECOLLAR_REQUIREMENTS["licenses"][:2]))
        elif job_category == "warehouse":
            if random.random() > 0.5:
                requirements.append("Forklift Certification")
        
        # Add physical requirements
        requirements.extend(random.sample(self.BLUECOLLAR_REQUIREMENTS["physical"], random.randint(1, 2)))
        
        # Add age requirement
        if job_category in ["delivery", "security"]:
            requirements.append(random.choice(self.BLUECOLLAR_REQUIREMENTS["age"]))
        
        # Add other requirements
        requirements.extend(random.sample(self.BLUECOLLAR_REQUIREMENTS["other"], random.randint(2, 4)))
        
        # Choose pay type
        pay_type = random.choice([PayType.HOURLY, PayType.DAILY, PayType.WEEKLY])
        pay_range = self.BLUECOLLAR_PAY[job_category][pay_type.value]
        pay_min = random.randint(pay_range[0], pay_range[0] + 3)
        pay_max = random.randint(pay_min + 2, pay_range[1])
        
        # Convert to annual equivalent for consistency with Job model
        annual_multiplier = {
            PayType.HOURLY: 2080,  # 40 hrs/week * 52 weeks
            PayType.DAILY: 260,    # 5 days/week * 52 weeks
            PayType.WEEKLY: 52,
        }
        salary_min = pay_min * annual_multiplier[pay_type]
        salary_max = pay_max * annual_multiplier[pay_type]
        
        # Location
        location_type = random.choice([LocationType.ONSITE, LocationType.HYBRID])
        location = random.choice(self.LOCATIONS)
        
        # Description with pay info
        pay_text = {
            PayType.HOURLY: f"${pay_min}-${pay_max}/hour",
            PayType.DAILY: f"${pay_min}-${pay_max}/day",
            PayType.WEEKLY: f"${pay_min}-${pay_max}/week",
        }[pay_type]
        
        description = self._generate_bluecollar_description(
            title, company, requirements, pay_text, pay_type
        )
        
        return Job(
            id=job_id or f"job-{uuid.uuid4().hex[:8]}",
            title=title,
            company=company,
            description=description,
            required_skills=requirements,
            preferred_skills=[],
            experience_level=ExperienceLevel.JUNIOR,
            min_years_experience=0,
            location_type=location_type,
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            industry=industry,
            department=job_category.title(),
            benefits=random.sample(self.BLUECOLLAR_BENEFITS, random.randint(3, 6))
        )
    
    def _generate_bluecollar_description(
        self, title: str, company: str, requirements: list[str],
        pay_text: str, pay_type: PayType
    ) -> str:
        """Generate a blue-collar job description."""
        req_text = ", ".join(requirements[:3])
        
        descriptions = [
            f"{company} is hiring {title}s! Pay: {pay_text} ({pay_type.value}). "
            f"Requirements: {req_text}. Immediate start available. Apply now!",
            
            f"Looking for reliable {title} to join {company}. "
            f"Earn {pay_text} ({pay_type.value} pay). Must have: {req_text}. "
            f"No experience needed - we train!",
            
            f"JOIN OUR TEAM as a {title} at {company}! "
            f"Competitive pay: {pay_text}. Requirements: {req_text}. "
            f"Full-time and part-time positions available.",
            
            f"{title} needed at {company}. Pay: {pay_text} ({pay_type.value}). "
            f"We're looking for: {req_text}. Great team environment!",
            
            f"NOW HIRING: {title} for {company}. "
            f"Starting at {pay_text}. Requirements: {req_text}. "
            f"Stable work with growth opportunities.",
        ]
        
        return random.choice(descriptions)
    
    def generate_bluecollar_candidate(self, candidate_id: str | None = None) -> Candidate:
        """Generate a blue-collar candidate profile."""
        first_name = random.choice(self.BLUECOLLAR_FIRST_NAMES)
        last_name = random.choice(self.LAST_NAMES)
        name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}@email.com"
        
        years_exp = random.randint(0, 10)
        
        # Select job category preference
        job_category = random.choice(list(self.BLUECOLLAR_TITLES.keys()))
        domain_label = {
            "delivery": "delivery and driving",
            "warehouse": "warehouse operations",
            "cleaning": "cleaning and janitorial",
            "maintenance": "maintenance and repairs",
            "security": "security work",
            "moving": "moving and logistics",
            "construction": "construction and labor"
        }[job_category]
        
        # Generate qualifications/skills
        skills = []
        
        # Add relevant licenses
        if job_category in ["delivery", "moving"]:
            skills.append("Valid Driver's License")
            if random.random() > 0.7:
                skills.append(random.choice(["CDL Class A", "CDL Class B"]))
        elif job_category == "warehouse" and random.random() > 0.5:
            skills.append("Forklift Certification")
        
        # Add physical abilities
        skills.extend(random.sample([
            "Able to lift 25kg/55lbs",
            "Able to lift 50kg/110lbs", 
            "Good physical condition",
            "Able to stand for 8+ hours"
        ], random.randint(1, 2)))
        
        # Add soft skills
        skills.extend(random.sample([
            "Punctual and reliable",
            "Team player",
            "Customer service skills",
            "Flexible schedule",
            "Available weekends",
            "Night shift available",
            "Own transportation"
        ], random.randint(2, 4)))
        
        # Generate summary
        summary_template = random.choice(self.BLUECOLLAR_SUMMARIES)
        summary = summary_template.format(years=years_exp, domain=domain_label)
        
        # Current and preferred titles
        current_title = random.choice(self.BLUECOLLAR_TITLES[job_category])
        preferred_titles = []
        for cat in random.sample(list(self.BLUECOLLAR_TITLES.keys()), random.randint(2, 4)):
            preferred_titles.extend(random.sample(self.BLUECOLLAR_TITLES[cat], 1))
        
        # Salary expectations (hourly equivalent converted to annual)
        hourly_rate = random.randint(14, 25)
        min_salary = hourly_rate * 2080  # Annual equivalent
        max_salary = (hourly_rate + random.randint(5, 10)) * 2080
        
        preferred_industries = random.sample(self.BLUECOLLAR_INDUSTRIES, random.randint(2, 4))
        
        return Candidate(
            id=candidate_id or f"candidate-{uuid.uuid4().hex[:8]}",
            name=name,
            email=email,
            summary=summary,
            skills=skills,
            years_experience=years_exp,
            current_title=current_title,
            preferred_titles=preferred_titles,
            preferred_location_types=[LocationType.ONSITE, LocationType.HYBRID],
            preferred_locations=random.sample(self.LOCATIONS, random.randint(1, 3)),
            min_salary=min_salary,
            max_salary=max_salary,
            preferred_industries=preferred_industries,
            declined_job_ids=[],
            accepted_job_id=None
        )

    def generate_jobs(self, count: int = 100) -> list[Job]:
        """Generate multiple job vacancies."""
        return [self.generate_job(f"job-{i:03d}") for i in range(1, count + 1)]
    
    def generate_bluecollar_jobs(self, count: int = 200) -> list[Job]:
        """Generate multiple blue-collar job vacancies."""
        return [self.generate_bluecollar_job(f"job-bc-{i:03d}") for i in range(1, count + 1)]
    
    def generate_candidates(self, count: int = 10) -> list[Candidate]:
        """Generate multiple candidate profiles."""
        return [self.generate_candidate(f"candidate-{i:03d}") for i in range(1, count + 1)]
    
    def generate_bluecollar_candidates(self, count: int = 20) -> list[Candidate]:
        """Generate multiple blue-collar candidate profiles."""
        return [self.generate_bluecollar_candidate(f"candidate-bc-{i:03d}") for i in range(1, count + 1)]
    
    def save_jobs(self, jobs: list[Job], filepath: Path) -> None:
        """Save jobs to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump([job.model_dump() for job in jobs], f, indent=2)
    
    def save_candidates(self, candidates: list[Candidate], filepath: Path) -> None:
        """Save candidates to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump([c.model_dump() for c in candidates], f, indent=2)
    
    def load_jobs(self, filepath: Path) -> list[Job]:
        """Load jobs from JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return [Job(**job) for job in data]
    
    def load_candidates(self, filepath: Path) -> list[Candidate]:
        """Load candidates from JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return [Candidate(**c) for c in data]

