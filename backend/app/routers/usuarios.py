from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Rol, Usuario
from ..schemas import UsuarioIn, UsuarioOut, UsuarioUpdate
from ..security import hash_password, requiere_roles

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])
solo_admin = requiere_roles(Rol.ADMINISTRADOR)


@router.get("", response_model=list[UsuarioOut], dependencies=[Depends(solo_admin)])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.scalars(select(Usuario).order_by(Usuario.id)).all()


@router.post(
    "",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(solo_admin)],
)
def crear_usuario(payload: UsuarioIn, db: Session = Depends(get_db)):
    existe = db.scalar(select(Usuario).where(Usuario.usuario == payload.usuario))
    if existe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El usuario ya existe")

    usuario = Usuario(
        nombre=payload.nombre,
        usuario=payload.usuario,
        contrasena_hash=hash_password(payload.contrasena),
        rol=payload.rol,
        area=payload.area,
        activo=payload.activo,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put(
    "/{usuario_id}", response_model=UsuarioOut, dependencies=[Depends(solo_admin)]
)
def actualizar_usuario(
    usuario_id: int, payload: UsuarioUpdate, db: Session = Depends(get_db)
):
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    datos = payload.model_dump(exclude_unset=True)
    contrasena = datos.pop("contrasena", None)
    rol_final = datos.get("rol", usuario.rol)
    area_final = datos.get("area", usuario.area)
    if rol_final == Rol.ENCARGADO_AREA and area_final is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Un encargado de área requiere un área",
        )
    if rol_final != Rol.ENCARGADO_AREA:
        datos["area"] = None
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)
    if contrasena:
        usuario.contrasena_hash = hash_password(contrasena)

    db.commit()
    db.refresh(usuario)
    return usuario
