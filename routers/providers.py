from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from database import get_db
from schemas.schemas import ProveedorCrear, ProveedorEditar

router = APIRouter(prefix="/api/proveedores", tags=["Proveedores"])

@router.post("/", response_model=dict)
def crear_proveedor(p: ProveedorCrear):
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO proveedores (nombre, contacto) VALUES (?, ?)",
            (p.nombre, p.contacto)
        )
        return {"id": cursor.lastrowid, "nombre": p.nombre}

@router.get("/", response_model=List[dict])
def listar_proveedores(activo: Optional[int] = 1):
    with get_db() as conn:
        res = conn.execute(
            "SELECT * FROM proveedores WHERE activo = ? ORDER BY nombre ASC",
            (activo,)
        ).fetchall()
        return [dict(r) for r in res]

@router.get("/{prov_id}", response_model=dict)
def obtener_proveedor(prov_id: int):
    with get_db() as conn:
        res = conn.execute("SELECT * FROM proveedores WHERE id = ?", (prov_id,)).fetchone()
        if not res:
            raise HTTPException(404, "Proveedor no encontrado")
        return dict(res)

@router.patch("/{prov_id}")
def editar_proveedor(prov_id: int, p: ProveedorEditar):
    with get_db() as conn:
        prov = conn.execute("SELECT * FROM proveedores WHERE id = ?", (prov_id,)).fetchone()
        if not prov:
            raise HTTPException(404, "Proveedor no encontrado")
        
        campos = []
        valores = []
        if p.nombre is not None:
            campos.append("nombre = ?")
            valores.append(p.nombre)
        if p.contacto is not None:
            campos.append("contacto = ?")
            valores.append(p.contacto)
        
        if not campos:
            return {"message": "Sin cambios"}
        
        valores.append(prov_id)
        conn.execute(f"UPDATE proveedores SET {', '.join(campos)} WHERE id = ?", valores)
        return {"message": "Actualizado"}

@router.delete("/{prov_id}")
def eliminar_proveedor(prov_id: int):
    with get_db() as conn:
        # Soft delete
        conn.execute("UPDATE proveedores SET activo = 0 WHERE id = ?", (prov_id,))
        return {"message": "Desactivado"}
