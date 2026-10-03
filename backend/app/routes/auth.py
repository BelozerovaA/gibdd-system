from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import create_access_token, verify_password
from ..database import get_db
from ..models import Employee
from ..schemas import LoginRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Вход сотрудника по логину и паролю, в ответ выдаётся JWT-токен."""
    user = db.query(Employee).filter(
        Employee.login == request.login,
        Employee.is_active == True  # noqa: E712
    ).first()

    if not user or not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "login": user.login}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        full_name=user.full_name,
        position=user.position or "Сотрудник",
        email=user.email
    )
