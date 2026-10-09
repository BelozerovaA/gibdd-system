from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Camera, Employee
from ..schemas import CameraResponse

router = APIRouter()


@router.get("/", response_model=List[CameraResponse])
def get_cameras(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Camera).all()


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(
    camera_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Камера не найдена")
    return camera
