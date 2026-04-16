from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from .auth import create_access_token, get_current_user, hash_password, require_role, verify_password
from .database import engine, get_session, init_db
from .models import BeneficiaryProfile, Case, Donation, Organization, Role, User
from .schemas import (
    BeneficiaryRegistrationRequest,
    CreateCaseRequest,
    DonateRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from .services import generate_case_code, split_donation

app = FastAPI(title="Unified Charity Platform")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def startup_event():
    init_db()
    with Session(engine) as session:
        if not session.exec(select(Organization)).first():
            session.add_all(
                [
                    Organization(name="جمعية الرحمة"),
                    Organization(name="جمعية الأمل"),
                    Organization(name="جمعية التكافل"),
                ]
            )
            session.commit()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/beneficiary", response_class=HTMLResponse)
def beneficiary_page(request: Request):
    return templates.TemplateResponse("beneficiary.html", {"request": request})


@app.get("/donor", response_class=HTMLResponse)
def donor_page(request: Request):
    return templates.TemplateResponse("donor.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.post("/api/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.email == payload.email)).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    if payload.national_id and session.exec(select(User).where(User.national_id == payload.national_id)).first():
        raise HTTPException(status_code=400, detail="National ID already exists in unified system")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        organization_id=payload.organization_id,
        national_id=payload.national_id,
        phone=payload.phone,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@app.get("/api/organizations")
def list_organizations(session: Session = Depends(get_session)):
    return session.exec(select(Organization)).all()


@app.post("/api/beneficiaries/register")
def register_beneficiary(
    payload: BeneficiaryRegistrationRequest,
    user: User = Depends(require_role(Role.BENEFICIARY)),
    session: Session = Depends(get_session),
):
    existing = session.exec(select(BeneficiaryProfile).where(BeneficiaryProfile.user_id == user.id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Beneficiary profile already exists")
    profile = BeneficiaryProfile(user_id=user.id, **payload.model_dump())
    session.add(profile)
    session.commit()
    return {"message": "Registration received for review"}


@app.post("/api/cases")
def create_case(
    payload: CreateCaseRequest,
    admin: User = Depends(require_role(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    beneficiary = session.get(User, payload.beneficiary_id)
    if not beneficiary or beneficiary.role != Role.BENEFICIARY:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    new_case = Case(
        case_code=generate_case_code(),
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        requested_amount=payload.requested_amount,
        organization_id=admin.organization_id or 1,
        beneficiary_id=payload.beneficiary_id,
    )
    session.add(new_case)
    session.commit()
    session.refresh(new_case)
    return new_case


@app.get("/api/cases")
def list_cases(session: Session = Depends(get_session)):
    return session.exec(select(Case).where(Case.is_active == True)).all()


@app.post("/api/cases/{case_id}/donate")
def donate_to_case(
    case_id: int,
    payload: DonateRequest,
    donor: User = Depends(require_role(Role.DONOR)),
    session: Session = Depends(get_session),
):
    case = session.get(Case, case_id)
    if not case or not case.is_active:
        raise HTTPException(status_code=404, detail="Case not found")

    needed = case.requested_amount - case.funded_amount
    beneficiary_share, organization_share = split_donation(payload.amount, needed)
    case.funded_amount += beneficiary_share
    if case.funded_amount >= case.requested_amount:
        case.is_active = False

    donation = Donation(
        donor_id=donor.id,
        case_id=case.id,
        organization_id=case.organization_id,
        amount=payload.amount,
        beneficiary_share=beneficiary_share,
        organization_share=organization_share,
    )
    session.add(donation)
    session.add(case)
    session.commit()
    return {
        "message": "Donation processed",
        "beneficiary_share": beneficiary_share,
        "organization_share": organization_share,
    }


@app.post("/api/donate/direct")
def donate_direct(
    organization_id: int,
    payload: DonateRequest,
    donor: User = Depends(require_role(Role.DONOR)),
    session: Session = Depends(get_session),
):
    if not session.get(Organization, organization_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    donation = Donation(
        donor_id=donor.id,
        case_id=None,
        organization_id=organization_id,
        amount=payload.amount,
        beneficiary_share=0,
        organization_share=payload.amount,
    )
    session.add(donation)
    session.commit()
    return {"message": "Direct donation received"}


@app.get("/api/admin/dashboard")
def admin_dashboard(
    user: User = Depends(require_role(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    total_donations = session.exec(select(func.sum(Donation.amount))).one() or 0
    donors_count = session.exec(select(func.count()).select_from(User).where(User.role == Role.DONOR)).one() or 0
    beneficiaries_count = session.exec(select(func.count()).select_from(User).where(User.role == Role.BENEFICIARY)).one() or 0

    donations_by_org = session.exec(
        select(Organization.name, func.sum(Donation.amount))
        .join(Donation, Donation.organization_id == Organization.id)
        .group_by(Organization.name)
    ).all()

    return {
        "admin_id": user.id,
        "total_donations": round(float(total_donations), 2),
        "donors_count": donors_count,
        "beneficiaries_count": beneficiaries_count,
        "donations_by_org": [{"organization": o, "amount": float(a or 0)} for o, a in donations_by_org],
    }
