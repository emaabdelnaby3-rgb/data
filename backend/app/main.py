from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from .auth import create_access_token, hash_password, require_role, verify_password
from .database import engine, get_session, init_db
from .models import BeneficiaryProfile, Case, Donation, Organization, PaymentMethod, Priority, Role, User
from .schemas import CreateCaseRequest, DonateRequest, DonorRegisterRequest, LoginRequest, TokenResponse
from .services import generate_case_code, generate_receipt_code, split_donation

app = FastAPI(title="المنصة الحكومية الموحدة للجمعيات")

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def save_file(uploaded_file: UploadFile, folder_name: str) -> str:
    folder = UPLOADS_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    extension = Path(uploaded_file.filename).suffix
    filename = f"{folder_name}_{generate_receipt_code()}{extension}"
    file_path = folder / filename
    with file_path.open("wb") as f:
        f.write(uploaded_file.file.read())
    return f"/uploads/{folder_name}/{filename}"


@app.on_event("startup")
def startup_event():
    init_db()
    with Session(engine) as session:
        if not session.exec(select(Organization)).first():
            orgs = [
                Organization(name="جمعية الرحمة"),
                Organization(name="جمعية الأمل"),
                Organization(name="جمعية التكافل"),
            ]
            session.add_all(orgs)
            session.commit()

        if not session.exec(select(User).where(User.role == Role.ADMIN)).first():
            session.add(
                User(
                    full_name="مدير المنصة",
                    email="admin@charity.gov.eg",
                    national_id="29901010101010",
                    hashed_password=hash_password("Admin@12345"),
                    role=Role.ADMIN,
                    organization_id=1,
                )
            )
            session.commit()

        if not session.exec(select(User).where(User.role == Role.BENEFICIARY)).first():
            ben = User(
                full_name="أب لثلاثة أطفال",
                email=None,
                national_id="30002020202020",
                hashed_password=hash_password("Beneficiary@123"),
                role=Role.BENEFICIARY,
                organization_id=1,
            )
            session.add(ben)
            session.commit()
            session.refresh(ben)
            session.add(
                BeneficiaryProfile(
                    user_id=ben.id,
                    age=43,
                    children_count=3,
                    monthly_income=1500,
                    is_married=True,
                    has_job=False,
                    salary=0,
                    medical_condition="طفل يعاني من مرض مزمن ويحتاج متابعة شهرية",
                    id_card_file="/uploads/seed/id_card.png",
                    birth_certificates_file="/uploads/seed/births.pdf",
                    approved=True,
                )
            )
            session.add(
                Case(
                    case_code=generate_case_code(),
                    title="علاج شهري لطفل مريض",
                    description="أسرة مكونة من 5 أفراد تحتاج 4000 جنيه شهريًا لتغطية علاج الطفل.",
                    priority=Priority.URGENT,
                    requested_amount=4000,
                    funded_amount=0,
                    organization_id=1,
                    beneficiary_id=ben.id,
                )
            )
            session.add(
                Case(
                    case_code=generate_case_code(),
                    title="إيجار وسلة غذائية",
                    description="حالة إنسانية تحتاج دعم أساسي للإيجار والطعام.",
                    priority=Priority.HIGH,
                    requested_amount=3000,
                    funded_amount=1000,
                    organization_id=2,
                    beneficiary_id=ben.id,
                )
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


@app.post("/api/auth/register-donor", response_model=TokenResponse)
def register_donor(payload: DonorRegisterRequest, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.email == payload.email)).first():
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مستخدم بالفعل")
    if session.exec(select(User).where(User.national_id == payload.national_id)).first():
        raise HTTPException(status_code=400, detail="الرقم القومي موجود بالفعل")

    donor = User(
        full_name=payload.full_name,
        email=payload.email,
        national_id=payload.national_id,
        hashed_password=hash_password(payload.password),
        role=Role.DONOR,
        phone=payload.phone,
    )
    session.add(donor)
    session.commit()
    session.refresh(donor)
    token = create_access_token(str(donor.id))
    return TokenResponse(access_token=token)


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(
        select(User).where((User.national_id == payload.identifier) | (User.email == payload.identifier))
    ).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@app.get("/api/organizations")
def list_organizations(session: Session = Depends(get_session)):
    return session.exec(select(Organization)).all()


@app.post("/api/beneficiaries/register")
def register_beneficiary_profile(
    age: int = Form(...),
    children_count: int = Form(...),
    monthly_income: float = Form(...),
    is_married: bool = Form(...),
    has_job: bool = Form(...),
    salary: float = Form(...),
    medical_condition: str = Form(""),
    id_card_file: UploadFile = File(...),
    birth_certificates_file: UploadFile = File(...),
    extra_documents_file: Optional[UploadFile] = File(None),
    user: User = Depends(require_role(Role.BENEFICIARY)),
    session: Session = Depends(get_session),
):
    existing = session.exec(select(BeneficiaryProfile).where(BeneficiaryProfile.user_id == user.id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="تم تسجيل بيانات المحتاج سابقًا")

    id_card_path = save_file(id_card_file, str(user.id))
    births_path = save_file(birth_certificates_file, str(user.id))
    extra_path = save_file(extra_documents_file, str(user.id)) if extra_documents_file else None

    profile = BeneficiaryProfile(
        user_id=user.id,
        age=age,
        children_count=children_count,
        monthly_income=monthly_income,
        is_married=is_married,
        has_job=has_job,
        salary=salary,
        medical_condition=medical_condition,
        id_card_file=id_card_path,
        birth_certificates_file=births_path,
        extra_documents_file=extra_path,
    )
    session.add(profile)
    session.commit()
    return {"message": "تم استلام بياناتك ومستنداتك بنجاح"}


@app.post("/api/cases")
def create_case(
    payload: CreateCaseRequest,
    admin: User = Depends(require_role(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    beneficiary = session.get(User, payload.beneficiary_id)
    if not beneficiary or beneficiary.role != Role.BENEFICIARY:
        raise HTTPException(status_code=404, detail="المحتاج غير موجود")

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
def list_cases(
    organization_id: Optional[int] = Query(default=None),
    priority: Optional[Priority] = Query(default=None),
    session: Session = Depends(get_session),
):
    query = select(Case).where(Case.is_active == True)
    if organization_id:
        query = query.where(Case.organization_id == organization_id)
    if priority:
        query = query.where(Case.priority == priority)
    cases = session.exec(query).all()

    return [
        {
            **case.model_dump(),
            "remaining_amount": round(case.requested_amount - case.funded_amount, 2),
            "progress_percent": round((case.funded_amount / case.requested_amount) * 100, 1) if case.requested_amount else 0,
        }
        for case in cases
    ]


@app.post("/api/cases/{case_id}/donate")
def donate_to_case(
    case_id: int,
    payload: DonateRequest,
    donor: User = Depends(require_role(Role.DONOR)),
    session: Session = Depends(get_session),
):
    case = session.get(Case, case_id)
    if not case or not case.is_active:
        raise HTTPException(status_code=404, detail="الحالة غير موجودة")

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
        payment_method=payload.payment_method,
        receipt_code=generate_receipt_code(),
    )
    session.add(donation)
    session.add(case)
    session.commit()
    return {
        "message": "تم تنفيذ التبرع بنجاح",
        "beneficiary_share": beneficiary_share,
        "organization_share": organization_share,
        "receipt_code": donation.receipt_code,
    }


@app.post("/api/donate/direct")
def donate_direct(
    organization_id: int,
    payload: DonateRequest,
    donor: User = Depends(require_role(Role.DONOR)),
    session: Session = Depends(get_session),
):
    if not session.get(Organization, organization_id):
        raise HTTPException(status_code=404, detail="الجمعية غير موجودة")

    donation = Donation(
        donor_id=donor.id,
        case_id=None,
        organization_id=organization_id,
        amount=payload.amount,
        beneficiary_share=0,
        organization_share=payload.amount,
        payment_method=payload.payment_method,
        receipt_code=generate_receipt_code(),
    )
    session.add(donation)
    session.commit()
    return {"message": "تم التبرع المباشر بنجاح", "receipt_code": donation.receipt_code}


@app.get("/api/admin/dashboard")
def admin_dashboard(
    user: User = Depends(require_role(Role.ADMIN)),
    session: Session = Depends(get_session),
):
    total_donations = session.exec(select(func.sum(Donation.amount))).one() or 0
    donors_count = session.exec(select(func.count()).select_from(User).where(User.role == Role.DONOR)).one() or 0
    beneficiaries_count = session.exec(select(func.count()).select_from(User).where(User.role == Role.BENEFICIARY)).one() or 0
    open_cases_count = session.exec(select(func.count()).select_from(Case).where(Case.is_active == True)).one() or 0

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
        "open_cases_count": open_cases_count,
        "donations_by_org": [{"organization": o, "amount": float(a or 0)} for o, a in donations_by_org],
    }
