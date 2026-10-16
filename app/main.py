from contextlib import asynccontextmanager
from datetime import date
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from . import models, schemas
from .database import Base, engine, get_db
from .security import current_user, hash_password, make_token, verify_password


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Job Application Tracker", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", response_model=schemas.Token, status_code=201)
def register(body: schemas.Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(models.User).where(models.User.email == body.email)):
        raise HTTPException(409, "Email already registered")
    user = models.User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return schemas.Token(access_token=make_token(user.id))


@app.post("/auth/login", response_model=schemas.Token)
def login(body: schemas.Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == body.email))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return schemas.Token(access_token=make_token(user.id))


def _own(db: Session, user: models.User, app_id: int) -> models.Application:
    obj = db.get(models.Application, app_id)
    if not obj or obj.user_id != user.id:
        raise HTTPException(404, "Application not found")
    return obj


@app.post("/applications", response_model=schemas.ApplicationOut, status_code=201)
def create_application(body: schemas.ApplicationIn, db: Session = Depends(get_db),
                       user: models.User = Depends(current_user)):
    obj = models.Application(user_id=user.id, **body.model_dump())
    obj.events.append(models.StatusEvent(status=obj.status))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/applications", response_model=list[schemas.ApplicationOut])
def list_applications(status: schemas.Status | None = None,
                      q: str | None = Query(None, description="search company or role"),
                      limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                      db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    A = models.Application
    stmt = select(A).where(A.user_id == user.id)
    if status:
        stmt = stmt.where(A.status == status)
    if q:
        stmt = stmt.where(A.company.ilike(f"%{q}%") | A.role.ilike(f"%{q}%"))
    return db.scalars(stmt.order_by(A.created_at.desc()).limit(limit).offset(offset)).all()


@app.get("/applications/{app_id}", response_model=schemas.ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db),
                    user: models.User = Depends(current_user)):
    return _own(db, user, app_id)


@app.patch("/applications/{app_id}", response_model=schemas.ApplicationOut)
def update_application(app_id: int, body: schemas.ApplicationUpdate,
                       db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    obj = _own(db, user, app_id)
    changes = body.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] != obj.status:
        obj.events.append(models.StatusEvent(status=changes["status"]))
    for k, v in changes.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/applications/{app_id}", status_code=204)
def delete_application(app_id: int, db: Session = Depends(get_db),
                       user: models.User = Depends(current_user)):
    db.delete(_own(db, user, app_id))
    db.commit()


@app.get("/analytics/summary")
def summary(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    A = models.Application
    rows = db.execute(select(A.status, func.count()).where(A.user_id == user.id)
                      .group_by(A.status)).all()
    by_status = {s: 0 for s in models.STATUSES} | dict(rows)
    total = sum(by_status.values())
    due = db.scalar(select(func.count()).where(
        A.user_id == user.id, A.follow_up_date <= date.today(),
        A.status.in_(["applied", "screening"])))
    return {"total": total, "by_status": by_status,
            "response_rate": round((total - by_status["applied"]) / total, 3) if total else 0.0,
            "follow_ups_due": due or 0}
