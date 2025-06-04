from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.schemas import UserSignup, UserOut, UserLogin, Token
from app.db.deps import get_db
from app.crud import user as crud_user
from app.utils.utils import verify_password, create_access_token

router = APIRouter()

@router.post("/signup", response_model=UserOut)
def create_user(user: UserSignup, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud_user.create_user(db=db, user_data=user)

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    access_token = create_access_token(data={"sub": db_user.id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": db_user.id,
        "name": db_user.name,
        "email": db_user.email
    }

