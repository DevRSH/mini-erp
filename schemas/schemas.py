from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class LoginRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6)

class ProductoCrear(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    precio: float = Field(..., ge=0)
    costo: float = Field(0, ge=0)
    costo_envio: float = Field(0, ge=0)
    stock: int = Field(0, ge=0)
    stock_minimo: int = Field(5, ge=0)
    categoria: str = Field("General", max_length=50)
    codigo_proveedor: str = Field("", max_length=80)
    tiene_variantes: bool = False

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v):
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()

class ProductoEditar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    precio: Optional[float] = Field(None, ge=0)
    costo: Optional[float] = Field(None, ge=0)
    costo_envio: Optional[float] = Field(None, ge=0)
    stock_minimo: Optional[int] = Field(None, ge=0)
    categoria: Optional[str] = Field(None, max_length=50)
    codigo_proveedor: Optional[str] = Field(None, max_length=80)

class AjusteStock(BaseModel):
    cantidad: int
    motivo: Optional[str] = "Ajuste manual"

class VarianteCrear(BaseModel):
    attr1_nombre: str = Field(..., min_length=1, max_length=40)
    attr1_valor: str = Field(..., min_length=1, max_length=60)
    attr2_nombre: Optional[str] = Field(None, max_length=40)
    attr2_valor: Optional[str] = Field(None, max_length=60)
    stock: int = Field(0, ge=0)
    stock_minimo: int = Field(2, ge=0)
    codigo_barras: str = Field("", max_length=80)

    @field_validator("attr2_valor")
    @classmethod
    def validar_attr2(cls, v, info):
        nombre = info.data.get("attr2_nombre")
        if nombre and not v:
            raise ValueError("Si hay nombre de atributo 2, debe tener valor")
        if not nombre and v:
            raise ValueError("Si hay valor de atributo 2, debe tener nombre")
        return v

class VarianteEditar(BaseModel):
    attr1_valor: Optional[str] = Field(None, max_length=60)
    attr2_valor: Optional[str] = Field(None, max_length=60)
    stock_minimo: Optional[int] = Field(None, ge=0)
    codigo_barras: Optional[str] = Field(None, max_length=80)

class AjusteVariante(BaseModel):
    cantidad: int
    motivo: Optional[str] = "Ajuste manual"

class ItemVenta(BaseModel):
    producto_id: int
    cantidad: int = Field(..., gt=0)
    variante_id: Optional[int] = None
    descuento_item: float = Field(0, ge=0, description="Descuento en $ aplicado a este item")

class VentaCrear(BaseModel):
    items: List[ItemVenta] = Field(..., min_length=1)
    metodo_pago: str = Field("efectivo", pattern="^(efectivo|transferencia|tarjeta)$")
    descuento_pct: float = Field(0, ge=0, le=100, description="Descuento porcentual sobre subtotal")
    descuento_monto: float = Field(0, ge=0, description="Descuento fijo en $ sobre subtotal")

class VentaCorreccion(BaseModel):
    metodo_pago: str = Field("efectivo", pattern="^(efectivo|transferencia|tarjeta)$")
    items: List[ItemVenta] = Field(..., min_length=1)

class ItemCompra(BaseModel):
    producto_id: int
    variante_id: Optional[int] = None
    cantidad: int = Field(..., gt=0)
    costo_unitario: float = Field(..., ge=0)

class CompraCrear(BaseModel):
    proveedor: str = Field("Sin nombre", max_length=100)
    notas: str = Field("", max_length=300)
    costo_envio: float = Field(0, ge=0)
    items: List[ItemCompra] = Field(..., min_length=1)
    actualizar_costo: bool = Field(True, description="Si true, actualiza el costo del producto con el de esta compra")

class CompraCorreccion(BaseModel):
    proveedor: str = Field("Sin nombre", max_length=100)
    notas: str = Field("", max_length=300)
    costo_envio: float = Field(0, ge=0)
    items: List[ItemCompra] = Field(..., min_length=1)
    actualizar_costo: bool = Field(True)

# ── Conteo Físico de Inventario ──

class ItemConteo(BaseModel):
    producto_id: int
    variante_id: Optional[int] = None
    cantidad_fisica: int = Field(..., ge=0)

class ConteoFisico(BaseModel):
    items: List[ItemConteo] = Field(..., min_length=1)
    motivo: str = Field("Toma de inventario físico", max_length=200)
